# -*- coding: utf-8 -*-
{
    'name': 'Gulfco Account Reports Custom',
    'version': '18.0.0.0.1',
    'sequence': 185,
    'category': 'Accounting Report Management',
    'website': 'https://www.plennix.com/',
    'summary': 'Extend account report Filteration based on analytic plans',
    'description': """

        Gulfco Account Reports Custom filteration based on analytic plans',
        ==============================

    """,
    'author': 'Plennix',
    'depends': [
        'base',
        'account',
        'account_reports',
        'web',
        'gulfco_contact_registration_custom'
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'data/soa_report.xml',
        'data/aged_partner_receivable_balance.xml',
        'data/customer_statement_report.xml',
        'data/account_tax_report_data.xml',
        'views/account_move_views.xml',
        'views/res_company_views.xml',
        'report/soa_pdf_report.xml',
        # 'report/account_followup_all_report.xml',
        'views/analytic_plan_views.xml',
        'views/analytic_report_view_inherit.xml',
        # 'views/customer_aging_report_view.xml',
        'report/customer_statement_supplier_soa_pdf_report.xml',
        'views/vendor_bills_field.xml',
        "views/account_account_views.xml",
    ],

    'assets': {
        'web.assets_backend': [
            'gulfco_account_reports/static/src/components/**/*',
        ],
        'web.assets_frontend': [],
    },
    'external_dependencies': {
        'python': ['toolz']
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
