# -*- coding: utf-8 -*-
{
    'name': "Plennix MRP Extended",
    'author': "Plennix",
    'website': "https://www.plennix.com",
    'category': 'Manufacturing',
    'version': '18.0',
    'summary': 'Enhance Fields Service apps.',
    'description': """
            Gulfco MRP Extended with stock lot values Enhancement
            ==============================
            - Added custom lot sequnce number based on schedule date
            - modify expiery date of the stock lot based on set division from product id
        """,
    'depends': ['base', 'mrp', 'mrp_product_expiry', 'stock', 'gulfco_product_customized_data'],
    'data': [
        'view/mrp_bom_views.xml',
    ],
}
