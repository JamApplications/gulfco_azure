# -*- coding: utf-8 -*-
{
    'name': 'Gulfco Contact Registration Custom Details',
    'version': '18.0.0.0.2',
    'sequence': 185,
    'category': 'Customer Relationship Management',
    'website': 'https://www.plennix.com/',
    'summary': 'Enhance customer Registration from website portal to register customer and supplier(vendore) with detailed information fields.',
    'description': """
    
        Gulfco Conntact Registration Detailed for Customer & Venndor
        ==============================
            - This module have the new menuns inside conatct for regisration of the customer & supplier comming from the portal  the customer (partner) model to include additional fields        
            - New manu inside Contact App
                - Contact/Registration
                - Contact/Registration/Customer Registration
                - Contact/Registration/Vendore Registration
             - Create registration process from the portal and store into to the relevent manus as an archived contacts
             - created protal registration forms
            
    """,
    'author': 'Plennix',
    'depends': [
        'base',
        'contacts',
        'account',
        'gulfco_customer_customized_data',
        'gulfco_vendor_customized_data',
        'stock_inventory_adjustment',
        'website',
        'web',
        'web_editor',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security_group.xml',
        'data/vendor_code_sequnce.xml',

        'views/res_partner.xml',
        'views/contact_registration_menu.xml',
        'views/vendor_registration_template.xml',
        'views/customer_registration_template.xml',

        'data/website_registration_menu.xml',
    ],


    'assets': {
        'web.assets_frontend': [
            'gulfco_contact_registration_custom/static/src/js/registration_form.js',
            'gulfco_contact_registration_custom/static/src/scss/form_vendore.scss',
        ],

        'web.assets_backend': [
            'gulfco_contact_registration_custom/static/src/js/contact_form_controller.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
