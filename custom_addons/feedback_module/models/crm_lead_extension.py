from odoo import models, fields, api

class CRMLeadExtension(models.Model):
    _inherit = 'crm.lead'

    def action_log_call(self):
        """Open a form to log a call for this lead"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Call',
            'res_model': 'feedback.call.log',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_salesperson_id': self.env.user.id,
            }
        }

    def action_open_questionnaire(self):
        """Open the client questionnaire form"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Client Questionnaire',
            'view_mode': 'form',
            'res_model': 'feedback.lead.questionnaire',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
            }
        } 
