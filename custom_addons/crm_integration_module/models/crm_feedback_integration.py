from odoo import models, fields, api

class CRMFeedbackIntegration(models.Model):
    _inherit = 'real.estate.feedback'
    
    call_ids = fields.One2many('crm.call.log', 'feedback_id', string='Calls')
    
    def action_create_call(self):
        """Create a new call related to this feedback"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Call',
            'res_model': 'crm.call.log',
            'view_mode': 'form',
            'context': {'default_feedback_id': self.id},
            'target': 'new',
        } 