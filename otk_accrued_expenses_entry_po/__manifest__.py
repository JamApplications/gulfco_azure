# -*- coding: utf-8 -*-
{
    'name': "OTK Accrued Expenses Entry from PO",
    'summary': "OTK Accrued Expenses Entry from PO",
    'description': """
    OTK Accrued Expenses Entry from PO

    """,
    'author': "Plennix",
    'website': "https://www.plennix.com",
    'category': 'Accounting/Configuration',
    'license': 'LGPL-3',

    # Dependencies
    'depends': ['base', 'purchase','account', 'purchase_line_views', 'purchase_stock', 'stock_outbouding_operation'],

    # Data files
    'data': [
        'security/ir.model.access.csv',
        'views/stock_reports.xml',
        'views/res_partner.xml',
        'views/stock_picking.xml',
        'views/purchase_order.xml',
        'views/product_views.xml',
    ],

    # Install settings
    'installable': True,
    'application': False,
    'auto_install': False,
}
