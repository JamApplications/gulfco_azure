# -*- coding: utf-8 -*-
{
    'name': 'Gulfco Product Template Detailed Data',
    'version': '1.0',
    'sequence': 185,
    'category': 'Products',
    'website': 'https://www.plennix.com/',
    'summary': 'Enhance Product Template records with detailed information fields.',
    'description': """
        Gulfco Product Detailed Data
        ==============================
            This module extends the Product Template model to include additional fields 
            for managing detailed customer information, enabling better data organization 
            and reporting capabilities.
    """,
    'author': 'Plennix',
    'depends': [
        'base',
        'product',
        'stock',
        'purchase',
        'stock_delivery'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_aging_report_wizard_views.xml',
        'report/product_aging_pdf_report.xml',
        'views/product_template.xml',
        'views/brand_views.xml',
        'views/stock_route_views.xml',
        'views/product_package_view.xml',
        'views/stock_warehouse_views.xml',
        'views/stock_location_views.xml',
        'views/product_views.xml',
        'views/stock_package_type_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gulfco_product_customized_data/static/src/js/no_negative_value.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
