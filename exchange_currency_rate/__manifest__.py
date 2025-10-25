
{
    'name': "Manual Currency Exchange Rate",
    'version': '18.0.1.1.0',
    'category': 'Accounting',
    "website": "https://www.plennix.com/",
    "author": "Plennix",
    'depends': ['base', 'purchase', 'sale_management', 'account'],
    'data': [
        'views/account_move_views.xml',
        'views/account_payment_view.xml',
        # 'views/purchase_order_views.xml',
        # 'views/sale_order_views.xml'
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
