{
    "name": "Gulfco Advanced Reporting",
    "summary": "Single SQL view over invoices, sales, pickings, RMA lines — with list/pivot/graph/search and dashboard tile.",
    "version": "18.0.1.0.0",
    "author": "Al-majid.com",
    "website": "al-majid.com",
    "license": "OPL-1",
    "category": "Reporting",
    "depends": [
        "sale_management",
        "account",
        "stock",
        'gulfco_sale_extanded',
        'gulfco_cash_transaction_limit',
        "board",   # for dashboard tile
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/mw_sales_rma_report_views.xml",
        # "data/cron.xml",  # uncomment if you switch to MATERIALIZED VIEW
    ],
    "installable": True,
    "application": True,
    "sequence": 1,
}