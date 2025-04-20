{
    'name': 'Custom CRM Add Call',
    'version': '1.0',
    'summary': 'Add Call Button to CRM Leads',
    'description': 'Custom module to add call logging in CRM.',
    'author': 'Your Name',
    'category': 'CRM',
    'depends': ['crm'],
    'data': [
    'security/ir.model.access.csv',
    'views/crm_call_log_views.xml',
    'views/crm_lead_view_inherit.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
