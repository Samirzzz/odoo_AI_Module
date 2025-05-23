# -*- coding: utf-8 -*-
import base64
import io
import logging
import urllib3

import requests
from requests_toolbelt import MultipartEncoder
from odoo import models, fields, api
from odoo.exceptions import UserError
from .llama import OllamaClient

_logger = logging.getLogger(__name__)
# Disable only the InsecureRequestWarning from urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FeedbackCallLog(models.Model):
    _name = 'feedback.call.log'
    _description = 'Feedback Call Log'

    lead_id               = fields.Many2one('crm.lead', required=True)
    feedback_id           = fields.Many2one('real.estate.feedback')
    call_description      = fields.Text()
    call_time             = fields.Datetime(default=fields.Datetime.now)
    salesperson_id        = fields.Many2one('res.users', default=lambda self: self.env.user)
    call_recording        = fields.Binary()
    recording_filename    = fields.Char()

    inference_status      = fields.Selection([
                              ('pending','Pending'),
                              ('success','Success'),
                              ('error','Error'),
                            ], default='pending')
    inference_language    = fields.Char(readonly=True)
    inference_transcript  = fields.Text(readonly=True)
    inference_translation = fields.Text(readonly=True)
    inference_rephrased   = fields.Text(readonly=True)

    is_processing         = fields.Boolean(default=False)
    llama_qna             = fields.Text()
    recommendation_results = fields.Html(string="Recommendation Results", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.call_recording:
                # immediately process on create
                self.env.cr.commit()
                rec._process_audio_file()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('call_recording'):
            # immediately process on update
            self.env.cr.commit()
            for rec in self:
                rec._process_audio_file()
        return res

    def _process_audio_file(self):
        """Process the audio file via external API without SSL verify."""
        self.ensure_one()
        if not self.call_recording:
            return

        # mark as processing
        self.write({'is_processing': True, 'inference_status': 'pending'})
        self.env.cr.commit()

        # API URL for transcription service
        api_url = "http://0001-34-147-125-189.ngrok-free.app/invocations"
        raw = base64.b64decode(self.call_recording)
        fname = self.recording_filename or "recording.wav"
        size_mb = len(raw) / (1024 * 1024)

        try:
            if size_mb > 5:
                m = MultipartEncoder({
                    'emp_id': self.salesperson_id.name,
                    'file':   (fname, io.BytesIO(raw), 'audio/wav'),
                })
                headers = {'Content-Type': m.content_type}
                resp = requests.post(
                    api_url, data=m, headers=headers,
                    timeout=(30, 600), stream=True, verify=False
                )
            else:
                resp = requests.post(
                    api_url,
                    files={'file': (fname, raw, 'audio/wav')},
                    data={'emp_id': self.salesperson_id.name},
                    timeout=(10, 300),
                    allow_redirects=True,
                    verify=False,
                )
            resp.raise_for_status()
            result = resp.json()
            self.write({
                'inference_status':      result.get('status', 'error'),
                'inference_language':    result.get('language', ''),
                'inference_transcript':  result.get('transcription', ''),
                'inference_translation': result.get('translation', ''),
                'inference_rephrased':   result.get('final_rephrased_text', ''),
                'is_processing':         False,
            })
            self.env.cr.commit()
            
            # Automatically generate Q&A if we have rephrased text
            if result.get('status') == 'success' and result.get('final_rephrased_text'):
                self._generate_qna_from_rephrased()
                
        except requests.exceptions.ConnectionError as e:
            _logger.error("Connection error during transcription: %s", e)
            self.write({
                'inference_status': 'error',
                'inference_transcript': 'Connection to transcription service failed. Please check if the service is running and the API URL is correct.',
                'is_processing': False,
            })
            self.env.cr.commit()
        except requests.exceptions.Timeout as e:
            _logger.error("Timeout during transcription: %s", e)
            self.write({
                'inference_status': 'error',
                'inference_transcript': 'Transcription service timed out. Please try again.',
                'is_processing': False,
            })
            self.env.cr.commit()
        except Exception as e:
            _logger.error("Audio processing failed: %s", e)
            self.write({
                'inference_status': 'error',
                'inference_transcript': f'Transcription error: {str(e)}',
                'is_processing': False,
            })
            self.env.cr.commit()
            
    def _generate_qna_from_rephrased(self):
        """Generate Q&A from rephrased text without user action."""
        if not self.inference_rephrased:
            return
            
        prompt = (
            "The following is a transcription of a phone call with a real estate client. "
            "Extract the answers to these questions in a structured format with JUST the answer and "
            "NO additional explanation. If the information is not available, answer with 'Unknown'.\n\n"
            f"--- Transcription ---\n{self.inference_rephrased}\n--- End of Transcription ---\n\n"
            "1. Property Type? (e.g. apartment, villa, townhouse)\n"
            "2. Number of Rooms? (numeric value only)\n"
            "3. Maximum Budget? (numeric value only)\n"
            "4. Does client prefer installments? (Yes/No)\n"
            "5. Required Features? (list main features)\n"
            "6. When does the client want to receive the property in years? (numeric value only, can be decimal like 1.5)\n"
            "7. Preferred Location? (location name only)\n"
            "8. Unit Type? (e.g. residential, commercial, etc.)\n"
            "9. Did the client agree to a meeting? (Yes/No/Unknown)\n\n"
            "Format your answers exactly like this, with just the direct answer for each question:\n"
            "1. Apartment\n"
            "2. 3\n"
            "3. 2000000\n"
            "4. Yes\n"
            "5. Swimming pool, garden, security\n"
            "6. 1.5\n"
            "7. R8\n"
            "8. Residential\n"
            "9. Yes"
        )
        
        try:
            answers = OllamaClient().generate(prompt)
            self.write({'llama_qna': answers})
            self.env.cr.commit()
        except Exception as e:
            _logger.error("Q&A generation failed: %s", e)
            self.write({'llama_qna': f"Error generating Q&A: {str(e)}"})
            self.env.cr.commit()

    def _extract_questionnaire_data(self):
        """Extract structured data from llama_qna to use in the questionnaire."""
        if not self.llama_qna:
            return {}
            
        # Initialize with default values
        data = {
            'property_type': False,
            'number_of_rooms': 0,
            'max_budget': 0,
            'prefers_installments': False,
            'required_features': False,
            'desired_years': 0,
            'preferred_location': False,
            'unit_type': False,
            'meeting_agreed': False,
        }
        
        # Split by lines and extract data
        lines = self.llama_qna.strip().split('\n')
        
        try:
            for i, line in enumerate(lines):
                # Skip lines that don't start with a number
                if not line.strip() or not line[0].isdigit():
                    continue
                    
                # Remove the question number and any leading/trailing spaces
                answer = line[2:].strip() if len(line) > 2 else ""
                
                # Skip if answer is 'Unknown' or empty
                if answer.lower() == 'unknown' or not answer:
                    continue
                    
                # Parse answers based on the question number
                if i == 0:  # Property Type
                    data['property_type'] = answer
                elif i == 1:  # Number of Rooms
                    try:
                        data['number_of_rooms'] = int(answer.split()[0])
                    except:
                        pass
                elif i == 2:  # Max Budget
                    # Extract numbers only
                    budget = ''.join(c for c in answer if c.isdigit())
                    if budget:
                        data['max_budget'] = float(budget)
                elif i == 3:  # Installments
                    data['prefers_installments'] = answer.lower() in ['yes', 'true', '1']
                elif i == 4:  # Required Features
                    data['required_features'] = answer
                elif i == 5:  # Desired Years
                    try:
                        # Handle decimal values properly
                        years = answer.split()[0]
                        data['desired_years'] = float(years)
                    except:
                        pass
                elif i == 6:  # Preferred Location
                    # Handle R8/R7 format by taking first location
                    location = answer.split('/')[0].strip()
                    data['preferred_location'] = location
                elif i == 7:  # Unit Type
                    data['unit_type'] = answer
                elif i == 8:  # Meeting Agreement
                    data['meeting_agreed'] = answer.lower() in ['yes', 'true', '1']
        except Exception as e:
            _logger.error("Error extracting questionnaire data: %s", e)
            
        return data

    def action_process_audio_now(self):
        """Manually re-trigger processing."""
        for rec in self:
            if not rec.is_processing:
                rec._process_audio_file()
        return True
        
    def action_open_questionnaire(self):
        """Open the questionnaire in a dialog view."""
        self.ensure_one()
        
        # Find existing questionnaire or create a new one
        questionnaire = self.env['feedback.lead.questionnaire'].search([
            ('call_log_id', '=', self.id)
        ], limit=1)
        
        if not questionnaire:
            # Create new questionnaire with data from llama QnA
            questionnaire_data = self._extract_questionnaire_data()
            questionnaire = self.env['feedback.lead.questionnaire'].create({
                'lead_id': self.lead_id.id,
                'call_log_id': self.id,
                'feedback_id': self.feedback_id.id if self.feedback_id else False,
                **questionnaire_data
            })
        
        # Open in dialog view with force_reload to ensure it opens
        return {
            'name': 'Client Questionnaire',
            'type': 'ir.actions.act_window',
            'res_model': 'feedback.lead.questionnaire',
            'res_id': questionnaire.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'mode': 'edit'},
            'context': {'force_reload': True}  # Force reload to ensure it opens
        }

    def action_generate_qna(self):
        self.ensure_one()
        if not self.inference_rephrased:
            raise UserError("No rephrased text available.")
        prompt = (
            "The following is a transcription of a phone call. Answer the eight questions at the end **in English** "
            "using only information found in the transcript.\n\n"
            f"--- Transcription ---\n{self.inference_rephrased}\n--- End of Transcription ---\n\n"
            "1. What type of property does the client want?\n"
            "2. How many rooms are preferred?\n"
            "3. What is the client's maximum budget?\n"
            "4. Does the client prefer installment plans?\n"
            "5. What features does the client require?\n"
            "6. When does the client want to receive the property in years?\n"
            "7. Which location does the client prefer?\n"
            "8. What is the type of the unit?\n\n"
            "Please list your answers 1-8 on separate lines."
        )
        answers = OllamaClient().generate(prompt)
        self.write({'llama_qna': answers})
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   'Q&A Generated',
                'message': 'AI answers saved.',
                'type':    'success',
            }
        }

    def action_save_and_stay(self):
        """Save the record and keep the form open."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'flags': {'mode': 'edit'}
        } 