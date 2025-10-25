# -*- coding: utf-8 -*-
{
    'name': 'Gulfco Advanced Loyalty Program',
    'version': '18.0.0.0.1',
    'sequence': -10,
    'category': 'Promotion Program',
    'website': 'https://www.al-majid.com',
    'summary': 'Gulfco Advanced Promotion Program',
    'description': """
        Gulfco Advanced Promotion Program
        ==============================
    """,
    'author': 'Al-majid',
    'depends': [
        'sale',
        'sale_loyalty',
        'gulfco_sale_extanded',
        'account',
        'point_of_sale',
        'hr_expense',
        'gulfco_cash_transaction_limit',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/promo_views.xml',
        'views/sale_order.xml',
        'views/account_move.xml',
        'views/worker_journal_views.xml',
        'data/data.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}