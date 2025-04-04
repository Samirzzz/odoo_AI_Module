from odoo import models, fields, api, _
from odoo.exceptions import UserError

class RealEstateRecommendedProperty(models.Model):
    _name = 'real_estate_recommendedproperty'
    _description = 'Real Estate Recommended Property'

    user_id = fields.Many2one('users.users', string='User', required=True)
    recommended_property_details_ids = fields.One2many(
        'recommended.property.details',
        'recommendation_id',
        string='Recommended Property Details'
    )

    def create_recommended_detail(self, property_id, score):
        """
        Create a recommended property detail record for this recommendation.
        :param property_id: ID of the property from real.estate.property.
        :param score: A float representing the recommendation score.
        """
        # Ensure the property exists
        property_obj = self.env['real.estate.property'].browse(property_id)
        if not property_obj:
            raise UserError(_("The selected property does not exist."))

        return self.env['recommended.property.details'].create({
            'recommendation_id': self.id,
            'property_id': property_id,
            'score': score,
        })

class RecommendedPropertyDetails(models.Model):
    _name = 'recommended.property.details'
    _description = 'Recommended Property Details'

    recommendation_id = fields.Many2one(
        'real_estate_recommendedproperty',
        string='Recommendation',
        required=True,
        ondelete='cascade'
    )
    property_id = fields.Many2one(
        'real.estate.property',
        string='Property',
        required=True
    )
    score = fields.Float(string='Score', required=True)
