from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    property_feedback = fields.Text(string="Property Feedback")
