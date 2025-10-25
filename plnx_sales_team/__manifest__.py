# -*- coding: utf-8 -*-
{
    'name': "Plennix Sales Team",
    'author': "Plennix",
    'website': "https://www.plennix.com",
    'category': 'Sales  ',
    'version': '18.0',
    'summary': 'Enhance Fields Service apps.',
    'description': """
            Gulfco Fields Service apps Enhancement
            ==============================
            - created customer mapping configuration in sales team
            - modify sales team member form users to partner
            - create sale order quote from the visit order
            - create RMA records from the visit order
            - added password configuration for sales team in fieldservice
        """,
    'author': 'Plennix',
    'depends': ['base','sales_team', 'fieldservice',
                'rma', 'plnx_rma_order', 'project', 'gulfco_customer_customized_data', "gulfco_contact_registration_custom"],

    'data': [
        "security/ir.model.access.csv",
        'security/res_group.xml',
        "views/crm_team_views.xml",
        'views/customer_mapping_view.xml',
        'views/fsm_order.xml',
        'views/sale_order.xml',
        'views/rma_order_view_inherit.xml',
        'views/fieldservice_team_password_view.xml',
        'views/res_partner_view.xml',
        'views/customer_channel_view.xml',
    ],
    'summary': """Plennix Sales Team""",
    'description': """
            Plennix Sales Team
   """,
}
