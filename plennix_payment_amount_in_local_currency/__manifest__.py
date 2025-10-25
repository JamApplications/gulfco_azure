{
    'name': "Plennix Payment Amount in Local Currency",
    'version': "18.0.1.0.0",
    'description': """
    Add Payment in Local Currency in Payment
    """,
    'author': "plennix",
    'website': "https://www.plennix.com",
    'license': 'AGPL-3',
    'depends': ['base', 'account', 'exchange_currency_rate'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_payment.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
