from odoo import models, fields, api

class PropertyRecommendation(models.Model):
    _name = 'property.recommendation'
    _description = 'Property Recommendation'
    _order = 'recommendation_date desc'

    # Core fields
    name = fields.Char(string='Recommendation Title', required=True, index=True)
    recommendation_date = fields.Datetime(string='Recommendation Date', default=fields.Datetime.now, index=True)
    user_id = fields.Many2one('res.users', string='User', required=True, index=True)
    
    # Property related fields
    recommended_property_id = fields.Char(string='Recommended Property', index=True)
    feedback_property_id = fields.Char(string='Feedback Property ID', required=True, index=True)
    feedback_property_name = fields.Char(string='Property Name', required=True, index=True)
    
    # Feedback
    feedback = fields.Text(string='Feedback', required=True)

            