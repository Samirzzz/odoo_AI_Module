{
    "name": "Real Estate CRM",
    "version": "1.0",
    'license': 'LGPL-3',

    "summary": "Manage Leads, Feedback, and Properties from Mobile App",
    "author": "Samirzzz",
    "category": "Sales",
    "website": "http://example.com",
    "depends": ["base", "crm", "web"],
    'assets': {
        'web.assets_backend': [
            'feedback_module/static/src/js/auto_fetch_users.js',
            'feedback_module/static/src/xml/button_templates.xml',
            'feedback_module/static/src/xml/form_templates.xml',
            
        ],
    },

    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/import_excel_views.xml',
        'views/menu_views.xml',
        'views/feedback_views.xml',
        'views/call_log_views.xml',
        'views/lead_questionnaire_views.xml',
        'views/call_report_views.xml',
        'views/dashboard_view.xml',
        'views/res_config_settings_view.xml',
        'views/segmentation_views.xml',
        'views/property_views.xml',
        'views/real_estate_recommendedproperty_views.xml',
        'views/recommended_property_details_views.xml',
    ],
    
    "installable": True,
    "application": True,
}
