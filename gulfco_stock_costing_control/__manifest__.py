# -*- coding: utf-8 -*-
{
    'name': 'Stock Costing Control',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Restrict use of GRN stock without validated Landed Cost when costing is enabled.',
    'author': 'khalid.khangi',
    'depends': ['stock', 'purchase', 'account', 'stock_landed_costs', "purchase_line_views", "stock_account", 'asn_request'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_cost_control_view.xml',
        'views/stock_picking_cost_control_view.xml',
        'views/stock_quant_cost_control_view.xml',
        'views/stock_valuation_layer_views.xml',
        'views/stock_landed_cost.xml',
        'wizard/total_cost_breakdown_wizard.xml',
        'wizard/quant_data_fix_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
