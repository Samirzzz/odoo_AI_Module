from odoo import models, fields, api

class CRMLead(models.Model):
    _inherit = 'crm.lead'

    def action_log_call(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Call',
            'view_mode': 'form',
            'res_model': 'crm.call.log',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_salesperson_id': self.env.user.id,
            }
        }

    def action_open_questionnaire(self):  # <-- This must be INSIDE the class
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Client Questionnaire',
            'view_mode': 'form',
            'res_model': 'crm.lead.questionnaire',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
            }
        }
