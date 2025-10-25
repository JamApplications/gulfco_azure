# -*- coding: utf-8 -*-
{
    'name': 'Customer Registration ImportData',
    'version': '1.0',
    'summary': 'Module to import and register customer data from XLSX files.',
    'description': 'This module allows users to import customer data from XLSX templates and create customer records in Odoo.',
    'author': "Plennix",
    'website': "https://www.plennix.com/",
    'category': 'Contact',
    'depends': ['base', 'gulfco_contact_registration_custom'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/customer_importdata.xml',
        'views/customer_importdata_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
}
