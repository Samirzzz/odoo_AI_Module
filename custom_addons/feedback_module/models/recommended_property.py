from odoo import models, fields, api

class RealEstateRecommendedProperties(models.Model):
    _name = 'real_estate_recommendedproperties'
    _description = 'Real Estate Recommended Properties'

    user_id = fields.Many2one('users.users', string='User', required=True, ondelete='cascade')
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now)
    recommendation_type = fields.Char(string='Recommendation Type', size=255)

class RealEstateRecommendedPropertiesDetails(models.Model):
    _name = 'real_estate_recommendedpropertiesdetails'
    _description = 'Real Estate Recommended Properties Details'

    recommendation_id = fields.Many2one('real_estate_recommendedproperties', string='Recommendation', required=True, ondelete='cascade')
    property_id = fields.Many2one('real.estate.property', string='Property', required=True, ondelete='cascade')
    score = fields.Float(string='Score') 