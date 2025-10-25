{
    "name": "Salesperson Filter in Accounting Reports",
    "version": "18.0.0.0.0",
    "website": "https://www.plennix.com/",
    "category": "Accounting/Accounting",
    "description": """
        Salesperson/Sales Team Filter in Accounting Reports
    """,
    "author": "Plennix Technologies",
    "depends": ["base", "account_reports", "sales_team"],
    "data": [
        "views/account_report_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "gulfco_account_report_filters/static/src/components/filters/filters.xml",
        ],  
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
