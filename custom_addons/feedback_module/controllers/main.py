from odoo import http
from odoo.http import request
import json

class PropertyRecommendationController(http.Controller):

    @http.route('/property/recommendations', auth='public', type='json', methods=['POST'], csrf=False)
    def receive_recommendations(self, **post):
        data = json.loads(request.httprequest.data)
        user_id = data.get('user_id')
        recommendations = data.get('recommendations')

        for rec in recommendations:
            request.env['property.recommendation'].sudo().create({
                'name': rec.get('property_name'),
                'user_id': user_id,
                'feedback': rec.get('feedback'),
                'property_id': rec.get('property_id')
            })

        return {'status': 'success', 'message': 'Recommendations received successfully'}
