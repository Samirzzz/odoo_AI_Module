{
    'name': 'Call Module',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Module for managing calls',
    'sequence': 1,
    'description': 'This module provides functionalities to manage calls.',
    'author': 'Your Name',
    'depends': ['base', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/call_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
} 