import logging
from odoo import models, fields
from supabase import create_client, Client
from datetime import datetime

_logger = logging.getLogger(__name__)

# Replace these with your actual Supabase credentials
SUPABASE_URL = "https://zodbnolhtcemthbjttab.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpvZGJub2xodGNlbXRoYmp0dGFiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ5NzE4MjMsImV4cCI6MjA1MDU0NzgyM30.bkW3OpxY1_IwU01GwybxHfrQQ9t3yFgLZVi406WvgVI"

# Create the Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class Users(models.Model):
    _name = 'users.users'
    _description = 'Users from Supabase and WebAuthn Demo'

    # Fields corresponding to your Supabase table (example fields)
    created_at = fields.Datetime(string='Created At')
    country = fields.Char(string='Country')
    dob = fields.Char(string='Date of Birth')
    job = fields.Char(string='Job')
    firstname = fields.Char(string='First Name')
    lastname = fields.Char(string='Last Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    password = fields.Char(string='Password')
    idd = fields.Char(string='IDD')  # This field will store the unique ID from Supabase
    token = fields.Char(string='Token')
    role = fields.Integer(string='Role')
    total_time_spent = fields.Integer(string='Total Time Spent')

    # Computed field for display (concatenating first and last names)
    name = fields.Char(string='Name', compute='_compute_name', store=True)

    def _compute_name(self):
        for record in self:
            record.name = f"{record.firstname or ''} {record.lastname or ''}".strip()

    def _parse_datetime(self, date_str):
        """Parse ISO format datetime string to Odoo datetime format."""
        if not date_str:
            return False
        try:
            # Parse ISO format datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            _logger.error("Error parsing datetime %s: %s", date_str, str(e))
            return False

    def fetch_supabase_users(self):
        """Fetch data from Supabase and update/create corresponding Odoo records."""
        try:
            response = supabase.table('users').select('*').execute()
            
            # Check if any data was returned
            if not response or not hasattr(response, 'data'):
                _logger.error("Invalid response from Supabase: %s", response)
                return {'success': False, 'error': 'Invalid response from Supabase'}

            users_data = response.data
            if not users_data:
                _logger.error("No data returned from Supabase")
                return {'success': False, 'error': 'No data returned'}

            _logger.info("Fetched %s users from Supabase", len(users_data))
            
            for user_data in users_data:
                # Use the Supabase record's 'id' as a unique identifier.
                existing = self.search([('idd', '=', str(user_data.get('id')))], limit=1)
                vals = {
                    'created_at': self._parse_datetime(user_data.get('created_at')),
                    'country': user_data.get('country') or 'Unknown',
                    'dob': user_data.get('dob') or '',
                    'job': user_data.get('job') or 'Unknown',
                    'firstname': user_data.get('firstname') or '',
                    'lastname': user_data.get('lastname') or '',
                    'email': user_data.get('email') or '',
                    'phone': user_data.get('phone') or '',
                    'role': user_data.get('role'),
                    'total_time_spent': user_data.get('total_time_spent') or 0,
                    'idd': str(user_data.get('id')),
                }
                if existing:
                    existing.write(vals)
                else:
                    self.create(vals)

            # Return success with the updated records
            return {
                'success': True,
                'users': self.search_read([], ['firstname', 'lastname', 'email', 'phone', 'country', 'job', 'total_time_spent'])
            }
            
        except Exception as e:
            _logger.error("Exception when fetching Supabase users: %s", str(e))
            return {'success': False, 'error': str(e)}
