# -*- coding: utf-8 -*-
{
    "name": "Multi Invoice Payment",
    'version': '1.0',
    'author': 'Elhamari',
    'category': 'Accounting',
    'depends': ['account','gulfco_account_payment_extended', 'web', 'gulfco_cheque_book'],
    'summary': 'This module is allow you to reconcile payment partial/full with multiple invoice/bills on payment',
    'description': """
This module is allow you to partial/full reconcile multiple invoice/bills on payment
    """,
    "data" : [
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'views/account_payment_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gulfco_multi_invoice_payment/static/src/views/fields/selection_field_inherited.js',
        ],
    },
    'application': True,
    'installable': True,
    "license": "LGPL-3",
}
