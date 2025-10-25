# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

{
    'name': 'PowerBI Connector',
    'summary': """
        Odoo PowerBI Connector
        Odoo PowerBI Direct Connector
        PowerBI Odoo Integration
        Power BI Odoo Data Import
        Odoo PowerBI Sync
        Odoo Power BI Data Connector
        Odoo PowerBI Live Connection
        Odoo PowerBI User Access Control
        PowerBI Odoo Sudo Mode
        Odoo to Power BI Direct Fetch
        PowerBI Odoo Company Restrictions
        Odoo PowerBI Admin Access
        Odoo 17 PowerBI Connector
        Odoo 16 Power BI Module
        Odoo PowerBI Integration v18
        Odoo Business Intelligence
        PowerBI Odoo API Connector
        Odoo BI Data Extraction
        Odoo Power BI Dashboard Integration
    """,
    'company': 'EKIKA CORPORATION PRIVATE LIMITED',
    'author': 'EKIKA',
    'website': 'https://ekika.co',
    'category': 'Extra Tools,Tools',
    'version': '18.0.1.0',
    'license': 'OPL-1',
    'depends': ['web', 'external_connector_base'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/pb_report_tag_data.xml',
        'views/pb_dataset_configuration_views.xml',
        'views/pb_dashboard_configuration_views.xml',
        'views/powerbi_dashbaord_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdn.jsdelivr.net/npm/powerbi-client@2.18.7/dist/powerbi.min.js',
            'ek_powerbi_connector/static/src/components/**/*.js',
            'ek_powerbi_connector/static/src/components/**/*.xml',
            'ek_powerbi_connector/static/src/components/**/*.scss',
        ],
    },
    'live_test_url': 'https://ek_powerbi_connector-18.demo.odoo-apps.ekika.co/web/login?module=ek_powerbi_connector-18',
    'images': ['static/description/banner.gif'],
    'price': 52.25,
    'currency': 'EUR',
    'description': """
    """
}
