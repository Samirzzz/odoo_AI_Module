import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)

class RealEstateFeedback(models.Model):
    _name = 'real.estate.feedback'
    _description = 'Real Estate Feedback'
    _order = 'created_at desc'

    feedback = fields.Text(string='Feedback', required=True)
    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    user_id = fields.Many2one('users.users', string='User', required=False)
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now, required=True)

    @api.model
    def create(self, vals):
        """Override create to ensure created_at is set correctly."""
        if 'created_at' in vals and not vals['created_at']:
            vals['created_at'] = fields.Datetime.now()
        return super(RealEstateFeedback, self).create(vals)

    def write(self, vals):
        """Override write to handle created_at field properly."""
        if 'created_at' in vals and not vals['created_at']:
            vals['created_at'] = fields.Datetime.now()
        return super(RealEstateFeedback, self).write(vals)
