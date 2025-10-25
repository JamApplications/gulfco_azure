# -*- coding: utf-8 -*-
{
    'name': "Plennix Gulfco Sales Commission",
    'author': "Plennix",
    'website': "https://www.plennix.com",
    'category': 'Sales  ',
    'version': '18.0',
    'summary': 'Sales Commission Enhancement',
    'description': """
            Gulfco Sales Commission apps Enhancement
            ==============================
            - Sales target comission 
            - add KPI new model
            - calculate commission based on target achived
            - Collection type commission calculation has been added 
            - MSL type commission calculation has been added
            
        """,
    'author': 'Plennix',
    'depends': ['sale_management', 'sale_commission', 'hr', 'account', 'sale', 'plnx_sales_team'],

    'data': [
        "security/ir.model.access.csv",
        "views/sales_commission_plan_view.xml",
        'views/commission_kpi_view.xml',
        'views/account_payment_view.xml',
        'views/msl_commission_view.xml',
        'views/sale_order_view_inherit.xml',
        'views/account_move_view_inherit.xml',
        'report/commission_achievement_view_inherit.xml',
        'report/commission_report_inherit.xml',
        'wizard/sale_commission_add_multiple_user.xml',

    ],

}
