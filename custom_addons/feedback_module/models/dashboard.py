# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FeedbackDashboard(models.Model):
    _name = 'feedback.dashboard'
    _description = 'Feedback Call and Questionnaire Dashboard'
    _auto = False  # Not creating a table

    name = fields.Char(default="Dashboard")
    recent_calls = fields.One2many('feedback.call.log', string="Recent Calls", compute="_compute_recent_calls")
    recent_questionnaires = fields.One2many('feedback.lead.questionnaire', string="Recent Questionnaires", compute="_compute_recent_questionnaires")
    call_count = fields.Integer(string="Call Count", compute="_compute_counts")
    questionnaire_count = fields.Integer(string="Questionnaire Count", compute="_compute_counts")
    success_rate = fields.Float(string="Success Rate (%)", compute="_compute_counts")

    @api.depends('name')
    def _compute_recent_calls(self):
        """Get the 10 most recent calls."""
        for rec in self:
            rec.recent_calls = self.env['feedback.call.log'].search(
                [], order='call_time desc', limit=10
            )

    @api.depends('name')
    def _compute_recent_questionnaires(self):
        """Get the 10 most recent questionnaires."""
        for rec in self:
            rec.recent_questionnaires = self.env['feedback.lead.questionnaire'].search(
                [], order='create_date desc', limit=10
            )

    @api.depends('name')
    def _compute_counts(self):
        """Compute statistics for the dashboard."""
        for rec in self:
            # Count calls
            all_calls = self.env['feedback.call.log'].search([])
            rec.call_count = len(all_calls)
            
            # Count successful transcriptions
            success_calls = self.env['feedback.call.log'].search([
                ('inference_status', '=', 'success')
            ])
            
            # Calculate success rate
            rec.success_rate = (len(success_calls) / rec.call_count * 100) if rec.call_count else 0
            
            # Count questionnaires
            rec.questionnaire_count = self.env['feedback.lead.questionnaire'].search_count([])
    
    @api.model
    def action_view_all_calls(self):
        """Open the call report view."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Call Reports',
            'res_model': 'feedback.call.log',
            'view_mode': 'list,form',
            'target': 'current',
        }
    
    @api.model
    def action_view_all_questionnaires(self):
        """Open the questionnaire view."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Client Questionnaires',
            'res_model': 'feedback.lead.questionnaire',
            'view_mode': 'list,form',
            'target': 'current',
        } 