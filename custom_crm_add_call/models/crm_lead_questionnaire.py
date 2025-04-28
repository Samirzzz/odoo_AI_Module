from odoo import models, fields

class CRMLeadQuestionnaire(models.Model):
    _name = 'crm.lead.questionnaire'
    _description = 'Client Questionnaire'

    lead_id = fields.Many2one('crm.lead', string="Lead", required=True)
    property_type = fields.Char(string="Property Type")
    number_of_rooms = fields.Integer(string="Number of Rooms")
    max_budget = fields.Float(string="Maximum Budget")
    prefers_installments = fields.Boolean(string="Prefers Installments")  # <-- this was missing
    required_features = fields.Text(string="Required Features")
    desired_years = fields.Integer(string="Desired Years to Receive Property")
    preferred_location = fields.Char(string="Preferred Location")
    unit_type = fields.Char(string="Unit Type")
    meeting_scheduled = fields.Boolean(string="Meeting Scheduled")
    meeting_datetime = fields.Datetime(string="Meeting Date & Time")
