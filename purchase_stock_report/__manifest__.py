{
    'name': 'Purchase & Stock Report',
    'version': '1.0',
    'summary': 'Tree view report for Purchases and Stock Transfers',
    'description': """
        Custom module to show Purchase & Stock movements in a tree view.
    """,
    'category': 'Inventory',
    'author': 'JAM',
    'depends': ['stock', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_stock_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
