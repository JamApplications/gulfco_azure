{
    "name": "Rma Analysis",
    "summary": " rma.line",
    'version': '18.0.1.0.0',
    "author": "Your Company",
    "license": "AGPL-3",
    "depends": [
        "base",
        "stock",
        "plnx_mrp_lot_production",
        "plnx_rma_extended",
        "plnx_rma_order",
        "ol_rma_extended",
        "account",
        'product',
        "mail",
        "rma",
    ],
    "data": [
        "security/ir.model.access.csv",
        'views/rma_analysis_excel_wizard.xml',
        'views/rma_analysis_menu.xml',

    ],
    "installable": True,
    "application": True,
}


