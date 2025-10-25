# -*- coding: utf-8 -*-
{
    'name': 'Gulfco Cash transaction Limit',
    'version': '18.0.0.0.1',
    'sequence': 185,
    'category': 'Trsansaction Management',
    'website': 'https://www.plennix.com/',
    'summary': 'Add Cash transaction limit for any customer',
    'description': """
    
        Gulfco Cash transaction Limit based on outstaning payment and curent sales',
        ==============================
        - Prevents excessive unpaid transactions for cash customers.
        - Provides real-time alerts and reports for better financial control.
        - Allows flexibility for admin users to adjust limits when necessary.
            
    """,
    'author': 'Plennix',
    'depends': [
        'base',
        'account',
        'sale',
        'sale_management',
        'gulfco_contact_registration_custom',
        'gulfco_sale_extanded',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/automatic_credit_hold_cron.xml',
        'data/credit_hold_email_notification.xml',
        'security/res_group.xml',
        'views/credit_hold_reason.xml',
        'views/res_partner_view_inherit.xml',
        'views/sale_order_view.xml',
        'views/account_move_invoice_view.xml',
        'views/res_config_setting_view.xml',
        'views/tl_expiry_report_view.xml',
    ],

    'assets': {
        'web.assets_backend': [],
        'web.assets_frontend': [],
    },

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
