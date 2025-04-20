from odoo import models, fields, api

class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _description = 'Real Estate Property'

    name = fields.Char(string='Property Name')
    type = fields.Selection([
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('studio', 'Studio'),
        ('twinhouse', 'Twinhouse'),
        ('penthouse', 'Penthouse'),
        ('duplex', 'Duplex'),
        ('standalone villa', 'Standalone Villa'),
        ('motel', 'Motel'),
        ('chalet', 'Chalet')
    ], string='Type')
    price = fields.Float(string='Price')
    bedrooms = fields.Integer(string='Bedrooms')
    bathrooms = fields.Integer(string='Bathrooms')
    area = fields.Float(string='Area (sqm)')
    furnished = fields.Selection([
        ('furnished', 'Furnished'),
        ('semi_furnished', 'Semi-Furnished'),
        ('unfurnished', 'Unfurnished'),
        ('unknown', 'Unknown'),
        ('no', 'No'),
        ('yes', 'Yes')
    ], string='Furnished Status')
    level = fields.Float(string='Level')
    compound = fields.Char(string='Compound')
    payment_option = fields.Char(string='Payment Option')
    city = fields.Char(string='City')
    img_url = fields.Text(string='Image URL')
    # Change the field name from customer_id to user_id
    user_id = fields.Many2one('users.users', string='User', required=False)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('approved', 'Approved')
    ], string='Status')
    sale_rent = fields.Selection([
        ('sale', 'Sale'),
        ('rent', 'Rent')
    ], string='Sale or Rent')

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
