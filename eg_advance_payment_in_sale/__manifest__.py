{
    'name': 'Advance Payment in Sale Order',
    'version': '18.0',
    'category': 'Accounting',
    'summary': 'Advance Payment in Sale Order',
    'author': "Plennix Technologies",
    'website': "https://www.plennix.com",
    'depends': ['account', 'sale_management'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/advance_payment_wizard_view.xml',
        'views/sale_order_view.xml',
    ],

    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}
