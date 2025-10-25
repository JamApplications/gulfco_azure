{
    "name": "Purchase Budget",
    "version": "18.0.0.0.1",
    "category": "Accounting/Purchase",
    "website": "https://www.plennix.com/",
    "author": "Plennix",
    "depends": ["account", 'purchase', "gulfco_vendor_customized_data","gulfco_customer_customized_data", "gulfco_product_customized_data"],
    "data": [
        "security/ir.model.access.csv",
        # "views/purchase_budget_line_view.xml",
        "views/purchase_budget_line_set_view.xml",
        "views/purchase_budget_view.xml",
    ],
    "installable": True,
    'assets': {
        'web.assets_backend': [
            # 'gulfco_purchase_budget/static/src/views/*',
            # 'gulfco_purchase_budget/static/src/css/custom.css',
        ],
    },

}
