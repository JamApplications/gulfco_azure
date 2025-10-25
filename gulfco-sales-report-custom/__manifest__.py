{
    'name': 'sales Excel Report',
    'version': '1.0',
    'category': 'Accounting/sales',
    'summary': 'Export sales report to Excel',
    'description': 'Custom wizard to export sales data to Excel file',
    'depends': ['account', 'sale','rma', 'plnx_rma_extended', 'plnx_rma_order'],
    'data': [
        'security/ir.model.access.csv',
        'views/sales_order_rma_view.xml',
        'views/sales_order_report_views.xml',
        'views/sales_report_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
