{
    'name': 'Sale Order Automation',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Automate sale order confirmation, invoice creation and payment posting',
    'description': '''
        This module adds a server action to automate the complete sale order workflow:
        - Confirm Sale Order
        - Create Invoice automatically
        - Post Invoice
        - Create Payment automatically
        - Post Payment
    ''',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale', 'account', 'sale_management'],
    'data': [
        'data/ir_actions_server.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}