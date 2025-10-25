# -*- coding: utf-8 -*-
{
    "name": "Voucher Sequence",
    'version': '1.0',
    'author': 'Elhamari',
    'category': 'Accounting',
    'depends': ['account', 'plennix_account_payment_extended'],
    'summary': 'This module generate digit sequence for AR\AP transaction',
    'description': """
This module generate digit sequence for AR\AP transaction
    """,
    "data" : [
        #'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'data/sequence.xml'
    ],
    'application': True,
    'installable': True,
    "license": "LGPL-3",
}
