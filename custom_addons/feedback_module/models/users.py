import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.parser import parse as parse_datetime  # Ensure python-dateutil is installed

def _parse_datetime(self, datetime_str):
    """Parse ISO datetime string to a datetime object."""
    if not datetime_str or datetime_str.strip() == '':
        return False
    try:
        dt = parse_datetime(datetime_str)
        return dt  # Return full datetime instead of dt.date()
    except Exception as e:
        _logger.warning(f"Could not parse datetime string: {datetime_str}, error: {e}")
        return False

_logger = logging.getLogger(__name__)

class Users(models.Model):
    _name = 'users.users'
    _description = 'Users'
    _rec_name = 'email'  # Use email as the display name

    name = fields.Char(compute='_compute_name', store=True)
    firstname = fields.Char(string='First Name', required=True)
    lastname = fields.Char(string='Last Name', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Phone')
    country = fields.Char(string='Country')
    job = fields.Char(string='Job')
    dob = fields.Date(string='Date of Birth')
    role = fields.Char(string='Role')
    
    cluster_id = fields.Many2one('real.estate.clusters', string='Cluster')
    
    # One2many field linking to recommended properties
    real_estate_recommendedproperty_ids = fields.One2many(
        'real_estate_recommendedproperty',
        'user_id',
        string='Recommended Properties'
    )

    # One2many field linking to feedback records
    feedback_ids = fields.One2many('real.estate.feedback', 'user_id', string='Feedbacks')

    _sql_constraints = [
        ('email_unique', 'unique(email)', 'Email must be unique!')
    ]

    @api.depends('firstname', 'lastname')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.firstname} {record.lastname}"

    def _parse_datetime(self, datetime_str):
        """Helper method to parse datetime strings"""
        if not datetime_str:
            return False
        
        try:
            return datetime.datetime.strptime(datetime_str, '%Y-%m-%d').date()
        except ValueError as e:
            _logger.warning(f"Could not parse datetime string: {datetime_str}, error: {e}")
            return False

    @api.model
    def create(self, vals):
        """Override create to handle date parsing"""
        if vals.get('dob'):
            dob_val = vals.get('dob')
            if isinstance(dob_val, str):
                parsed_date = self._parse_datetime(dob_val)
                vals['dob'] = parsed_date if parsed_date else False
        return super(Users, self).create(vals)

    def write(self, vals):
        """Override write to handle date parsing"""
        if vals.get('dob'):
            dob_val = vals.get('dob')
            if isinstance(dob_val, str):
                parsed_date = self._parse_datetime(dob_val)
                vals['dob'] = parsed_date if parsed_date else False
        return super(Users, self).write(vals)

    def action_insert_feedbacks(self):
        """
        Create a feedback record for each user.
        For each user, we assign a default property (ensure at least one property exists).
        Adjust the feedback text or logic as needed.
        """
        feedback_obj = self.env['real.estate.feedback']
        default_property = self.env['real.estate.property'].search([], limit=1)
        if not default_property:
            raise UserError(_("No property available to assign feedback."))
        for user in self:
            # Optionally, check if a feedback already exists for the user.
            if not user.feedback_ids:
                feedback_obj.create({
                    'feedback': f"This is a feedback for {user.name}.",
                    'property_id': default_property.id,
                    'user_id': user.id,
                })
        return True

    def import_users(self, users_data):
        """Import users from Excel data"""
        if not users_data:
            return False

        for user_data in users_data:
            # Check if user already exists
            existing_user = self.search([('email', '=', user_data.get('email'))], limit=1)
            
            if existing_user:
                # Update existing user
                existing_user.write({
                    'firstname': user_data.get('firstname'),
                    'lastname': user_data.get('lastname'),
                    'phone': user_data.get('phone'),
                    'country': user_data.get('country'),
                    'job': user_data.get('job'),
                    'dob': user_data.get('dob'),
                })
            else:
                # Create new user
                self.create({
                    'firstname': user_data.get('firstname'),
                    'lastname': user_data.get('lastname'),
                    'email': user_data.get('email'),
                    'phone': user_data.get('phone'),
                    'country': user_data.get('country'),
                    'job': user_data.get('job'),
                    'dob': user_data.get('dob'),
                })
        return True

    def name_get(self):
        """Override name_get to display email as the record name"""
        result = []
        for user in self:
            display_name = f"{user.email} ({user.name})" if user.name else user.email
            result.append((user.id, display_name))
        return result
