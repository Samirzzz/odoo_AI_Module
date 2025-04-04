import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)

class RealEstateFeedback(models.Model):
    _name = 'real.estate.feedback'
    _description = 'Real Estate Feedback'

    feedback = fields.Text(string='Feedback', required=True)
    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    user_id = fields.Many2one('users.users', string='User', required=False)
