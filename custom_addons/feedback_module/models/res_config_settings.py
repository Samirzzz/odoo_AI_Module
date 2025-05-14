# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Pinecone settings
    pinecone_api_key = fields.Char(
        string='Pinecone API Key',
        config_parameter='feedback_module.pinecone_api_key',
    )
    
    pinecone_index = fields.Char(
        string='Pinecone Index Name',
        config_parameter='feedback_module.pinecone_index',
        default='recommendation-index',
    )
    
    embedding_model = fields.Char(
        string='Embedding Model',
        config_parameter='feedback_module.embedding_model',
        default='distilbert-base-uncased',
    ) 