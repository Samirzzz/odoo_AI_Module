from odoo import models, fields, api

class PropertyRecommendation(models.Model):
        _name = 'property.recommendation'
        _description = 'Property Recommendation'

        name = fields.Char(string='Recommendation Title', required=True)
        id = fields.Char(string='ID', readonly=True, copy=False, default='New')
        
        customer_id = fields.Many2one( string='Customer', required=True)
        customer_name = fields.Char( string='Customer Name', store=True)
        
        recommendation_date = fields.Datetime(string='Recommendation Date', default=fields.Datetime.now)
        feedback = fields.Text(string='Customer Feedback', required=True)
        
        # recommended_property_id = fields.Many2one('crm.lead', string='Recommended Property', required=False)
        recommended_property_id = fields.Char(string='Recommended Property')

        feedback_property_id = fields.Char(string='Feedback Property ID', required=True)
        feedback_property_name = fields.Char(string='Property Name', required=True)
