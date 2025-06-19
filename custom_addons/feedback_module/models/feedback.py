import logging
import time
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)

class RealEstateFeedback(models.Model):
    _name = 'real.estate.feedback'
    _description = 'Real Estate Feedback'

    feedback = fields.Text(string='Feedback', required=True)
    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    user_id = fields.Many2one('users.users', string='User', required=False)

    @api.model
    def load(self, fields, data):
        # --- Robust Import Logic ---

        # 1. Map relational fields by database ID
        id_map_fields = ['property_id', 'user_id']
        for field_name in id_map_fields:
            if field_name in fields:
                field_index = fields.index(field_name)
                fields[field_index] = f'{field_name}/.id'
                for row in data:
                    if len(row) > field_index and row[field_index]:
                        try:
                            # Handle potential floats in IDs and keep as string
                            row[field_index] = str(int(float(row[field_index])))
                        except (ValueError, TypeError):
                            pass

        # 2. Generate unique external IDs to prevent conflicts
        if 'id' not in fields:
            fields.append('id')
            for i, row in enumerate(data):
                ext_id = f"__import__.{self._name}_{int(time.time()*1000)}_{i}"
                row.append(ext_id)
        
        return super().load(fields, data)
