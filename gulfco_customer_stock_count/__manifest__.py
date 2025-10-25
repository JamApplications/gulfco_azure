{
    "name": "Customer Stock Count",
    "version": "1.1",
    "depends": ["stock", "fieldservice", "fieldservice_sale"],
    'author': "Plennix",
    'website': "https://www.plennix.com/",
    "category": "Inventory",
    "description": "Module to manage customer stock counts from field service visits.",
    'depends': ['fieldservice', 'plnx_sales_team',],
    "data": [
        "security/ir.model.access.csv",
        "views/customer_stock_views.xml",
        "views/fsm_order.xml",
    ],
    "installable": True,
    "auto_install": False,
}
