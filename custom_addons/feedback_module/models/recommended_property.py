import time
from odoo import models, fields, api

class RealEstateRecommendedProperties(models.Model):
    _name = 'real_estate_recommendedproperties'
    _description = 'Real Estate Recommended Properties'

    user_id = fields.Many2one('users.users', string='User', required=True, ondelete='cascade')
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now)
    recommendation_type = fields.Char(string='Recommendation Type', size=255)
    review_number = fields.Integer(string='Review Number')
    review_text = fields.Text(string='Review Text')
    
    # Review processing fields
    original_review = fields.Text(string='Original Review')
    translated_review = fields.Text(string='Translated Review')
    processed_review = fields.Text(string='Processed Review')
    
    # Sentiment analysis fields
    overall_sentiment = fields.Char(string='Overall Sentiment')
    overall_confidence = fields.Float(string='Overall Confidence')
    size_sentiment = fields.Char(string='Size Sentiment')
    size_confidence = fields.Float(string='Size Confidence')
    price_sentiment = fields.Char(string='Price Sentiment')
    price_confidence = fields.Float(string='Price Confidence')
    location_sentiment = fields.Char(string='Location Sentiment')
    location_confidence = fields.Float(string='Location Confidence')
    cleanliness_sentiment = fields.Char(string='Cleanliness Sentiment')
    cleanliness_confidence = fields.Float(string='Cleanliness Confidence')
    maintenance_sentiment = fields.Char(string='Maintenance Sentiment')
    maintenance_confidence = fields.Float(string='Maintenance Confidence')
    amenities_sentiment = fields.Char(string='Amenities Sentiment')
    amenities_confidence = fields.Float(string='Amenities Confidence')
    text_sentiment = fields.Char(string='Text Sentiment')
    text_confidence = fields.Float(string='Text Confidence')
    
    # Extracted entities fields
    size_text = fields.Char(string='Size Text')
    price_text = fields.Char(string='Price Text')
    location_text = fields.Char(string='Location Text')
    cleanliness_text = fields.Char(string='Cleanliness Text')
    maintenance_text = fields.Char(string='Maintenance Text')
    amenities_text = fields.Char(string='Amenities Text')
    entities_text = fields.Text(string='Entities Text')
    
    # Property details fields
    price = fields.Float(string='Price')
    size = fields.Float(string='Size')
    city = fields.Char(string='City')
    sale_rent = fields.Char(string='Sale/Rent')
    payment_type = fields.Char(string='Payment Type')

    details_ids = fields.One2many(
        comodel_name='real_estate_recommendedpropertiesdetails',
        inverse_name='recommendation_id',
        string='Recommended Details'
    )

    @api.model
    def load(self, fields, data):
        # Handle mapping user_id by database ID
        if 'user_id' in fields:
            user_id_index = fields.index('user_id')
            fields[user_id_index] = 'user_id/.id'
            for row in data:
                if len(row) > user_id_index and row[user_id_index]:
                    try:
                        row[user_id_index] = str(int(float(row[user_id_index])))
                    except (ValueError, TypeError):
                        pass

        # To prevent "found record of different model" errors, we forcibly
        # generate a unique external ID for every row, overriding any
        # 'id' column that might be in the import file.
        try:
            id_index = fields.index('id')
        except ValueError:
            # 'id' column does not exist, so add it
            id_index = len(fields)
            fields.append('id')
            for row in data:
                # Add a placeholder for the new column
                row.append('')

        # Now, populate the 'id' column with unique values
        for i, row in enumerate(data):
            ext_id = f"__import__.{self._name}_{int(time.time()*1000)}_{i}"
            row[id_index] = ext_id

        return super().load(fields, data)

class RealEstateRecommendedPropertiesDetails(models.Model):
    _name = 'real_estate_recommendedpropertiesdetails'
    _description = 'Real Estate Recommended Properties Details'

    recommendation_id = fields.Many2one('real_estate_recommendedproperty', string='Recommendation', required=True, ondelete='cascade')
    property_id = fields.Many2one('real.estate.property', string='Property', required=True, ondelete='cascade')
    score = fields.Float(string='Score')

    @api.model
    def load(self, fields, data):
        # --- Robust Import Logic ---
        
        # 1. Map relational fields by database ID
        id_map_fields = ['recommendation_id', 'property_id']
        for field_name in id_map_fields:
            if field_name in fields:
                field_index = fields.index(field_name)
                fields[field_index] = f'{field_name}/.id'
                for row in data:
                    if len(row) > field_index and row[field_index]:
                        try:
                            row[field_index] = str(int(float(row[field_index])))
                        except (ValueError, TypeError):
                            pass

        # 2. Generate unique external IDs to prevent conflicts
        try:
            id_index = fields.index('id')
        except ValueError:
            id_index = len(fields)
            fields.append('id')
            for row in data:
                row.append('')

        for i, row in enumerate(data):
            row[id_index] = f"__import__.{self._name}_{int(time.time()*1000)}_{i}"
            
        return super().load(fields, data) 