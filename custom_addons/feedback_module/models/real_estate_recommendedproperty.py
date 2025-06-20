from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json

class RealEstateRecommendedProperty(models.Model):
    _name = 'real_estate_recommendedproperty'
    _description = 'Recommended Properties'

    user_id = fields.Many2one('users.users', string='User', required=True)
    # Related fields for user information
    user_email = fields.Char(related='user_id.email', string='Email', store=True)
    user_phone = fields.Char(related='user_id.phone', string='Phone', store=True)
    user_country = fields.Char(related='user_id.country', string='Country', store=True)
    user_job = fields.Char(related='user_id.job', string='Job', store=True)

    # Feedback fields
    feedback_id = fields.Many2one('real.estate.feedback', string='Selected Feedback')
    feedback_text = fields.Text(related='feedback_id.feedback', string='Feedback Text', readonly=True)

    # Add a computed field to show all feedbacks for this user
    available_feedback_ids = fields.Many2many(
        'real.estate.feedback',
        compute='_compute_available_feedbacks',
        string='Available Feedbacks'
    )

    property_id = fields.Many2one('real.estate.property', string='Property')

    recommended_property_details_ids = fields.One2many(
        'real_estate_recommendedpropertiesdetails',
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
    size_text = fields.Char(string='Extracted Size', readonly=True)
    price_text = fields.Char(string='Extracted Price', readonly=True)
    location_text = fields.Char(string='Extracted Location', readonly=True)
    cleanliness_text = fields.Char(string='Extracted Cleanliness', readonly=True)
    maintenance_text = fields.Char(string='Extracted Maintenance', readonly=True)
    amenities_text = fields.Char(string='Extracted Amenities', readonly=True)

    @api.depends('user_id')
    def _compute_available_feedbacks(self):
        """Compute available feedbacks for the selected user"""
        for record in self:
            if record.user_id:
                record.available_feedback_ids = self.env['real.estate.feedback'].search([
                    ('user_id', '=', record.user_id.id)
                ], order='id desc')
            else:
                record.available_feedback_ids = False

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """When user changes, automatically select their most recent feedback"""
        self.ensure_one()
        self.feedback_id = False  # Clear existing feedback
        if self.user_id:
            # Force refresh the available feedbacks
            self._compute_available_feedbacks()
            # Search for the most recent feedback for this user, ordered by ID desc
            latest_feedback = self.env['real.estate.feedback'].search([
                ('user_id', '=', self.user_id.id)
            ], order='id desc', limit=1)
            
            if latest_feedback:
                self.feedback_id = latest_feedback.id
            else:
                return {
                    'warning': {
                        'title': _('No Feedback Found'),
                        'message': _('No feedback found for this user.')
                    }
                }

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

        return self.env['real_estate_recommendedpropertiesdetails'].create({
            'recommendation_id': self.id,
            'property_id': property_id,
            'score': score,
        })

    def action_request_prediction(self):
        """Make API request to the preprocessmodel endpoint and store results"""
        if not self.user_id:
            raise UserError(_("Please select a user first."))

        if not self.feedback_id:
            raise UserError(_("No feedback found for this user."))

        try:
            url = "https://preprocessmodel.fly.dev/predict"
            headers = {'Content-Type': 'application/json'}
            data = {
                "review": self.feedback_text or "",
                "property_id": self.property_id.id if self.property_id else None,
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
            entities = result.get('entities', {})
            self.write({
                'size_text': entities.get('size', 'N/A'),
                'price_text': entities.get('price', 'N/A'),
                'location_text': entities.get('location', 'N/A'),
                'cleanliness_text': entities.get('cleanliness', 'N/A'),
                'maintenance_text': entities.get('maintenance', 'N/A'),
                'amenities_text': entities.get('amenities', 'N/A'),
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
