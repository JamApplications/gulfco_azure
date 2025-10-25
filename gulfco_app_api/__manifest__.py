# gulfco_app_api/__manifest__.py
{
    'name': 'Gulfco App API',
    'version': '1.0',
    'summary': 'API endpoints for Gulfco mobile app',
    'description': 'This module provides API endpoints for the Gulfco React Native mobile application.',
    'author': 'Juma Al-Majid IT department',
    'website': 'https://al-majid.com',
    'category': 'Tools',
    'depends': ['base', 'web', 'mail', 'stock','sale_management', 'website_sale','stock_outbouding_operation'],  # add more dependencies if needed
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/mobile_app_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}