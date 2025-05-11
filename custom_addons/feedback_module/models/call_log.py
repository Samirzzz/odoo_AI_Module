from odoo import models, fields, api

class FeedbackCallLog(models.Model):
    _name = 'feedback.call.log'
    _description = 'Feedback Call Log'

    lead_id = fields.Many2one('crm.lead', string="Lead", required=True)
    feedback_id = fields.Many2one('real.estate.feedback', string="Feedback")
    call_description = fields.Text(string="Call Description")
    call_time = fields.Datetime(string="Call Time", default=fields.Datetime.now)
    salesperson_id = fields.Many2one('res.users', string="Salesperson", default=lambda self: self.env.user)
    
    # 📞 Add audio recording field
    call_recording = fields.Binary(string="Call Recording")
    recording_filename = fields.Char(string="File Name")  # To store filename

    @api.onchange('call_recording')
    def _onchange_call_recording(self):
        """When an audio file is uploaded, open the questionnaire form"""
        if self.call_recording and self.lead_id:
            # We need to save the record first because it's a new record
            # Since we can't return a redirect from onchange, we'll set a flag to open questionnaire
            self.env.context = dict(self.env.context, open_questionnaire=True)
            return {
                'warning': {
                    'title': 'Audio Uploaded',
                    'message': 'Audio file uploaded successfully. Questionnaire will open after saving.'
                }
            }
    
    def create(self, vals):
        """Override create to handle questionnaire redirect after saving"""
        record = super(FeedbackCallLog, self).create(vals)
        if self.env.context.get('open_questionnaire') and record.lead_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Client Questionnaire',
                'view_mode': 'form',
                'res_model': 'feedback.lead.questionnaire',
                'target': 'new',
                'context': {
                    'default_lead_id': record.lead_id.id,
                    'default_call_log_id': record.id,
                }
            }
        return record
        
    def action_open_questionnaire(self):
        """Open the client questionnaire form"""
        self.ensure_one()
        if not self.lead_id:
            return {
                'warning': {
                    'title': 'Error',
                    'message': 'No lead associated with this call log.'
                }
            }
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Client Questionnaire',
            'view_mode': 'form',
            'res_model': 'feedback.lead.questionnaire',
            'target': 'new',
            'context': {
                'default_lead_id': self.lead_id.id,
                'default_call_log_id': self.id,
            }
        } 