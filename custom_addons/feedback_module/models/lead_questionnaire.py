from odoo import models, fields, api
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class FeedbackLeadQuestionnaire(models.Model):
    _name = 'feedback.lead.questionnaire'
    _description = 'Client Questionnaire for Feedback Module'

    name = fields.Char(string="Name", required=True, default=lambda self: self.env['ir.sequence'].next_by_code('feedback.lead.questionnaire'))
    lead_id = fields.Many2one('crm.lead', string="Lead", required=True)
    call_log_id = fields.Many2one('feedback.call.log', string="Related Call Log")
    feedback_id = fields.Many2one('real.estate.feedback', string="Related Feedback")
    
    # Property Details
    property_type = fields.Char(string="Property Type")
    bedrooms = fields.Integer(string="Number of Bedrooms")
    bathrooms = fields.Integer(string="Number of Bathrooms")
    area = fields.Float(string="Area (sq.m)", help="Desired property area in square meters")
    unit_type = fields.Char(string="Unit Type")
    
    # Financial Details
    min_price = fields.Float(string="Minimum Price")
    max_price = fields.Float(string="Maximum Price")
    payment_option = fields.Selection([
        ('cash', 'Cash'),
        ('installment', 'Installment')
    ], string="Payment Option")
    installment_years = fields.Float(string="Installment Years")
    down_payment = fields.Float(string="Down Payment")
    
    # Location and Features
    city = fields.Char(string="City")
    features = fields.Text(string="Required Features")
    finishing_type = fields.Char(string="Finishing Type")
    delivery_in = fields.Float(string="Delivery Timeline (Years)")
    
    # Meeting Details
    meeting_agreed = fields.Boolean(string="Meeting Agreed")
    meeting_scheduled_info = fields.Char(string="Meeting Scheduled Info")
    meeting_scheduled = fields.Boolean(string="Meeting Scheduled")
    meeting_datetime = fields.Datetime(string="Meeting Date & Time")
    
    # Additional Information
    notes = fields.Text(string="Additional Notes")
    recommended_properties = fields.Html(string="Recommended Properties", readonly=True)
    
    # Related fields from call log
    call_inference_status = fields.Selection(related="call_log_id.inference_status", string="Inference Status", readonly=True)
    call_inference_language = fields.Char(related="call_log_id.inference_language", string="Detected Language", readonly=True)
    call_inference_transcript = fields.Text(related="call_log_id.inference_transcript", string="Transcription", readonly=True)
    call_inference_translation = fields.Text(related="call_log_id.inference_translation", string="Translation", readonly=True)
    call_inference_rephrased = fields.Text(related="call_log_id.inference_rephrased", string="Rephrased Text", readonly=True)
    
    @api.onchange('meeting_scheduled')
    def _onchange_meeting_scheduled(self):
        """When meeting_scheduled is turned off, clear the meeting datetime"""
        if not self.meeting_scheduled:
            self.meeting_datetime = False

    @api.onchange('max_price')
    def _onchange_max_price(self):
        """Update min_price when max_price changes"""
        if self.max_price:
            self.min_price = self.max_price * 0.75
        else:
            self.min_price = 0

    def action_generate_property_recommendations(self):
        self.ensure_one()
        
        # Check if we have enough data
        if not self.property_type or not self.bedrooms or not self.max_price:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Missing Information',
                    'message': 'Please fill in at least property type, number of bedrooms, and maximum price.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Build query text for semantic search
        query_parts = []
        if self.property_type: query_parts.append(f"Property type: {self.property_type}")
        if self.city: query_parts.append(f"Location: {self.city}")
        if self.bedrooms: query_parts.append(f"{self.bedrooms} bedrooms")
        if self.features: query_parts.append(f"Features: {self.features}")
        if self.unit_type: query_parts.append(f"Unit type: {self.unit_type}")
        query_text = ". ".join(query_parts) if query_parts else "property"
        
        # Build filters
        filters = {
            'price': {
                '$gte': self.min_price or 0,
                '$lte': self.max_price
            },
            'bedrooms': {
                '$eq': self.bedrooms
            },
            'type': {
                '$eq': self.property_type.lower()
            }
        }
        
        if self.city:
            filters['city'] = {'$eq': self.city.lower()}
        if self.unit_type:
            filters['unit_type'] = {'$eq': self.unit_type.lower()}
        
        try:
            # Initialize the search service
            search_service = PropertyVectorSearch(self.env)
            
            # Search for properties
            properties = search_service.search_properties(
                query_text=query_text,
                filters=filters,
                top_k=5
            )
            
            # Format the results as HTML
            html = search_service.format_properties_as_html(properties)
            
            # Update the form with the results
            self.write({'recommended_properties': html})
            
            # Return success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Search Complete',
                    'message': f"Found {len(properties.get('matches', []))} matching properties.",
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error generating property recommendations: {str(e)}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f"Failed to generate recommendations: {str(e)}",
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_save_and_stay(self):
        """Save the record and keep the form open."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'mode': 'edit'},
        }

    def action_view_call_log(self):
        """Navigate to the related call log."""
        self.ensure_one()
        if not self.call_log_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'No call log associated with this questionnaire.',
                    'type': 'danger',
                }
            }
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Call Log',
            'res_model': 'feedback.call.log',
            'res_id': self.call_log_id.id,
            'view_mode': 'form',
            'target': 'current',
        } 