from odoo import models, fields

class UsersTest(models.Model):
    _name = 'users.test'  # This should match the model_id in the CSV
    _description = 'Users Test'

    name = fields.Char(string='Name')
