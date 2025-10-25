# -*- coding: utf-8 -*-
{
    'name': 'Gulfco Customer Detailed Data',
    'version': '1.0',
    'sequence': 185,
    'category': 'Customer Relationship Management',
    'website': 'https://www.plennix.com/',
    'summary': 'Enhance customer records with detailed information fields.',
    'description': """
        Gulfco Customer Detailed Data
        ==============================
            This module extends the customer (partner) model to include additional fields 
            for managing detailed customer information, enabling better data organization 
            and reporting capabilities.
    """,
    'author': 'Plennix',
    'depends': [
        'base',
        'contacts',
        'account',
        "account_asset"
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/customer_code_sequnce.xml',
        'views/divisions.xml',
        'views/customer_group_view.xml',
        'views/res_partner.xml',
        'views/account_move_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
