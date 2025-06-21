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
    inference_rephrased   = fields.Html(string="Rephrased Text", readonly=True)

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

    def _to_html(self, text):
        """Convert plain text to HTML format preserving line breaks."""
        if not text:
            return ""
        # Split into paragraphs and wrap each in <p> tags
        paragraphs = text.split('\n\n')
        html = []
        for p in paragraphs:
            if p.strip():
                # Convert single line breaks to <br>
                p = p.replace('\n', '<br>')
                html.append(f'<p>{p}</p>')
        return '\n'.join(html)

    def _process_audio_file(self):
        """Process the audio file via external API without SSL verify."""
        self.ensure_one()
        if not self.call_recording:
            return

        # mark as processing
        self.write({'is_processing': True, 'inference_status': 'pending'})
        self.env.cr.commit()

        # API URL for transcription service
        api_url = "http://a179-34-125-21-13.ngrok-free.app/invocations"
        raw = base64.b64decode(self.call_recording)
        fname = self.recording_filename or "recording.wav"
        size_mb = len(raw) / (1024 * 1024)

        try:
            if size_mb > 5:
                m = MultipartEncoder({
                    'emp_id': self.salesperson_id.name,
                    'file':   (fname, io.BytesIO(raw), 'audio/wav'),
                    'output_format': 'html'  # Request HTML format from the API
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
                    data={
                        'emp_id': self.salesperson_id.name,
                        'output_format': 'html'  # Request HTML format from the API
                    },
                    timeout=(10, 300),
                    allow_redirects=True,
                    verify=False,
                )
            resp.raise_for_status()
            result = resp.json()
            
            # Convert plain text to HTML if needed
            rephrased_text = result.get('final_rephrased_text', '')
            if result.get('output_format') != 'html':
                rephrased_text = self._to_html(rephrased_text)
            
            self.write({
                'inference_status':      result.get('status', 'error'),
                'inference_language':    result.get('language', ''),
                'inference_transcript':  result.get('transcription', ''),
                'inference_translation': result.get('translation', ''),
                'inference_rephrased':   rephrased_text,
                'is_processing':         False,
            })
            self.env.cr.commit()
            
            # Automatically generate Q&A if we have rephrased text
            if result.get('status') == 'success' and rephrased_text:
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
            "The following is a transcription of a phone call between a real estate broker and a client. "
            "Extract answers ONLY from the CLIENT's statements, ignoring the broker's questions and statements. "
            "Answer the twelve questions below in English using ONLY information that the CLIENT explicitly stated. "
            "If the client did not mention specific information, output 'Unknown'.\n\n"
            f"--- Transcription ---\n{self.inference_rephrased}\n"
            "--- End of Transcription ---\n\n"
            "Important Instructions:\n"
            "1. Only use information that was explicitly stated by the CLIENT\n"
            "2. Ignore any information mentioned by the broker\n"
            "3. If the client didn't mention something, use 'Unknown'\n"
            "4. Do not infer or assume information not directly stated by the client\n"
            "5. For meeting scheduling (Question 9):\n"
            "   - If client agrees to a viewing but no specific date/time is mentioned, write 'Agreed to viewing'\n"
            "   - If client mentions a specific date/time, include those details\n"
            "   - If client declines or doesn't respond to viewing request, write 'Unknown'\n"
            "6. For payment options (Question 4):\n"
            "   - Answer 'No' if client explicitly states any of these:\n"
            "     * 'I prefer cash'\n"
            "     * 'I want to pay in cash'\n"
            "     * 'Cash payment'\n"
            "     * 'Full payment'\n"
            "     * 'Pay in full'\n"
            "     * 'Pay cash'\n"
            "     * 'Pay the full amount'\n"
            "   - Answer 'Yes' if client explicitly states any of these:\n"
            "     * 'I prefer installments'\n"
            "     * 'I want to pay in installments'\n"
            "     * 'Monthly payments'\n"
            "     * 'Payment plan'\n"
            "     * 'Financing'\n"
            "     * 'Pay in installments'\n"
            "   - Answer 'Unknown' ONLY if client doesn't mention any payment preference\n"
            "7. For finishing type (Question 12):\n"
            "   - Answer 'Fully Furnished' if client mentions any of these:\n"
            "     * 'Turnkey'\n"
            "     * 'Key ready'\n"
            "     * 'Key-ready'\n"
            "     * 'Ready to move in'\n"
            "     * 'Fully furnished'\n"
            "     * 'Ready for immediate use'\n"
            "     * 'Ready to use'\n"
            "   - Answer 'Core' if client mentions any of these:\n"
            "     * 'Semi-finished'\n"
            "     * 'Core and Shell'\n"
            "     * 'Core'\n"
            "     * 'Basic structure'\n"
            "     * 'Shell'\n"
            "   - Answer 'Finished' if client mentions any of these:\n"
            "     * 'Finished'\n"
            "     * 'Fully finished'\n"
            "     * 'Complete'\n"
            "     * 'Ready'\n"
            "     * 'Done'\n"
            "   - Answer 'Unknown' ONLY if client doesn't mention any finishing type\n\n"
            "Location Translation Rules:\n"
            "- If a speaker mentions 'madinaty', translate it as 'Madinaty' (a city in Egypt)\n"
            "- If a speaker mentions 'tagamo3' or 'tagamoa', translate it as 'New Cairo'\n"
            "- If a speaker mentions 'zamalek', translate it as 'Zamalek' (a neighborhood in Cairo)\n"
            "- If a speaker mentions 'maadi' or 'ma3adi', translate it as 'Maadi'\n"
            "- If a speaker mentions 'nasr city', 'nasr', or 'madinet nasr', translate as 'Nasr City'\n"
            "- If a speaker mentions '3asema', 'el 3asema', or '3asema el edarya', translate it as 'New Capital'\n"
            "- If a speaker mentions 'sheikh zayed', translate it as 'Sheikh Zayed'\n"
            "- If a speaker mentions '6 october' or '6th october', translate it as '6th of October City'\n"
            "- If a speaker mentions 'heliopolis' or 'masr el gedida', translate it as 'Heliopolis'\n"
            "- Maintain all other place names as contextually accurate Egyptian locations\n\n"
            "Questions:\n"
            "1. What type of property does the client want?\n"
            "2. How many rooms are preferred?\n"
            "3. What is the desired area in square meters?\n"
            "4. What is the client's maximum budget? (numbers only – e.g. "
            "'2 million' → 2000000)\n"
            "5. Does the client prefer installment plans? (Yes/No)\n"
            "6. What amenities does the client require?\n"
            "7. When does the client want to get the property in years?\n"
            "8. Preferred location?\n"
            "9. Unit type?\n"
            "10. Was a meeting scheduled (date/time)?\n"
            "11. Down-payment percent or amount?\n"
            "12. Bathrooms required?\n"
            "13. Preferred finishing?\n\n"
            "Format your answers as follows:\n"
            "1. [Property type - e.g., Apartment, Villa, etc.]\n"
            "2. [Number of bedrooms - numeric only]\n"
            "3. [Area in square meters - numeric only]\n"
            "4. [Budget in EGP - numeric only]\n"
            "5. [Yes/No for installment preference - 'No' for cash, 'Yes' for installments]\n"
            "6. [Comma-separated list of amenities]\n"
            "7. [Number of years - numeric only]\n"
            "8. [Location name - use standardized names from translation rules]\n"
            "9. [Unit type - e.g., Residential, Commercial]\n"
            "10. [Meeting status - 'Agreed to viewing' if client agreed but no date specified, specific date/time if mentioned, or 'Unknown']\n"
            "11. [Down payment as number or percentage]\n"
            "12. [Number of bathrooms - numeric only]\n"
            "13. [Finishing type - 'Fully Furnished' for Turnkey/Key-ready, 'Core' for Semi-finished/Core and Shell, 'Finished' for Fully Finished, or 'Unknown']\n\n"
            "Important:\n"
            "- Use 'Unknown' if the client did not explicitly state the information\n"
            "- For numeric answers (budget, rooms, years), provide only the number\n"
            "- For amenities, list only those specifically mentioned by the client\n"
            "- Keep answers concise and to the point\n"
            "- Do not include any information that was only mentioned by the broker\n"
            "- Always use standardized location names as per the translation rules\n"
            "- For meeting scheduling, clearly indicate if client agreed to viewing even if no specific date was mentioned\n"
            "- For finishing types, carefully check for all variations of key-ready, turnkey, and other finishing terms\n"
            "- For payment options, carefully check for explicit statements about cash or installment preferences"
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
                    # Extract everything after the number and dot
                    answer = line.split(".", 1)[1].strip()
                    # Remove any square brackets or example text
                    answer = re.sub(r'\[.*?\]', '', answer).strip()
                    answer_lines.append(answer)

            # Normalize and extract data for search
            norm = self._normalize_and_extract(answer_lines)

            # Build search filters
            filters = {}
            if norm.get("max_price") is not None and norm.get("max_price") > 0:
                filters["price"] = {"$lte": norm["max_price"]}
            if norm.get("city"):
                filters["city"] = norm["city"]
            if norm.get("bedrooms") and norm.get("bedrooms") > 0:
                filters["bedrooms"] = norm["bedrooms"]
            if norm.get("area") and norm.get("area") > 0:
                filters["area"] = {"$gte": norm["area"]}

            # Search properties using vector search
            query_text = " ".join(answer_lines)
            from .property_vector_search import PropertyVectorSearch
            search_service = PropertyVectorSearch(self.env)
            
            # Get property recommendations
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
            "property_type": answers_padded[0] if str(answers_padded[0]).lower() != 'unknown' else '',
            "bedrooms": FeedbackCallLog._parse_int_answer(answers_padded[1]),
            "area": FeedbackCallLog._parse_float_answer(answers_padded[2]),
            "max_price": FeedbackCallLog._parse_budget_to_float(answers_padded[3]),
            "payment_option": FeedbackCallLog._parse_payment_option(answers_padded[4]),
            "features": answers_padded[5] if str(answers_padded[5]).lower() != 'unknown' else '',
            "delivery_in": FeedbackCallLog._parse_float_answer(answers_padded[6]),
            "city": answers_padded[7] if str(answers_padded[7]).lower() != 'unknown' else '',
            "meeting_scheduled_info": answers_padded[8] if str(answers_padded[8]).lower() != 'unknown' else '',
            "down_payment": FeedbackCallLog._parse_budget_to_float(answers_padded[9]),
            "bathrooms": FeedbackCallLog._parse_int_answer(answers_padded[10]),
            "finishing_type": answers_padded[11] if str(answers_padded[11]).lower() != 'unknown' else '',
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
            'meeting_scheduled_info': False,
            'down_payment': 0.0,
            'bathrooms': 0,
            'finishing_type': False,
            'meeting_agreed': False,
            'meeting_scheduled': False,
            'area': 0.0,
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
        data.update(normalized_data)

        # Enhanced meeting status handling
        meeting_info = data.get('meeting_scheduled_info', '').lower()
        if meeting_info:
            if 'agreed to viewing' in meeting_info:
                data['meeting_agreed'] = True
                data['meeting_scheduled'] = False
                data['meeting_scheduled_info'] = 'Agreed to viewing'
            elif meeting_info != 'unknown':
                data['meeting_agreed'] = True
                data['meeting_scheduled'] = True
                data['meeting_scheduled_info'] = meeting_info
            else:
                data['meeting_agreed'] = False
                data['meeting_scheduled'] = False
                data['meeting_scheduled_info'] = False
        else:
            data['meeting_agreed'] = False
            data['meeting_scheduled'] = False
            data['meeting_scheduled_info'] = False

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
            "3. What is the desired area in square meters?\n"
            "4. What is the client's maximum budget?\n"
            "5. Does the client prefer installment plans?\n"
            "6. What features does the client require?\n"
            "7. When does the client want to receive the property in years?\n"
            "8. Which location does the client prefer?\n"
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