{
    'name': 'Advance Payment in Purchase',
    'version': '18.0',
    'category': 'Accounting',
    'summary': 'Advance Payment in Purchase',
     'author': "Plennix Technologies",
    'website': "https://www.plennix.com",
    'depends': ['account', 'purchase','purchase_requisition'],

    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/advance_payments_wizard_view.xml',
        'views/purchase_order_view.xml',
    ],

    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}
