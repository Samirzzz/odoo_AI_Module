odoo.define('feedback_module.property_search', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var session = require('web.session');

    var PropertySearch = Widget.extend({
        events: {
            'click button[name="action_generate_property_recommendations"]': '_onSearchProperties',
        },

        _onSearchProperties: function (ev) {
            ev.preventDefault();
            var self = this;
            
            // Get the current form view
            var form = this.$el.closest('form');
            var questionnaireId = form.data('id');
            
            // Make the RPC call
            this._rpc({
                route: '/web/dataset/call_button',
                params: {
                    model: 'feedback.lead.questionnaire',
                    method: 'action_generate_property_recommendations',
                    args: [[questionnaireId]],
                    kwargs: {},
                },
            }).then(function (result) {
                if (result && result.tag === 'property_search_request') {
                    // Make the actual API request
                    return $.ajax({
                        url: result.params.url,
                        type: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify(result.params.data),
                        success: function(response) {
                            // Update the form with results
                            self._updateFormWithResults(response, questionnaireId);
                        },
                        error: function(error) {
                            self._showError(error);
                        }
                    });
                }
            });
        },

        _updateFormWithResults: function(results, questionnaireId) {
            var self = this;
            
            // Format results as HTML
            var html = this._formatResultsAsHtml(results);
            
            // Update the form with the results
            this._rpc({
                route: '/web/dataset/call_button',
                params: {
                    model: 'feedback.lead.questionnaire',
                    method: 'write',
                    args: [[questionnaireId], {'recommended_properties': html}],
                    kwargs: {},
                },
            }).then(function() {
                // Reload the form
                self.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'feedback.lead.questionnaire',
                    res_id: questionnaireId,
                    view_mode: 'form',
                    target: 'new',
                    flags: {'mode': 'readonly'},
                    context: {'show_property_recommendations': True},
                    views: [[false, 'form']]
                });
            });
        },

        _formatResultsAsHtml: function(results) {
            if (!results || !results.matches || results.matches.length === 0) {
                return "<p class='text-muted'>No matching properties found.</p>";
            }
            
            var html = `
                <div class='property-recommendations mb-4' style='margin-top: 20px; padding: 10px; background-color: #f8f9fa;'>
                    <h4 style='color: #4a4a4a; margin-bottom: 15px; border-bottom: 1px solid #dee2e6; padding-bottom: 10px;'>
                        Found Properties (${results.matches.length})
                    </h4>
            `;
            
            results.matches.forEach(function(prop) {
                // Format price with commas
                var price = prop.price || 0;
                var priceFormatted = price.toLocaleString('en-US', {maximumFractionDigits: 0});
                
                // Calculate match percentage
                var score = prop.similarity_score || 0;
                var matchPct = Math.min(score * 100, 100);  // Cap at 100%
                
                // Set badge color based on match percentage
                var badgeColor = matchPct > 80 ? '#28a745' : matchPct > 60 ? '#ffc107' : '#dc3545';
                
                html += `
                    <div class='property-card mb-3 p-3 border rounded' style='background-color: white; box-shadow: 0 3px 10px rgba(0,0,0,0.1); margin-bottom: 20px !important;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <h5 class='property-title mb-0' style='font-weight: bold; color: #2c3e50; font-size: 1.2rem;'>${prop.type || 'Property'}</h5>
                            <span style='background-color: ${badgeColor}; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold;'>${matchPct.toFixed(1)}% Match</span>
                        </div>
                        <hr style='margin: 10px 0; border-top: 1px solid #eee;'/>
                        <div style='display: flex; flex-wrap: wrap;'>
                            <div style='flex: 1; min-width: 50%;'>
                                <p style='margin-bottom: 8px;'><strong style='color: #555;'>ID:</strong> <span style='color: #333;'>${prop.id || 'N/A'}</span></p>
                                <p style='margin-bottom: 8px;'><strong style='color: #555;'>Price:</strong> <span style='color: #333; font-weight: bold;'>${priceFormatted} EGP</span></p>
                                <p style='margin-bottom: 8px;'><strong style='color: #555;'>Area:</strong> <span style='color: #333;'>${prop.area || 'N/A'} sq.m</span></p>
                            </div>
                            <div style='flex: 1; min-width: 50%;'>
                                <p style='margin-bottom: 8px;'><strong style='color: #555;'>Bedrooms:</strong> <span style='color: #333;'>${prop.bedrooms || 'N/A'}</span></p>
                                <p style='margin-bottom: 8px;'><strong style='color: #555;'>Bathrooms:</strong> <span style='color: #333;'>${prop.bathrooms || 'N/A'}</span></p>
                                <p style='margin-bottom: 8px;'><strong style='color: #555;'>City:</strong> <span style='color: #333;'>${prop.city || 'N/A'}</span></p>
                            </div>
                        </div>
                        ${prop.amenities ? `
                            <div style='margin-top: 10px;'>
                                <p style='margin-bottom: 8px;'><strong style='color: #555;'>Amenities:</strong></p>
                                <div style='display: flex; flex-wrap: wrap; gap: 5px;'>
                                    ${prop.amenities.map(function(amenity) {
                                        return `<span style='background-color: #e9ecef; padding: 3px 8px; border-radius: 12px; font-size: 0.9em;'>${amenity}</span>`;
                                    }).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;
            });
            
            html += "</div>";
            return html;
        },

        _showError: function(error) {
            this.do_warn('Error', 'Failed to search properties: ' + (error.responseText || error.message || 'Unknown error'));
        },
    });

    core.action_registry.add('property_search', PropertySearch);
    return PropertySearch;
}); 