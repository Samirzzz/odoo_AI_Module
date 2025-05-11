from odoo import models, fields

class CRMCallLog(models.Model):
    _name = 'crm.call.log'
    _description = 'CRM Call Log'

    lead_id = fields.Many2one('crm.lead', string="Lead", required=True)
    feedback_id = fields.Many2one('real.estate.feedback', string="Feedback")
    call_description = fields.Text(string="Call Description")
    call_time = fields.Datetime(string="Call Time", default=fields.Datetime.now)
    salesperson_id = fields.Many2one('res.users', string="Salesperson", default=lambda self: self.env.user)
    
    # 📞 Add audio recording field
    call_recording = fields.Binary(string="Call Recording")
    recording_filename = fields.Char(string="File Name")  # To store filename
