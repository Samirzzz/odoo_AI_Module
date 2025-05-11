from odoo import models, fields, api

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
    
    @api.onchange('meeting_scheduled')
    def _onchange_meeting_scheduled(self):
        """When meeting_scheduled is turned off, clear the meeting datetime"""
        if not self.meeting_scheduled:
            self.meeting_datetime = False 