# -*- coding: utf-8 -*-
{
    'name': "Gulfco Product Registration Import Date",

    'author': "Plennix",
    'website': "https://www.plennix.com/",
    'version': '1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product_registration','stock'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_importdata.xml',
        'views/product_importdata_menu.xml'
    ],
}

