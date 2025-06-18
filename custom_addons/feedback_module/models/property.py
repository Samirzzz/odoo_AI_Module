from odoo import models, fields, api

class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _description = 'Real Estate Property'

    name = fields.Char(string='Name')
    price = fields.Float(string='Price')
    bedrooms = fields.Integer(string='Bedrooms')
    bathrooms = fields.Integer(string='Bathrooms')
    level = fields.Float(string='Level')
    type = fields.Char(string='Type')
    furnished = fields.Char(string='Furnished')
    compound = fields.Char(string='Compound')
    payment_option = fields.Char(string='Payment Option')
    city = fields.Char(string='City')
    status = fields.Char(string='Status')
    sale_rent = fields.Char(string='Sale/Rent')
    img_url = fields.Text(string='Image URLs')
    area = fields.Float(string='Area')
    user_id = fields.Many2one('users.users', string='Owner', ondelete='set null')
    down_payment = fields.Char(string='Down Payment')
    installment_years = fields.Integer(string='Installment Years')
    delivery_in = fields.Integer(string='Delivery In (Months)')
    finishing = fields.Char(string='Finishing')
    amenities = fields.Text(string='Amenities')
    cluster_id = fields.Many2one('real.estate.clusters', string='Cluster', ondelete='set null')
    cluster_score = fields.Float(string='Cluster Score')
    create_uid = fields.Many2one('res.users', string='Created by', ondelete='set null')
    write_uid = fields.Many2one('res.users', string='Last Updated by', ondelete='set null')
    create_date = fields.Datetime(string='Created on')
    write_date = fields.Datetime(string='Last Updated on')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            property_type = vals.get('type', 'Property')
            city = vals.get('city', 'Unknown City')
            vals['name'] = f"{property_type.capitalize()} in {city}"
        return super(RealEstateProperty, self).create(vals)

    def write(self, vals):
        for record in self:
            if not vals.get('name') and not record.name:
                property_type = vals.get('type', record.type or 'Property')
                city = vals.get('city', record.city or 'Unknown City')
                vals['name'] = f"{property_type.capitalize()} in {city}"
        return super(RealEstateProperty, self).write(vals)

    def init(self):
        # Drop any existing selection data
        self.env.cr.execute("""
            DELETE FROM ir_model_fields_selection 
            WHERE field_id IN (
                SELECT id FROM ir_model_fields 
                WHERE model = 'real.estate.property' 
                AND name IN ('type', 'furnished', 'payment_option', 'status', 'sale_rent', 'finishing')
            );
        """)
