{
    'name': "OL RMA Extended",
    'version': "18.0.1.0.0",
    'summary': "Extension module for RMA related features",
    'description': """
        This module adds return caused by feature and related configurations.
    """,
    'category': 'Sales',
    'author': "",
    'website': "",
    'license': 'AGPL-3',
    'depends': ['base', 'crm', 'rma','plnx_rma_extended'],  
    'data': [
        'security/ir.model.access.csv',
        'views/view_return_caused_by.xml',
        'views/rma.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
