{
    "name": "Sales Budget",
    "version": "18.0.0.0.1",
    "category": "Accounting/Sales",
    "website": "https://www.plennix.com/",
    "author": "Plennix",
    "depends": ["account", "gulfco_customer_customized_data", "gulfco_product_customized_data", "plnx_sales_team"],
    "data": [
        "security/ir.model.access.csv",
        "report/sale_budget_report_view.xml",
        "views/sales_budget_line_view.xml",
        "views/sales_budget_view.xml",
    ],
    "installable": True,
    'assets': {
        'web.assets_backend': [
            'gulfco_sales_budget/static/src/views/*',
        ],
    },

}
