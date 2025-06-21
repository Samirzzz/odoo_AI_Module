# -*- coding: utf-8 -*-
import logging
import json
import requests

from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PropertyVectorSearch:
    """Property search service for recommendations."""
    
    def __init__(self, env):
        """Initialize with Odoo environment."""
        self.env = env
    
    def search_properties(self, query_text, filters=None, top_k=5):
        """Search for properties using the API endpoint."""
        try:
            # Prepare the request data
            request_data = {
                'query': query_text,
                'filters': filters or {},
                'top_k': top_k
            }
            
            # Make the API request
            response = requests.post(
                'http://localhost:8016/search',
                json=request_data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse and return the response
            result = response.json()
            _logger.info(f"API search response: {json.dumps(result, indent=2)}")
            return result
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"API request failed: {str(e)}")
            return {'matches': []}
        except Exception as e:
            _logger.error(f"Error in search_properties: {str(e)}")
            return {'matches': []}
    
    def format_properties_as_html(self, properties):
        """Format properties as HTML for display."""
        if not properties or not properties.get('matches'):
            return "<p class='text-muted'>No matching properties found.</p>"
            
        html = """
        <div class='property-recommendations mb-4' style='margin-top: 20px; padding: 10px; background-color: #f8f9fa;'>
            <h4 style='color: #4a4a4a; margin-bottom: 15px; border-bottom: 1px solid #dee2e6; padding-bottom: 10px;'>
                Found Properties ({count})
            </h4>
        """.format(count=len(properties['matches']))
        
        for prop in properties['matches']:
            # Format price with commas
            price = prop.get('price', 0)
            price_formatted = f"{float(price):,.0f}" if price else 'N/A'
            
            # Calculate match percentage
            score = float(prop.get('similarity_score', 0))
            match_pct = min(score * 100, 100)  # Cap at 100%
            
            # Set badge color based on match percentage
            badge_color = 'success' if match_pct > 80 else 'warning' if match_pct > 60 else 'danger'
            
            # Create a card for each property
            html += f"""
            <div class='property-card mb-3 p-3 border rounded' style='background-color: white; box-shadow: 0 3px 10px rgba(0,0,0,0.1); margin-bottom: 20px !important;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h5 class='property-title mb-0' style='font-weight: bold; color: #2c3e50; font-size: 1.2rem;'>{prop.get('type', 'Property')}</h5>
                    <span style='background-color: {"#28a745" if badge_color == "success" else "#ffc107" if badge_color == "warning" else "#dc3545"}; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold;'>{match_pct:.1f}% Match</span>
                </div>
                <hr style='margin: 10px 0; border-top: 1px solid #eee;'/>
                <div style='display: flex; flex-wrap: wrap;'>
                    <div style='flex: 1; min-width: 50%;'>
                        <p style='margin-bottom: 8px;'><strong style='color: #555;'>ID:</strong> <span style='color: #333;'>{prop.get('id', 'N/A')}</span></p>
                        <p style='margin-bottom: 8px;'><strong style='color: #555;'>Price:</strong> <span style='color: #333; font-weight: bold;'>{price_formatted} EGP</span></p>
                        <p style='margin-bottom: 8px;'><strong style='color: #555;'>Area:</strong> <span style='color: #333;'>{prop.get('area', 'N/A')} sq.m</span></p>
                    </div>
                    <div style='flex: 1; min-width: 50%;'>
                        <p style='margin-bottom: 8px;'><strong style='color: #555;'>Bedrooms:</strong> <span style='color: #333;'>{prop.get('bedrooms', 'N/A')}</span></p>
                        <p style='margin-bottom: 8px;'><strong style='color: #555;'>Bathrooms:</strong> <span style='color: #333;'>{prop.get('bathrooms', 'N/A')}</span></p>
                        <p style='margin-bottom: 8px;'><strong style='color: #555;'>City:</strong> <span style='color: #333;'>{prop.get('city', 'N/A')}</span></p>
                    </div>
                </div>
            """
            
            # Add amenities section if available
            if prop.get('amenities'):
                html += """
                <div style='margin-top: 10px;'>
                    <p style='margin-bottom: 8px;'><strong style='color: #555;'>Amenities:</strong></p>
                    <div style='display: flex; flex-wrap: wrap; gap: 5px;'>
                """
                for amenity in prop['amenities']:
                    html += f"<span style='background-color: #e9ecef; padding: 3px 8px; border-radius: 12px; font-size: 0.9em;'>{amenity}</span>"
                html += """
                    </div>
                </div>
                """
            
            html += "</div>"
        
        html += "</div>"
        return html


