# -*- coding: utf-8 -*-
{
    'name': 'Gulfco Vendor Detailed Data',
    'version': '1.0',
    'sequence': 185,
    'category': 'Accounting',
    'website': 'https://www.plennix.com/',
    'summary': 'Enhance customer records with detailed information fields.',
    'description': """
        Gulfco Customer Detailed Data
        ==============================
            This module extends the vendor (partner) model to include additional fields 
            for managing detailed vendor information, enabling better data organization 
            and reporting capabilities.
    """,
    'author': 'Plennix',
    'depends': ['gulfco_customer_customized_data'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_bank_views.xml',
        'views/res_partner.xml',
        'views/supplier_classification_view.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
