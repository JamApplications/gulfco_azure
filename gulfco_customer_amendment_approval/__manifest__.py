# -*- coding: utf-8 -*-
{
    'name': 'Gulfco Customer Amendment Approval',
    'version': '18.0.1.0.0',
    'category': 'Sales/Customer',
    'summary': 'Gulfco Customer Amendment Approval',
    'description': """Gulfco Customer Amendment Approval""",
    'author': 'Plennix',
     'website': 'https://www.plennix.com/',
    'depends': ['gulfco_contact_registration_custom','sales_team','account','plnx_sales_team','gulfco_cash_transaction_limit'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/customer_amendment_view.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
