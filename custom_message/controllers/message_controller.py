print("🔥 CustomMessageController loaded!")
from odoo import http
from odoo.http import request

class CustomMessageController(http.Controller):

    @http.route('/crm/messages/<int:lead_id>', auth='none', type='json', methods=['GET'], csrf=False)
    def get_messages_for_lead(self, lead_id):
        print("📩 GET /crm/messages hit with lead_id:", lead_id)
        messages = request.env['mail.message'].sudo().search([
            ('res_id', '=', lead_id),
            ('model', '=', 'crm.lead')
        ], order='create_date asc')

        return [{
            'author': msg.author_id.name if msg.author_id else 'Unknown',
            'body': msg.body,
            'date': msg.date
        } for msg in messages]
