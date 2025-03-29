from odoo import models, fields

class RealEstateFeedback(models.Model):
    _name = 'real.estate.feedback'
    _description = 'Lead Feedback'

    lead_id = fields.Many2one('real.estate.lead', string='Lead', required=True, ondelete='cascade')
    feedback_text = fields.Text(string='Feedback')
