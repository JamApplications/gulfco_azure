
{
    "name": "Gulfco Sale Purchase Account Discount",
    "version": "18.0.0.0.1",
    'author': "Plennix",
    'website': "https://www.plennix.com/",
    "category": "Accounting",
    "description": "Gulfco Sale Purchase Account Discount",
    "depends": ["sale", "purchase","account","gulfco_sale_extanded", "gulfco_advanced_loyalty_program"],
    # need to add depend of gulfco_sale_extanded becuase of overrided method in that module sale
    "data": [
        'report/ir_actions_report_templates.xml',
        'views/account_move.xml',
        'views/sale_order.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gulfco_sale_purchase_discount/static/src/xml/*',
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False
}
