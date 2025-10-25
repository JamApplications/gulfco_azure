{
    'name': 'Product Registration',
    'version': '18.0.0.0.0',
    'category': 'Products',
    'website': 'https://www.plennix.com/',
    'author': 'Plennix',
    'depends': ['product', 'stock', 'account_intrastat', 'product_expiry', 'stock_delivery','base','gulfco_product_customized_data', 'web','mrp'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/product_template.xml',
        'views/product_registration_server_action.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'product_registration/static/src/**/*',
        ],
    },

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
