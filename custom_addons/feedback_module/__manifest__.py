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
        'views/lead_views.xml',
        'views/feedback_views.xml',
        'views/property_views.xml',
        'views/crm_lead_views.xml',
        'views/property_recommendation_views.xml',
        'views/users_views.xml',
        'security/ir.model.access.csv'
    ],
    
    "installable": True,
    "application": True,
}
