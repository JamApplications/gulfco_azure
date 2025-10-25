{
    'name': 'Advance Payment in Sale And Purchase Journal Entry',
    'version': '18.0',
    'category': 'Accounting',
    'author': "Plennix Technologies",
    'website': "https://www.plennix.com",
    'depends': ['account', 'eg_advance_payment_in_purchase','eg_advance_payment_in_sale', 'account_pdc'],

    'data': [
        'views/account_product_view_inherit.xml'
    ],

    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}
