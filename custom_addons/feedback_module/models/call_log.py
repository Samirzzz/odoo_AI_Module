# -*- coding: utf-8 -*-
import base64
import io
import logging
import urllib3

import requests
from requests_toolbelt import MultipartEncoder
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
# Disable only the InsecureRequestWarning from urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OllamaClient:
    """Ollama HTTP client (no SSL verification)."""
    def __init__(
        self,
        base_url: str = "http://localhost:11434/api",
        model: str = "llama3.2:3b",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"max_tokens": max_tokens},
                },
                timeout=300,  # Increase timeout to 2 minutes
                verify=False,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.exceptions.Timeout:
            _logger.error("Ollama API timeout")
            return "Error: Ollama service timed out. The request took too long to process."
        except requests.exceptions.ConnectionError:
            _logger.error("Ollama API connection error")
            return "Error: Cannot connect to Ollama service. Please ensure it's running."
        except Exception as e:
            _logger.error("Ollama API error: %s", str(e))
            return f"Error: Unable to generate response. {str(e)}"


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

        api_url = "http://cfc5-34-16-136-168.ngrok-free.app/invocations"
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
                
        except Exception as e:
            _logger.error("Audio processing failed: %s", e)
            msg = str(e).lower()
            if "getaddrinfo failed" in msg or "max retries" in msg:
                user_msg = "Cannot reach transcription service; check your URL."
            elif "timeout" in msg:
                user_msg = "Transcription service timed out."
            else:
                user_msg = f"Transcription error: {e}"
            self.write({
                'inference_status':     'error',
                'inference_transcript': user_msg,
                'is_processing':        False,
            })
            self.env.cr.commit()
            
    def _generate_qna_from_rephrased(self):
        """Generate Q&A from rephrased text without user action."""
        if not self.inference_rephrased:
            return
            
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
        
        try:
            answers = OllamaClient().generate(prompt)
            self.write({'llama_qna': answers})
            self.env.cr.commit()
        except Exception as e:
            _logger.error("Q&A generation failed: %s", e)
            self.write({'llama_qna': f"Error generating Q&A: {str(e)}"})
            self.env.cr.commit()

    def action_process_audio_now(self):
        """Manually re-trigger processing."""
        for rec in self:
            if not rec.is_processing:
                rec._process_audio_file()
        return True

    def action_open_questionnaire(self):
        self.ensure_one()
        # … your existing code …

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