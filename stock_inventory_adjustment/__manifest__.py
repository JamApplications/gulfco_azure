{
    "name": "Stock Inventory Adjustment",
    "version": "18.0.0.0.0",
    "category": "Stock",
    "website": "https://www.plennix.com/",
    "author": "Plennix",
    "depends": ["stock", 'sales_team', 'gulfco_product_customized_data', 'gulfco_vendor_customized_data'],
    "data": [
        "security/ir.model.access.csv",
        "security/security_group.xml",
        "data/print_excel_discrepancy_report_action.xml",
        "wizard/reject_reason_view.xml",
        "report/discrepancy_report.xml",
        "views/stock_inventory_adjustment_view.xml",
    ],
    "installable": True,

}
