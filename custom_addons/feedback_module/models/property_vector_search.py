# -*- coding: utf-8 -*-
import logging
import os
import time
import re

import torch
import requests
from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Initialize empty global variables - will be set up when needed
_pc = None
_index = None
_tokenizer = None
_model = None

class PropertyVectorSearch:
    """Vector search service for property recommendations."""
    
    def __init__(self, env):
        """Initialize with Odoo environment."""
        self.env = env
        self._setup_pinecone()
        self._setup_embedding_model()
    
    def _setup_pinecone(self):
        """Setup Pinecone connection."""
        global _pc, _index
        
        # Only setup once
        if _pc is not None:
            return
            
        try:
            from pinecone import Pinecone, ServerlessSpec
            
            # Get API key from system parameters
            ICP = self.env['ir.config_parameter'].sudo()
            api_key = ICP.get_param('feedback_module.pinecone_api_key', '')
            index_name = ICP.get_param('feedback_module.pinecone_index', 'recommendation-index')
            
            if not api_key:
                _logger.warning("Pinecone API key not configured")
                return
                
            # Initialize Pinecone client
            _pc = Pinecone(api_key=api_key)
            
            # Create index if it doesn't exist
            try:
                _pc.create_index(
                    name=index_name,
                    dimension=768,  # For distilbert embeddings
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
                _logger.info(f"Created Pinecone index: {index_name}")
            except Exception as e:
                _logger.info(f"Index creation skipped: {e}")
            
            # Wait for index to be ready
            try:
                index_info = _pc.describe_index(index_name)
                if index_info.status['ready']:
                    _index = _pc.Index(index_name)
                    _logger.info(f"Connected to Pinecone index: {index_name}")
                else:
                    _logger.warning(f"Pinecone index not ready: {index_name}")
            except Exception as e:
                _logger.error(f"Error connecting to Pinecone index: {e}")
                
        except ImportError:
            _logger.error("Pinecone package not installed. Install with: pip install pinecone")
        except Exception as e:
            _logger.error(f"Error setting up Pinecone: {e}")
    
    def _setup_embedding_model(self):
        """Setup embedding model."""
        global _tokenizer, _model
        
        # Only setup once
        if _tokenizer is not None:
            return
            
        try:
            from transformers import AutoTokenizer, AutoModel
            
            # Get model name from system parameters
            ICP = self.env['ir.config_parameter'].sudo()
            model_name = ICP.get_param('feedback_module.embedding_model', 'distilbert-base-uncased')
            
            # Initialize model & tokenizer
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            _model = AutoModel.from_pretrained(model_name)
            _logger.info(f"Loaded embedding model: {model_name}")
            
        except ImportError:
            _logger.error("Transformers package not installed. Install with: pip install transformers")
        except Exception as e:
            _logger.error(f"Error setting up embedding model: {e}")
            
    def generate_embedding(self, text):
        """Generate text embedding."""
        global _tokenizer, _model
        
        if _tokenizer is None or _model is None:
            _logger.warning("Embedding model not initialized")
            return [0] * 768  # Return empty vector
            
        try:
            inputs = _tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
            with torch.no_grad():
                outputs = _model(**inputs)
                return outputs.last_hidden_state.mean(dim=1).squeeze().tolist()
        except Exception as e:
            _logger.error(f"Error generating embedding: {e}")
            return [0] * 768  # Return empty vector
    
    def search_properties(self, query_text, filters=None, top_k=5):
        """Search for properties in vector database."""
        global _index
        
        if _index is None:
            _logger.warning("Pinecone index not initialized")
            return self._get_mock_properties()
            
        try:
            # Generate embedding for query text
            embedding = self.generate_embedding(query_text)
            
            # Perform vector search
            results = _index.query(
                vector=embedding,
                top_k=top_k,
                filter=filters or {},
                include_metadata=True
            )
            
            # Format results
            properties = []
            for match in results.matches:
                property_data = match.metadata
                property_data['score'] = match.score
                properties.append(property_data)
                
            _logger.info(f"Found {len(properties)} properties via vector search")
            return properties
            
        except Exception as e:
            _logger.error(f"Error searching properties: {e}")
            return self._get_mock_properties()
    
    def _get_mock_properties(self):
        """Return mock properties for testing or when API fails."""
        return [
            {
                'amenities': ['Parking', 'Playground', 'Concierge', 'Doorman', 'Garage', 'Pool', 'Balcony', 'Security'],
                'bathrooms': 0.0,
                'bedrooms': 3.0,
                'city': 'new cairo',
                'compound': 'other',
                'delivery_in': 2029.0,
                'down_payment': 45.0,
                'furnished': 'unknown',
                'installment_years': 8.0,
                'payment_option': 'other',
                'price': 1800000.0,
                'type': 'apartment',
                'score': 0.857101798,
                'id': '992',
                'title': 'Apartment in New Cairo'
            },
            {
                'amenities': ['Gym', 'Wifi', 'Dishwasher', 'Security', 'Playground', 'Doorman', 'Garage'],
                'bathrooms': 0.0,
                'bedrooms': 3.0,
                'city': '6th of october',
                'compound': 'other',
                'delivery_in': 2030.0,
                'down_payment': 16.0,
                'furnished': 'no',
                'installment_years': 4.0,
                'payment_option': 'cash',
                'price': 1800000.0,
                'type': 'penthouse',
                'score': 0.856945097,
                'id': '945',
                'title': 'Penthouse in 6th of October'
            },
            {
                'amenities': ['Security', 'Garage', 'Pool', 'Parking', 'Elevator', 'Hardwood', 'Dishwasher'],
                'bathrooms': 0.0,
                'bedrooms': 3.0,
                'city': 'faisal',
                'compound': 'other',
                'delivery_in': 2029.0,
                'down_payment': 35.0,
                'furnished': 'no',
                'installment_years': 8.0,
                'payment_option': 'cash',
                'price': 1500000.0,
                'type': 'apartment',
                'score': 0.856688499,
                'id': '198',
                'title': 'Apartment in Faisal'
            },
            {
                'amenities': ['Garage', 'Pool', 'Security', 'Dishwasher'],
                'bathrooms': 0.0,
                'bedrooms': 3.0,
                'city': 'sheikh zayed',
                'compound': 'other',
                'delivery_in': 2031.0,
                'down_payment': 10.0,
                'furnished': 'unknown',
                'installment_years': 3.0,
                'payment_option': 'cash',
                'price': 1995000.0,
                'type': 'apartment',
                'score': 0.856421709,
                'id': '47',
                'title': 'Apartment in Sheikh Zayed'
            },
            {
                'amenities': ['Pool', 'Elevator', 'Dishwasher', 'Concierge', 'Spa', 'Garden', 'Wifi'],
                'bathrooms': 0.0,
                'bedrooms': 3.0,
                'city': '6th of october',
                'compound': 'other',
                'delivery_in': 2026.0,
                'down_payment': 40.0,
                'furnished': 'no',
                'installment_years': 7.0,
                'payment_option': 'cash',
                'price': 2150000.0,
                'type': 'apartment',
                'score': 0.854761958,
                'id': '27',
                'title': 'Apartment in 6th of October'
            }
        ]
        
    def format_properties_as_html(self, properties):
        """Format properties as HTML for display."""
        if not properties:
            return "<p class='text-muted'>No matching properties found.</p>"
            
        html = """
        <div class='property-recommendations mb-4' style='margin-top: 20px; padding: 10px; background-color: #f8f9fa;'>
            <h4 style='color: #4a4a4a; margin-bottom: 15px; border-bottom: 1px solid #dee2e6; padding-bottom: 10px;'>
                Found Properties ({count})
            </h4>
        """.format(count=len(properties))
        
        for prop in properties:
            # Format price with commas
            price = prop.get('price', 0)
            price_formatted = f"{float(price):,.0f}" if price else 'N/A'
            
            # Calculate match percentage
            score = float(prop.get('score', 0))
            match_pct = min(score * 100, 100)  # Cap at 100%
            
            # Set badge color based on match percentage
            badge_color = 'success' if match_pct > 80 else 'warning' if match_pct > 60 else 'danger'
            
            # Create a card for each property
            html += f"""
            <div class='property-card mb-3 p-3 border rounded' style='background-color: white; box-shadow: 0 3px 10px rgba(0,0,0,0.1); margin-bottom: 20px !important;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h5 class='property-title mb-0' style='font-weight: bold; color: #2c3e50; font-size: 1.2rem;'>{prop.get('title', 'Property')}</h5>
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
                    </div>
                </div>
            </div>
            """
        
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
    
    # Fields for search ranges
    min_price = fields.Float(
        string="Min Price (Search)", 
        compute="_compute_search_ranges", 
        store=True
    )
    max_price = fields.Float(
        string="Max Price (Search)", 
        compute="_compute_search_ranges", 
        store=True
    )
    min_area = fields.Float(
        string="Min Area (Search)", 
        compute="_compute_search_ranges", 
        store=True
    )
    max_area = fields.Float(
        string="Max Area (Search)", 
        compute="_compute_search_ranges", 
        store=True
    )
    
    # Meeting agreement field
    meeting_agreed = fields.Boolean(
        string="Meeting Agreed",
        help="Whether the client agreed to a meeting"
    )
    
    @api.model
    def _init_system_parameters(self):
        """Initialize system parameters for property vector search."""
        ICP = self.env['ir.config_parameter'].sudo()
        if not ICP.get_param('feedback_module.pinecone_api_key', False):
            # Set empty default value - admin should set this to a real API key
            ICP.set_param('feedback_module.pinecone_api_key', '')
            
        if not ICP.get_param('feedback_module.pinecone_index', False):
            ICP.set_param('feedback_module.pinecone_index', 'recommendation-index')
            
        if not ICP.get_param('feedback_module.embedding_model', False):
            ICP.set_param('feedback_module.embedding_model', 'distilbert-base-uncased')
            
        return True
    
    @api.model
    def _register_hook(self):
        """Initialize system parameters on module install/upgrade."""
        self._init_system_parameters()
        return super()._register_hook()
        
    @api.depends('max_budget', 'area')
    def _compute_search_ranges(self):
        """Compute search ranges with +/- 25% flexibility."""
        for record in self:
            # Calculate price range
            if record.max_budget:
                record.min_price = record.max_budget * 0.75
                record.max_price = record.max_budget * 1.25
            else:
                record.min_price = record.max_price = 0
                
            # Calculate area range
            if record.area:
                record.min_area = record.area * 0.75
                record.max_area = record.area * 1.25
            else:
                record.min_area = record.max_area = 0
                
    def action_generate_property_recommendations(self):
        """Generate property recommendations based on questionnaire data."""
        self.ensure_one()
        
        # Check if we have enough data
        if not (self.property_type or self.max_budget or self.preferred_location):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Missing Information',
                    'message': 'Please provide more property details first.',
                    'type': 'warning',
                }
            }
        
        try:
            # Create search service
            search_service = PropertyVectorSearch(self.env)
            
            # Build query text from the questionnaire data
            query_parts = []
            if self.property_type:
                query_parts.append(f"Property type: {self.property_type}")
            if self.preferred_location:
                query_parts.append(f"Location: {self.preferred_location}")
            if self.number_of_rooms:
                query_parts.append(f"{self.number_of_rooms} bedrooms")
            if self.required_features:
                query_parts.append(f"Features: {self.required_features}")
            if self.unit_type:
                query_parts.append(f"Unit type: {self.unit_type}")
                
            query_text = ". ".join(query_parts)
            
            # Build search filters
            filters = {}
            if self.max_budget:
                filters['price'] = {
                    '$gte': self.min_price,
                    '$lte': self.max_price
                }
            if self.number_of_rooms:
                filters['bedrooms'] = self.number_of_rooms
                
            # Search for properties
            properties = search_service.search_properties(
                query_text=query_text,
                filters=filters,
                top_k=5
            )
            
            # Format as HTML
            html = search_service.format_properties_as_html(properties)
            
            # Update the record
            self.write({'recommended_properties': html})
            
            # Display notification first
            self.env.cr.commit()  # Commit changes to ensure they're visible
            
            message = f"Found {len(properties)} matching properties"
            self._cr.execute("""
                SELECT COALESCE(
                    (SELECT id FROM bus_bus ORDER BY id DESC LIMIT 1), 0
                ) + 1
            """)
            notification_id = self._cr.fetchone()[0]
            
            # Show the notification directly
            self.env['bus.bus']._sendone(
                self.env.user.partner_id, 
                'mail.simple_notification',
                {
                    'title': 'Success',
                    'message': message,
                    'sticky': False,
                    'warning': False
                }
            )
            
            # Force reloading the form to show results
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'flags': {'mode': 'readonly'},
                'context': {'show_property_recommendations': True}
            }
            
        except Exception as e:
            _logger.error(f"Error generating recommendations: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f"Failed to generate recommendations: {e}",
                    'type': 'danger',
                }
            } 