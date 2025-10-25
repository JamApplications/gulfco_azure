{
    'name': 'Loyalty Extension',
    'version': '1.0',
    'author': 'Khalid Khangi',
    'summary': 'Enhances the loyalty program with customer-specific rules and reward eligibility filtering.',
    'depends': ['loyalty', 'sale', 'sale_loyalty','gulfco_sale_purchase_discount','gulfco_advanced_loyalty_program', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'report/ir_actions_report_templates.xml',
        'views/loyalty_program_views.xml',
        'views/res_config_settings_view.xml',
        'wizard/loyalty_rule_customer_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loyalty_extension/static/src/xml/*',
        ],
    },
    'installable': True,
    'application': False,
}
