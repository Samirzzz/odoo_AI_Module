# -*- coding: utf-8 -*-
import base64
import io
import logging
import urllib3
import re

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

    @staticmethod
    def _parse_budget_to_float(s):
        if not s or str(s).lower() == 'unknown':
            return 0.0
        s = str(s).lower()
        s = re.sub(r'[^\d.,millionk]', '', s)
        val = 0.0
        try:
            if 'million' in s:
                val = float(re.sub(r'million', '', s).replace(',', '').strip() or 0) * 1000000
            elif 'k' in s:
                val = float(re.sub(r'k', '', s).replace(',', '').strip() or 0) * 1000
            else:
                val = float(s.replace(',', '').strip() or 0)
        except ValueError:
            _logger.warning(f"Could not parse budget string to float: {s}")
            return 0.0
        return val

    @staticmethod
    def _parse_int_answer(s):
        if not s or str(s).lower() == 'unknown':
            return 0
        try:
            return int(re.search(r'\d+', str(s)).group())
        except (ValueError, AttributeError):
            _logger.warning(f"Could not parse int from: {s}")
            return 0

    @staticmethod
    def _parse_float_answer(s):
        if not s or str(s).lower() == 'unknown':
            return 0.0
        try:
            match = re.search(r'(\d*?\.?\d+)', str(s))
            return float(match.group(1)) if match else 0.0
        except (ValueError, AttributeError):
            _logger.warning(f"Could not parse float from: {s}")
            return 0.0

    @staticmethod
    def _parse_payment_option(s):
        if not s or str(s).lower() == 'unknown':
            return False
        s_lower = str(s).lower()
        if s_lower in ['yes', 'true', '1', 'installment', 'installments']:
            return 'installment'
        elif s_lower in ['no', 'false', '0', 'cash']:
            return 'cash'
        return False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.call_recording:
                self.env.cr.commit()
                rec._process_audio_file()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('call_recording'):
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
        api_url = "http://6eba-34-125-187-1.ngrok-free.app/invocations"
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
                'inference_transcript': 'Connection error.',
                'is_processing': False,
            })
            self.env.cr.commit()
        except requests.exceptions.Timeout as e:
            _logger.error("Timeout during transcription: %s", e)
            self.write({
                'inference_status': 'error',
                'inference_transcript': 'Timeout.',
                'is_processing': False,
            })
            self.env.cr.commit()
        except Exception as e:
            _logger.error("Audio processing failed: %s", e)
            self.write({
                'inference_status': 'error',
                'inference_transcript': f'Error: {str(e)}',
                'is_processing': False,
            })
            self.env.cr.commit()
            
    def _generate_qna_from_rephrased(self):
        """Generate Q&A from rephrased text without user action."""
        if not self.inference_rephrased:
            return
            
        prompt = (
            "The following is a transcription of a phone call with a real-estate "
            "client. Answer the twelve questions below in English **using ONLY "
            "information that appears in the transcript**. If information is "
            "missing, output the single word 'Unknown'.\n\n"
            f"--- Transcription ---\n{self.inference_rephrased}\n"
            "--- End of Transcription ---\n\n"
            "Questions:\n"
            "1. What type of property does the client want?\n"
            "2. How many rooms are preferred?\n"
            "3. What is the client's maximum budget? (numbers only – e.g. "
            "'2 million' → 2000000)\n"
            "4. Does the client prefer installment plans? (Yes/No)\n"
            "5. What amenities does the client require?\n"
            "6. When does the client want to get the property in years?\n"
            "7. Preferred location?\n"
            "8. Unit type?\n"
            "9. Was a meeting scheduled (date/time)?\n"
            "10. Down-payment percent or amount?\n"
            "11. Bathrooms required?\n"
            "12. Preferred finishing?\n\n"
            "Format your answers EXACTLY as in this example (twelve lines, "
            "number, dot, space, direct answer, nothing else):\n"
            "1. Apartment\n"
            "2. 3\n"
            "3. 2000000\n"
            "4. Yes\n"
            "5. Gym, security, near monorail\n"
            "6. 1.5\n"
            "7. R8\n"
            "8. Residential\n"
            "9. Next Thursday\n"
            "10. 10%\n"
            "11. 2\n"
            "12. Unknown"
        )
        
        try:
            answers = OllamaClient().generate(prompt)
            self.write({'llama_qna': answers})
            self.env.cr.commit()
            
            # Extract answer text after "n. " and normalize
            answer_lines = []
            for line in answers.splitlines():
                line = line.strip()
                if line and line[0].isdigit() and "." in line:
                    answer_lines.append(line.split(".", 1)[1].strip())

            # Normalize and extract data for Pinecone search
            norm = self._normalize_and_extract(answer_lines)

            # Build Pinecone filter
            filters = {}
            if norm.get("max_price") is not None and norm.get("max_price") > 0:
                filters["price"] = {"$lte": norm["max_price"]}
            if norm.get("city"):
                filters["city"] = norm["city"]
            if norm.get("bedrooms") and norm.get("bedrooms") > 0:
                filters["bedrooms"] = norm["bedrooms"]
            if norm.get("unit_type"):
                filters["type"] = norm["unit_type"]

            # Search properties using vector search
            query_text = " ".join(answer_lines)
            from .property_vector_search import PropertyVectorSearch
            search_service = PropertyVectorSearch(self.env)
            
            # Get property recommendations using the existing search method
            properties = search_service.search_properties(
                query_text=query_text,
                filters=filters,
                top_k=5
            )
            
            # Format as HTML
            html_results = search_service.format_properties_as_html(properties)
            
            self.write({
                "recommendation_results": html_results,
                "inference_status": "success",
                "is_processing": False,
            })
            self.env.cr.commit()
            
        except Exception as e:
            _logger.error("Q&A generation failed: %s", e)
            self.write({
                'llama_qna': f"Error: {str(e)}",
                "recommendation_results": f"Error: {e}",
                "inference_status": "error",
                "is_processing": False,
            })
            self.env.cr.commit()

    @staticmethod
    def _normalize_and_extract(answers):
        """
        Convert list of 12 raw answer strings → dict of neat values.
        """
        # Ensure we have 12 answers, padding with 'Unknown' if necessary
        answers_padded = answers + ['Unknown'] * (12 - len(answers)) if len(answers) < 12 else answers

        out = {
            "property_type": answers_padded[0] if str(answers_padded[0]).lower() != 'unknown' else False,
            "bedrooms": FeedbackCallLog._parse_int_answer(answers_padded[1]),
            "max_price": FeedbackCallLog._parse_budget_to_float(answers_padded[2]),
            "payment_option": FeedbackCallLog._parse_payment_option(answers_padded[3]),
            "features": answers_padded[4] if str(answers_padded[4]).lower() != 'unknown' else False,
            "delivery_in": FeedbackCallLog._parse_float_answer(answers_padded[5]),
            "city": answers_padded[6] if str(answers_padded[6]).lower() != 'unknown' else False,
            "unit_type": answers_padded[7] if str(answers_padded[7]).lower() != 'unknown' else False,
            "meeting_scheduled_info": answers_padded[8] if str(answers_padded[8]).lower() != 'unknown' else False,
            "down_payment": FeedbackCallLog._parse_budget_to_float(answers_padded[9]),
            "bathrooms": FeedbackCallLog._parse_int_answer(answers_padded[10]),
            "finishing_type": answers_padded[11] if str(answers_padded[11]).lower() != 'unknown' else False,
        }
        return out

    def _extract_questionnaire_data(self):
        """Extract structured data from llama_qna to use in the questionnaire."""
        if not self.llama_qna:
            return {}
            
        # Initialize with default values, mapping to FeedbackLeadQuestionnaire fields
        data = {
            'property_type': False,
            'bedrooms': 0,
            'max_price': 0.0,
            'payment_option': False,
            'features': False,
            'delivery_in': 0.0,
            'city': False,
            'unit_type': False,
            'meeting_scheduled_info': False,
            'down_payment': 0.0,
            'bathrooms': 0,
            'finishing_type': False,
            'meeting_agreed': False,
            'meeting_scheduled': False,
        }
        
        lines = self.llama_qna.strip().split('\n')
        answers_from_llama = ['Unknown'] * 12 # Initialize with defaults

        for line in lines:
            line_strip = line.strip()
            if not line_strip or not line_strip[0].isdigit():
                continue
            try:
                q_num_str, answer_text = line_strip.split('.', 1)
                q_num = int(q_num_str)
                if 1 <= q_num <= 12:
                    answers_from_llama[q_num - 1] = answer_text.strip()
            except ValueError:
                _logger.warning(f"Could not parse Q&A line: {line_strip}")
                continue

        # Use the same parsing logic as _normalize_and_extract for consistency
        normalized_data = self._normalize_and_extract(answers_from_llama)
        
        # Map normalized data to the fields expected by FeedbackLeadQuestionnaire
        # Most keys should already match due to _normalize_and_extract structure
        data.update(normalized_data) # This will overwrite initial defaults with parsed values

        # Logic for meeting_agreed and meeting_scheduled based on meeting_scheduled_info (Q9)
        meeting_info = data.get('meeting_scheduled_info')
        if meeting_info and str(meeting_info).lower() != 'unknown' and str(meeting_info).strip():
            data['meeting_agreed'] = True 
            data['meeting_scheduled'] = True 
        else:
            data['meeting_agreed'] = False
            data['meeting_scheduled'] = False
            data['meeting_scheduled_info'] = False # Clear if it was 'Unknown' or empty after normalization

        # Ensure fields not in the 12 questions but present in the questionnaire model are handled if necessary
        # e.g., data['area'] = ... if there's a way to infer it or set a default

        _logger.info(f"Extracted questionnaire data: {data}")
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
        
        questionnaire = self.env['feedback.lead.questionnaire'].search([
            ('call_log_id', '=', self.id)
        ], limit=1)
        
        questionnaire_data = self._extract_questionnaire_data()
        
        if not questionnaire:
            questionnaire = self.env['feedback.lead.questionnaire'].create({
                'lead_id': self.lead_id.id,
                'call_log_id': self.id,
                'feedback_id': self.feedback_id.id if self.feedback_id else False,
                **questionnaire_data
            })
        else:
            # Optionally update existing questionnaire if desired
            questionnaire.write(questionnaire_data)
        
        return {
            'name': 'Client Questionnaire',
            'type': 'ir.actions.act_window',
            'res_model': 'feedback.lead.questionnaire',
            'res_id': questionnaire.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'mode': 'edit'},
            'context': {'force_reload': True}
        }

    def action_generate_qna(self):
        self.ensure_one()
        if not self.inference_rephrased:
            raise UserError("No rephrased text available.")
        prompt = (
            "The following is a transcription of a phone call. Answer the twelve questions at the end **in English** "
            "using only information found in the transcript. If information is not mentioned in the transcript, answer \"Unknown\".\n\n"
            f"--- Transcription ---\n{self.inference_rephrased}\n--- End of Transcription ---\n\n"
            "1. What type of property does the client want?\n"
            "2. How many rooms are preferred?\n"
            "3. What is the client's maximum budget?\n"
            "4. Does the client prefer installment plans?\n"
            "5. What features does the client require?\n"
            "6. When does the client want to receive the property in years?\n"
            "7. Which location does the client prefer?\n"
            "8. What is the type of the unit?\n"
            "9. Was a meeting scheduled (date/time)?\n"
            "10. What is the down payment percentage or amount mentioned?\n"
            "11. How many bathrooms are required?\n"
            "12. What type of finishing is preferred?\n\n"
            "Please list your answers 1-12 on separate lines."
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