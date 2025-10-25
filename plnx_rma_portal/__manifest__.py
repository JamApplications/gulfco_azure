# -*- coding: utf-8 -*-
{
    'name': "Plennix RMA Portal",
    'author': "Plennix",
    'website': "https://www.plennix.com",
    'category': 'RMA',
    'version': '17.1',
    'depends': ['base','rma'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/portal_rma_tree.xml',
        'views/portal_rma_form.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'plnx_rma_portal/static/src/js/*',
        ],
    },
}

