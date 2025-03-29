from odoo import models, fields

class RealEstateLead(models.Model):
    _name = 'real.estate.lead'
    _description = 'Real Estate Lead'

    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    feedback_ids = fields.One2many('real.estate.feedback', 'lead_id', string='Feedback')
