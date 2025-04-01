import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class Users(models.Model):
    _name = 'users.users'
    _description = 'Users'

    name = fields.Char(compute='_compute_name', store=True)
    firstname = fields.Char(string='First Name', required=True)
    lastname = fields.Char(string='Last Name', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Phone')
    country = fields.Char(string='Country')
    dob = fields.Date(string='Date of Birth', default=False)
    job = fields.Char(string='Job')
    role = fields.Char(string='Role')
    total_time_spent = fields.Float(string='Total Time Spent')
    idd = fields.Char(string='IDD')
    token = fields.Char(string='Token')
    password = fields.Char(string='Password')
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now)

    # One2many field linking to feedback records
    feedback_ids = fields.One2many('real.estate.feedback', 'user_id', string='Feedbacks')

    @api.depends('firstname', 'lastname')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.firstname or ''} {record.lastname or ''}".strip()

    def _parse_datetime(self, datetime_str):
        """Parse ISO datetime string to date object."""
        if not datetime_str or datetime_str == '':
            return False
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.date()
        except (ValueError, TypeError):
            _logger.warning(f"Could not parse datetime string: {datetime_str}")
            return False

    @api.model
    def create(self, vals):
        """Override create to handle the dob field properly."""
        if 'dob' in vals:
            dob_val = vals['dob']
            if isinstance(dob_val, str) and dob_val.strip() == '':
                vals['dob'] = False
            else:
                parsed_date = self._parse_datetime(dob_val)
                vals['dob'] = parsed_date if parsed_date else False
        return super(Users, self).create(vals)

    def write(self, vals):
        """Override write to handle the dob field properly."""
        if 'dob' in vals:
            dob_val = vals['dob']
            if isinstance(dob_val, str) and dob_val.strip() == '':
                vals['dob'] = False
            else:
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