class FeedbackLeadQuestionnaire(models.Model):
    _inherit = 'feedback.lead.questionnaire'
    
    # Fields for property recommendations
    recommended_properties = fields.Html(
        string="Recommended Properties", 
        readonly=True,
        help="Property recommendations based on user preferences"
    )
    
    # Meeting agreement field
    meeting_agreed = fields.Boolean(
        string="Meeting Agreed",
        help="Whether the client agreed to a meeting"
    )

    # Change desired_years to Float
    desired_years = fields.Float(
        string="Desired Years to Receive Property",
        help="Number of years until the client wants to receive the property"
    )
    
    # Additional fields for 12-question format
    meeting_scheduled_info = fields.Char(
        string="Meeting Scheduled Info",
        help="Information about when the meeting was scheduled"
    )
    down_payment = fields.Char(
        string="Down Payment",
        help="Down payment percentage or amount"
    )
    preferred_finishing = fields.Char(
        string="Preferred Finishing",
        help="Client's preferred finishing type"
    )
    
    @api.model
    def _init_system_parameters(self):
        """Initialize system parameters for property vector search."""
        ICP = self.env['ir.config_parameter'].sudo()
        # Ensure default API key is an empty string if not set, forcing admin to configure.
        if not ICP.get_param('feedback_module.pinecone_api_key'): 
            ICP.set_param('feedback_module.pinecone_api_key', '')
            _logger.info("Pinecone API key system parameter initialized (empty). Please configure it.")
            
        if not ICP.get_param('feedback_module.pinecone_index'):
            ICP.set_param('feedback_module.pinecone_index', 'recommendation-index')
            
        if not ICP.get_param('feedback_module.embedding_model'):
            ICP.set_param('feedback_module.embedding_model', 'distilbert-base-uncased')
            
        return True
    
    @api.model
    def _register_hook(self):
        """Initialize system parameters on module install/upgrade."""
        self._init_system_parameters()
        return super()._register_hook()
        
    def action_generate_property_recommendations(self):
        """Generate property recommendations based on questionnaire data."""
        self.ensure_one()
        
        if not (self.property_type or self.max_price or self.city):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Missing Information',
                    'message': 'Please provide Property Type, Max Price, and City.',
                    'type': 'warning',
                    'sticky': False, # Added sticky false
                }
            }
        
        try:
            search_service = PropertyVectorSearch(self.env)
            
            query_parts = []
            if self.property_type: query_parts.append(f"Property type: {self.property_type}")
            if self.city: query_parts.append(f"Location: {self.city}")
            if self.bedrooms: query_parts.append(f"{self.bedrooms} bedrooms")
            if self.features: query_parts.append(f"Features: {self.features}")
            if self.unit_type: query_parts.append(f"Unit type: {self.unit_type}") # Added unit_type
                
            query_text = ". ".join(query_parts) if query_parts else "property"
            
            filters = {}
            if self.max_price and self.max_price > 0: # Ensure max_price is positive
                current_min_price = self.min_price # Relies on onchange having set this
                # If min_price is still 0 from onchange (e.g. max_price was 0 then changed),
                # and max_price is now positive, recalculate a sensible gte.
                if current_min_price == 0 and self.max_price > 0:
                    current_min_price = self.max_price * 0.5 # Default to 50% if onchange didn't run or was 0
                
                filters['price'] = {'$gte': current_min_price, '$lte': self.max_price}
            
            if self.bedrooms and self.bedrooms > 0:
                # Flexible bedroom search: exact, -1, +1
                # Pinecone doesn't directly support OR on same field in this way with $eq or $in for ranges easily.
                # Best to query for exact if critical, or omit if less so, or handle in post-processing if Pinecone returns more.
                # For now, let's try exact. If your Pinecone data uses numeric bedrooms:
                filters['bedrooms'] = {'$eq': self.bedrooms} 
                # Alternative for a range if your data supports it and Pinecone $in accepts numbers:
                # filters['bedrooms'] = {'$in': [self.bedrooms, self.bedrooms -1, self.bedrooms + 1]} 
                # However, $eq is safer if you expect exact matches primarily.

            if self.property_type: # Assuming Pinecone metadata field is 'type' or 'property_type'
                filters['type'] = {'$eq': self.property_type} 
            if self.city:
                filters['city'] = {'$eq': self.city.lower()} # Assuming city names are stored in lowercase
            if self.unit_type:
                 filters.setdefault('unit_type', {'$eq': self.unit_type}) # Add unit_type filter

            _logger.info(f"Attempting direct Odoo search with query: '{query_text}' and filters: {filters}")

            properties = search_service.search_properties(
                query_text=query_text,
                filters=filters,
                top_k=10 # Increased top_k to see if anything comes back
            )
            
            html = search_service.format_properties_as_html(properties)
            self.write({'recommended_properties': html})
            
            self.env.cr.commit() 
            
            # Simplified notification part for direct Python action
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Search Complete',
                    'message': f"Found {len(properties)} matching properties.",
                    'type': 'success' if properties else 'warning',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in action_generate_property_recommendations (direct search): {e}", exc_info=True)
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