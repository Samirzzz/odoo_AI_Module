from odoo import models, fields, api

class RealEstateClusters(models.Model):
    _name = 'real.estate.clusters'
    _description = 'Real Estate Clusters'
    _rec_name = 'name'

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
    user_ids = fields.One2many('users.users', 'cluster_id', string='Users')
    
    recommended_details_ids = fields.Many2many(
        comodel_name='real_estate_recommendedpropertiesdetails',
        compute='_compute_recommended_details',
        string='Recommended Property Details'
    )

    # Computed fields
    user_count = fields.Integer(string='Number of Users', compute='_compute_counts')
    
    @api.depends('user_ids')
    def _compute_counts(self):
        for record in self:
            record.user_count = len(record.user_ids)

    def _compute_recommended_details(self):
        for cluster in self:
            properties_in_cluster = self.env['real.estate.property'].search([('cluster_id', '=', cluster.id)])
            if properties_in_cluster:
                details = self.env['real_estate_recommendedpropertiesdetails'].search([
                    ('property_id', 'in', properties_in_cluster.ids)
                ])
                cluster.recommended_details_ids = [(6, 0, details.ids)]
            else:
                cluster.recommended_details_ids = False 