import logging
from odoo import http
from odoo.http import request
from supabase import create_client, Client

_logger = logging.getLogger(__name__)

# Replace these with your actual Supabase credentials
SUPABASE_URL = "https://zodbnolhtcemthbjttab.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpvZGJub2xodGNlbXRoYmp0dGFiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ5NzE4MjMsImV4cCI6MjA1MDU0NzgyM30.bkW3OpxY1_IwU01GwybxHfrQQ9t3yFgLZVi406WvgVI"

# Create the Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class UsersController(http.Controller):

    @http.route('/supabase/users/view', type='http', auth='public', website=True)
    def view_supabase_users(self, **kwargs):
        # Fetch all records from the "users" table in Supabase
        result = supabase.table('users').select('*').execute()
        if result.error:
            _logger.error("Error fetching Supabase users: %s", result.error.message)
            users = []
        else:
            users = result.data
            _logger.info("Fetched %s users from Supabase", len(users))
        # Render the QWeb template and pass the list of users
        return request.render('feedback_module.supabase_users_template', {'users': users})
