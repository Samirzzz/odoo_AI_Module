from odoo import models, fields, api
import json

class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _description = 'Real Estate Property'

    # -- DB columns --
    id                 = fields.Integer(string='ID', readonly=True)
    create_uid         = fields.Many2one('res.users', string='Created by', readonly=True, ondelete='set null')
    write_uid          = fields.Many2one('res.users', string='Last Updated by', readonly=True, ondelete='set null')
    create_date        = fields.Datetime(string='Created on', readonly=True)
    write_date         = fields.Datetime(string='Last Updated on', readonly=True)

    name               = fields.Char(string='Name')
    price              = fields.Float(string='Price')
    bedrooms           = fields.Integer(string='Bedrooms')
    bathrooms          = fields.Integer(string='Bathrooms')
    level              = fields.Float(string='Level')
    type               = fields.Char(string='Type')
    furnished          = fields.Char(string='Furnished')
    compound           = fields.Char(string='Compound')
    payment_option     = fields.Char(string='Payment Option')
    city               = fields.Char(string='City')
    status             = fields.Char(string='Status')
    sale_rent          = fields.Char(string='Sale/Rent')
    img_url            = fields.Text(string='Image URLs')
    area               = fields.Float(string='Area')
    user_id            = fields.Many2one('users.users', string='Owner', ondelete='set null')
    down_payment       = fields.Char(string='Down Payment')
    installment_years  = fields.Integer(string='Installment Years')
    delivery_in        = fields.Integer(string='Delivery In (Months)')
    finishing          = fields.Char(string='Finishing')
    amenities          = fields.Text(string='Amenities')
    cluster_id         = fields.Many2one('real.estate.clusters', string='Cluster')
    cluster_score      = fields.Float(string='Cluster Score')

    def get_image_urls(self):
        """Helper method to get image URLs as a Python list"""
        if not self.img_url:
            return []
        
        try:
            # Try to parse as JSON first
            urls = json.loads(self.img_url)
            return urls if isinstance(urls, list) else [urls]
        except (json.JSONDecodeError, TypeError):
            # If it's not JSON, treat as single URL
            return [self.img_url] if self.img_url else []

    def set_image_urls(self, urls):
        """Helper method to set image URLs from a Python list"""
        if isinstance(urls, list):
            self.img_url = json.dumps(urls)
        elif isinstance(urls, str):
            self.img_url = json.dumps([urls])
        else:
            self.img_url = json.dumps([])

    def add_image_url(self, url):
        """Helper method to add a single image URL"""
        current_urls = self.get_image_urls()
        if url not in current_urls:
            current_urls.append(url)
            self.set_image_urls(current_urls)

    def remove_image_url(self, url):
        """Helper method to remove a single image URL"""
        current_urls = self.get_image_urls()
        if url in current_urls:
            current_urls.remove(url)
            self.set_image_urls(current_urls)

    # -- Optional: auto‑name logic --
    @api.model
    def create(self, vals):
        if not vals.get('name'):
            ptype = vals.get('type', 'Property')
            city  = vals.get('city', 'Unknown City')
            vals['name'] = f"{ptype.capitalize()} in {city}"
        
        # Convert img_url to JSON array format if needed
        if 'img_url' in vals and vals['img_url']:
            if isinstance(vals['img_url'], list):
                vals['img_url'] = json.dumps(vals['img_url'])
            elif isinstance(vals['img_url'], str) and not vals['img_url'].startswith('['):
                # If it's a single URL string, convert to array
                vals['img_url'] = json.dumps([vals['img_url']])
        
        return super().create(vals)

    def write(self, vals):
        for record in self:
            if not vals.get('name') and not record.name:
                ptype = vals.get('type', record.type or 'Property')
                city  = vals.get('city', record.city or 'Unknown City')
                vals['name'] = f"{ptype.capitalize()} in {city}"
        
        # Convert img_url to JSON array format if needed
        if 'img_url' in vals and vals['img_url']:
            if isinstance(vals['img_url'], list):
                vals['img_url'] = json.dumps(vals['img_url'])
            elif isinstance(vals['img_url'], str) and not vals['img_url'].startswith('['):
                # If it's a single URL string, convert to array
                vals['img_url'] = json.dumps([vals['img_url']])
        
        return super().write(vals)

    @api.model
    def load(self, fields, data):
        # Fields to map by database ID instead of name/external ID
        id_map_fields = ['cluster_id', 'user_id']

        for field_name in id_map_fields:
            if field_name in fields:
                field_index = fields.index(field_name)
                # Tell Odoo to map this column to the database ID (/.id) of the relational field
                fields[field_index] = f'{field_name}/.id'
                for row in data:
                    if len(row) > field_index and row[field_index]:
                        try:
                            # Convert float strings like "2.0" to an integer string "2"
                            row[field_index] = str(int(float(row[field_index])))
                        except (ValueError, TypeError):
                            # If conversion fails, the default Odoo importer will
                            # catch and report the error for the specific row.
                            pass

        # Handle img_url field conversion during import
        if 'img_url' in fields:
            img_url_index = fields.index('img_url')
            for row in data:
                if len(row) > img_url_index and row[img_url_index]:
                    try:
                        # Try to parse as JSON first
                        parsed = json.loads(row[img_url_index])
                        if isinstance(parsed, list):
                            row[img_url_index] = json.dumps(parsed)
                        else:
                            row[img_url_index] = json.dumps([str(parsed)])
                    except (json.JSONDecodeError, TypeError):
                        # If it's not JSON, treat as single URL and convert to array
                        row[img_url_index] = json.dumps([str(row[img_url_index])])
                            
        return super().load(fields, data)

    def init(self):
        # Convert existing img_url data to JSON array format
        self.env.cr.execute("""
            UPDATE real_estate_property 
            SET img_url = CASE 
                WHEN img_url IS NULL OR img_url = '' THEN '[]'
                WHEN img_url LIKE '[%' AND img_url LIKE '%]' THEN img_url
                ELSE '["' || replace(img_url, '"', '\\"') || '"]'
            END
            WHERE img_url IS NOT NULL
        """)
        
        # Clean up any old selections on the six picklist fields
        self.env.cr.execute("""
            DELETE FROM ir_model_fields_selection 
             WHERE field_id IN (
               SELECT id FROM ir_model_fields 
                WHERE model = 'real.estate.property' 
                  AND name IN (
                    'type','furnished','payment_option',
                    'status','sale_rent','finishing'
                  )
             )
        """)
