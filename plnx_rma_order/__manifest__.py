# -*- coding: utf-8 -*-
{
    'name': "Plennix RMA Order",
    'author': "Plennix",
    'website': "https://www.plennix.com",
    'category': 'RMA',
    'version': '18.0',
    'depends': ['base', 'rma', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/rma_order.xml',
        'views/menus_actions.xml',
    ],
}
