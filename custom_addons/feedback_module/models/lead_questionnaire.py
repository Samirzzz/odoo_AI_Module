from odoo import models, fields, api
from .llama import OllamaClient
import logging

_logger = logging.getLogger(__name__)

class FeedbackLeadQuestionnaire(models.Model):
    _name = 'feedback.lead.questionnaire'
    _description = 'Client Questionnaire for Feedback Module'

    lead_id = fields.Many2one('crm.lead', string="Lead", required=True)
    property_type = fields.Char(string="Property Type")
    number_of_rooms = fields.Integer(string="Number of Rooms")
    max_budget = fields.Float(string="Maximum Budget")
    prefers_installments = fields.Boolean(string="Prefers Installments")
    required_features = fields.Text(string="Required Features")
    desired_years = fields.Integer(string="Desired Years to Receive Property")
    preferred_location = fields.Char(string="Preferred Location")
    unit_type = fields.Char(string="Unit Type")
    meeting_scheduled = fields.Boolean(string="Meeting Scheduled")
    meeting_datetime = fields.Datetime(string="Meeting Date & Time")
    
    # Additional fields for feedback module
    feedback_id = fields.Many2one('real.estate.feedback', string="Related Feedback")
    call_log_id = fields.Many2one('feedback.call.log', string="Related Call Log")
    notes = fields.Text(string="Additional Notes")
    
    # Related fields to display call log inference results
    call_inference_status = fields.Selection(related="call_log_id.inference_status", string="Inference Status", readonly=True)
    call_inference_language = fields.Char(related="call_log_id.inference_language", string="Detected Language", readonly=True)
    call_inference_transcript = fields.Text(related="call_log_id.inference_transcript", string="Transcription", readonly=True)
    call_inference_translation = fields.Text(related="call_log_id.inference_translation", string="Translation", readonly=True)
    call_inference_rephrased = fields.Text(related="call_log_id.inference_rephrased", string="Rephrased Text", readonly=True)
    
    # Llama integration fields
    llama_prompt = fields.Text(string="AI Prompt", 
        default="Generate a description of an ideal property based on: ")
    llama_response = fields.Text(string="AI Generated Response", readonly=True)
    
    @api.onchange('meeting_scheduled')
    def _onchange_meeting_scheduled(self):
        """When meeting_scheduled is turned off, clear the meeting datetime"""
        if not self.meeting_scheduled:
            self.meeting_datetime = False 
            
    def action_generate_llama_response(self):
        """Generate a response using the Llama model"""
        self.ensure_one()
        
        # Build the full prompt with questionnaire data
        full_prompt = self.llama_prompt + "\n\n"
        
        # Add questionnaire data to the prompt
        if self.property_type:
            full_prompt += f"- Property Type: {self.property_type}\n"
        if self.number_of_rooms:
            full_prompt += f"- Number of Rooms: {self.number_of_rooms}\n"
        if self.max_budget:
            full_prompt += f"- Budget: {self.max_budget}\n"
        if self.preferred_location:
            full_prompt += f"- Location: {self.preferred_location}\n"
        if self.required_features:
            full_prompt += f"- Required Features: {self.required_features}\n"
        if self.unit_type:
            full_prompt += f"- Unit Type: {self.unit_type}\n"
        
        try:
            # Log the request
            _logger.info(f"Generating Llama response with prompt: {full_prompt}")
            
            # Initialize the Ollama client and generate response
            client = OllamaClient(model="llama3.2")
            response = client.generate(full_prompt, max_tokens=500)
            
            # Update the response field
            self.write({'llama_response': response})
            
            # Odoo 18 notification style
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'AI response generated successfully!',
                    'sticky': False,
                    'type': 'success',
                }
            }
            
        except Exception as e:
            error_message = f"Error generating AI response: {str(e)}"
            _logger.error(error_message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': error_message,
                    'sticky': True,
                    'type': 'danger',
                }
            }

    def action_save_and_stay(self):
        """Save the record and keep the form open."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',  # Keep it as a dialog
            'flags': {'mode': 'edit'},
        } 