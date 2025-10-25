# -*- coding: utf-8 -*-
{
    'name': "Barcode Employee PIN",
    'author': "Plennix",
    'website': "https://www.plennix.com",
    'category': 'stock  ',
    'version': '18.0',
    'summary': 'Barcode Employee PIN Login',
    'description': """
            Barcode Employee PIN Login
            ==============================
            - create Multiple user access barcode app with pin allow access on user
        """,
    'author': 'Plennix',
    'depends': ['base', 'hr', 'stock_barcode','web', 'stock_picking_batch', 'mrp',
                'stock_barcode_mrp', 'stock_barcode_picking_batch', "stock_inbounding_lot"],

    'data': [
        "security/ir.model.access.csv",
        "views/stock_picking_views.xml",
        'views/hr_employee_view_inherit.xml',
        'views/res_users_view_inherit.xml',
        'views/mrp_production_view_inherit.xml',
        'views/stock_picking_batch_view.xml',
        'views/stock_quant_inventory_view.xml',
        'views/stock_move_line_views.xml',
        'wizard/employee_barcode_pin_wiz.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'plnx_barcode_employee_pin/static/src/js/barcode_main.js',
            'plnx_barcode_employee_pin/static/src/js/PinInputDiolog.js',
            'plnx_barcode_employee_pin/static/src/js/batch_picking.js',
            'plnx_barcode_employee_pin/static/src/js/barcode_model.js',
            'plnx_barcode_employee_pin/static/src/js/barcode_quant_model.js',
            # 'plnx_barcode_employee_pin/static/src/xml/barcode_pin_pupup.xml',
            'plnx_barcode_employee_pin/static/src/xml/pinInput.xml',
            # 'plnx_barcode_employee_pin/static/src/xml/PInDilogPopup.xml',
            'plnx_barcode_employee_pin/static/src/xml/line.xml',

            'plnx_barcode_employee_pin/static/src/js/main_component/main.js',
            'plnx_barcode_employee_pin/static/src/js/main_component/main_menu.js',
            'plnx_barcode_employee_pin/static/src/js/main_component/main_menu.xml',

            'plnx_barcode_employee_pin/static/src/js/control_panel/barcode_store.js',
            'plnx_barcode_employee_pin/static/src/js/control_panel/control_panel.js',
            'plnx_barcode_employee_pin/static/src/js/control_panel/control_panel.xml',

        ],
    },

}
