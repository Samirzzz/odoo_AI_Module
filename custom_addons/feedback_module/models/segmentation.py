from odoo import models, fields, api

class PropertySegmentation(models.Model):
    _name = 'property.segmentation'
    _description = 'Property Segmentation'
    _rec_name = 'name'

    cluster_id = fields.Integer(string='Cluster ID', required=True)
    name = fields.Char(string='Cluster Name', required=True)
    description = fields.Text(string='Description')
    message = fields.Text(string='Message')
    
    # Size and Demographics
    size = fields.Integer(string='Cluster Size')
    avg_age = fields.Float(string='Average Age')
    avg_favorites = fields.Float(string='Average Favorites')
    common_job = fields.Char(string='Common Job')
    common_country = fields.Char(string='Common Country')
    
    # Property Preferences
    avg_favorited_area = fields.Float(string='Average Favorited Area')
    avg_favorited_bedrooms = fields.Float(string='Average Favorited Bedrooms')
    avg_favorited_price = fields.Float(string='Average Favorited Price')
    favorite_property_type = fields.Char(string='Favorite Property Type')
    favorite_city = fields.Char(string='Favorite City')
    favorite_sale_rent = fields.Char(string='Favorite Sale/Rent')
    
    # Preferences
    furnished_preference = fields.Float(string='Furnished Preference')
    sale_preference = fields.Float(string='Sale Preference')
    avg_installment_years = fields.Float(string='Average Installment Years')
    avg_delivery_time = fields.Float(string='Average Delivery Time')
    preferred_finishing = fields.Char(string='Preferred Finishing')
    
    # Related fields
    property_ids = fields.Many2many('real.estate.property', string='Properties')
    user_ids = fields.Many2many('res.users', string='Users')
    
    # Computed fields
    property_count = fields.Integer(string='Number of Properties', compute='_compute_counts')
    user_count = fields.Integer(string='Number of Users', compute='_compute_counts')
    
    @api.depends('property_ids', 'user_ids')
    def _compute_counts(self):
        for record in self:
            record.property_count = len(record.property_ids)
            record.user_count = len(record.user_ids) 