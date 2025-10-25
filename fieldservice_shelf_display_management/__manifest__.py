# -*- coding: utf-8 -*-
{
    'name': 'Shelf Display Management',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Manage Shelf Displays, Display Areas, and Display Area Lines',
    'author': 'Plennix',
    'website': "https://www.plennix.com/",
    'depends': ['base', 'fieldservice_account', 'plnx_sales_team'],  # Add dependencies as needed
    'data': [
        'security/ir.model.access.csv',
        'report/fsm_detail_report.xml',
        'wizard/fsm_details_report_view.xml',
        'views/shelf_display.xml',
        'views/display_area.xml',
        'views/res_partner_view.xml',
        'wizard/fsm_summary_report_view.xml',
        'views/summary_report.xml',
        'report/fsm_summary_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

