{
    'name': "Sale Customisation",
    'version': "18.0.1.0.0",
    'description': """
    """,
    'author': "",
    'website': "",
    'license': 'AGPL-3',
    'depends': ['base','sale', 'account', 'stock','gulfco_sale_extanded','purchase'],
    'data': [
        # 'security/ir.model.access.csv',
        'data/sale_quotation.xml',
        'views/sale_order_view.xml',
        # 'views/rma.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
