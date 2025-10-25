{
    'name': 'Invoice Regeneration',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Regenerate invoices by adding missing products from sale orders',
    'description': """
        This module provides a server action to regenerate invoices by comparing
        them with their related sale orders and adding any missing product lines.

        Features:
        - Compare sale orders with their invoices
        - Identify missing product lines
        - Add missing lines with correct details
        - Automatic posting of updated invoices
        - Batch processing support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/server_actions.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}