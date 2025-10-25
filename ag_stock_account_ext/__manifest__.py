{
    "name": "Stock Account Extension",
    "version": "18.0.1.0.2",
    "summary": "Stock Account Extension",
    "description": """
        tock Account Extension
    """,
    "author": "APPS-GATE",
    "website": "https://apps-gate.net",
    "license": "OPL-1",
    "category": "Inventory",
    "depends": [
        "product",
        "stock_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_move_views.xml",
        "wizard/product_cost_update.xml",
        "wizard/update_cogs.xml",
        "wizard/val_generate_jv.xml",
        "wizard/correct_valuation.xml"
    ],
    "installable": True,
    "application": False,
}
