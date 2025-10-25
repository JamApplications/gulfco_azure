{
    "name": "ASN Request",
    "summary": "ASN Request",
    "version": "18.0.0.0.0",
    "category": "Stock",
    "depends": ["base", "stock", "purchase", "gulfco_product_customized_data", "stock_landed_costs"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/print_excel_server_action.xml",
        "views/account_plan_view.xml",
        "views/analytic_account_view.xml",
        "views/asn_request_views.xml",
        "views/asn_request_line_views.xml",
        "views/account_move_views.xml",
        "views/asn_stage.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
    "author": "Plennix",

}
