# -*- coding: utf-8 -*-
{
    'name': "Gulfco Approval Custom",
    'author': "Plennix",
    'website': "https://www.plennix.com",
    'category': 'Approval',
    'version': '18.0',
    'depends': ['purchase_line_views', 'gulfco_contact_registration_custom', 'stock_inventory_adjustment',
                'gulfco_demand_planning'],
    'data': [
        'data/mail_activity_type.xml',
        'data/pr_line_server_actions.xml',
        'views/purchase_requisition_views.xml',
        'views/purchase_request_view.xml',
        'views/purchase_order_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gulfco_approval_custom/static/src/**/*',
        ],
    },
}
