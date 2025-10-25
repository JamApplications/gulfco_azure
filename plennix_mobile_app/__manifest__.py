# -*- coding: utf-8 -*-
{
    'name': 'Plennix Mobile App',
    'version': '18.0.0.0',
    'summary': 'Plennix Mobile App',
    'description': 'Plennix Mobile App',
    'category': 'Hidden/Tools',
    'author': 'Plennix Technologies',
    'license': 'LGPL-3',
    'website': 'https://www.plennix.com/',
    'depends': [
        'base',
        'web',
        'sale_management',
        'website_sale',
        'stock',
        'gulfco_sale_extanded',
        'plnx_rma_extended',
        'gulfco_account_payment_extended',
        'stock_outbouding_operation',
        'plnx_sales_team',
        'stock_request'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner.xml',
        'views/sale_order_view.xml',
        'views/van_daily_collection_wizard_view.xml',
        'reports/report_van_daily_collection_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
