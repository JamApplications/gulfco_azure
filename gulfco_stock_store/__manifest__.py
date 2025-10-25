{
    'name': 'Stock in Store',
    'version': '1.0',
    'summary': 'Manage stock records for store visits under the Inventory module.',
    'description': 'This module adds a new menu "Stock in Store" under Inventory, accessible only to Merchandise User group. It allows tracking stock details with auto-populating fields like Location, Customer, Date, and Worker Name.',
    'author': "Plennix",
    'website': "https://www.plennix.com/",
    'depends': ['fieldservice', 'plnx_sales_team', 'gulfco_customer_stock_count'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_store.xml',
        'views/fsm_order.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
