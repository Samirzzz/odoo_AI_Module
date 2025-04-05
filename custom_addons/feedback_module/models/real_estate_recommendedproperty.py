from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json

class RealEstateRecommendedProperty(models.Model):
    _name = 'real_estate_recommendedproperty'
    _description = 'Recommended Properties'

    user_id = fields.Many2one('users.users', string='User', required=True)
    recommended_property_details_ids = fields.One2many(
        'recommended.property.details',
        'recommendation_id',
        string='Recommended Property Details'
    )

    # Sentiment Analysis Fields
    overall_sentiment = fields.Char(string='Overall Sentiment', readonly=True)
    overall_confidence = fields.Float(string='Overall Confidence', readonly=True)
    size_sentiment = fields.Char(string='Size Sentiment', readonly=True)
    size_confidence = fields.Float(string='Size Confidence', readonly=True)
    price_sentiment = fields.Char(string='Price Sentiment', readonly=True)
    price_confidence = fields.Float(string='Price Confidence', readonly=True)
    location_sentiment = fields.Char(string='Location Sentiment', readonly=True)
    location_confidence = fields.Float(string='Location Confidence', readonly=True)
    cleanliness_sentiment = fields.Char(string='Cleanliness Sentiment', readonly=True)
    cleanliness_confidence = fields.Float(string='Cleanliness Confidence', readonly=True)
    maintenance_sentiment = fields.Char(string='Maintenance Sentiment', readonly=True)
    maintenance_confidence = fields.Float(string='Maintenance Confidence', readonly=True)
    amenities_sentiment = fields.Char(string='Amenities Sentiment', readonly=True)
    amenities_confidence = fields.Float(string='Amenities Confidence', readonly=True)

    # Extracted Entities Fields
    extracted_size = fields.Char(string='Extracted Size', readonly=True)
    extracted_price = fields.Char(string='Extracted Price', readonly=True)
    extracted_location = fields.Char(string='Extracted Location', readonly=True)
    extracted_cleanliness = fields.Char(string='Extracted Cleanliness', readonly=True)
    extracted_maintenance = fields.Char(string='Extracted Maintenance', readonly=True)
    extracted_amenities = fields.Char(string='Extracted Amenities', readonly=True)

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

    def action_request_prediction(self):
        """Make API request to the preprocessmodel endpoint and store results"""
        try:
            url = "https://preprocessmodel.fly.dev/predict"
            headers = {'Content-Type': 'application/json'}
            data = {
                "review": "The apartment was clean and spacious but a bit pricey.",
                "property_id": 102,
                "user_id": str(self.user_id.id),
                "review_number": 1
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            result = response.json()

            # Update sentiment analysis fields
            sentiment = result.get('sentiment_analysis', {})
            self.write({
                'overall_sentiment': sentiment.get('full_review_sentiment'),
                'overall_confidence': sentiment.get('full_review_confidence', 0),
                'size_sentiment': sentiment.get('size_sentiment'),
                'size_confidence': sentiment.get('size_confidence', 0),
                'price_sentiment': sentiment.get('price_sentiment'),
                'price_confidence': sentiment.get('price_confidence', 0),
                'location_sentiment': sentiment.get('location_sentiment'),
                'location_confidence': sentiment.get('location_confidence', 0),
                'cleanliness_sentiment': sentiment.get('cleanliness_sentiment'),
                'cleanliness_confidence': sentiment.get('cleanliness_confidence', 0),
                'maintenance_sentiment': sentiment.get('maintenance_sentiment'),
                'maintenance_confidence': sentiment.get('maintenance_confidence', 0),
                'amenities_sentiment': sentiment.get('amenities_sentiment'),
                'amenities_confidence': sentiment.get('amenities_confidence', 0),
            })

            # Update extracted entities fields
            entities = result.get('extracted_entities', {})
            self.write({
                'extracted_size': entities.get('size', 'N/A'),
                'extracted_price': entities.get('price', 'N/A'),
                'extracted_location': entities.get('location', 'N/A'),
                'extracted_cleanliness': entities.get('cleanliness', 'N/A'),
                'extracted_maintenance': entities.get('maintenance', 'N/A'),
                'extracted_amenities': entities.get('amenities', 'N/A'),
            })

            # Create or update recommended properties
            recommendations = result.get('recommendations', {}).get('recommendations', [])
            # Clear existing recommendations
            self.recommended_property_details_ids.unlink()
            
            for rec in recommendations:
                self.create_recommended_detail(
                    int(rec['property_id']),
                    float(rec['similarity_score'])
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
            
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error making API request: {str(e)}")

class RecommendedPropertyDetails(models.Model):
    _name = 'recommended.property.details'
    _description = 'Recommended Property Details'

    recommendation_id = fields.Many2one('real_estate_recommendedproperty', string='Recommendation')
    property_id = fields.Many2one('real.estate.property', string='Property')
    score = fields.Float(string='Score')
