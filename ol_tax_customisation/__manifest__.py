{
    'name': "Tax Customisation",
    'version': "18.0.1.0.0",
    'description': """
    """,
    'author': "",
    'website': "",
    'license': 'AGPL-3',
    'depends': ['base', 'account', 'l10n_ae_corporate_tax_report', 'hr_expense', 'sale', 'purchase'],  
    'data': [
        # 'security/ir.model.access.csv',
        # 'data/report_extension.xml',
        'views/account_tax_view.xml',
        'views/account_move_views.xml',
        'views/hr_expense_views.xml',
        'views/purchase_order_line_views.xml',
        'views/sale_order_line_views.xml',
        # 'views/rma.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
