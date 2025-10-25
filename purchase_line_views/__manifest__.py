# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': "Purchase Order Line View",
    "category": "Purchases",
    "version": "18.0.1.0.0",
    "description": "View the purchase order and RFQ order line",
    "summary": "Access purchase order lines and"
               " RFQs through various intuitive views "
               "including tree view, kanban, calendar, pivot, and graph. "
               "Effortlessly navigate between different perspectives "
               "for enhanced visualization and analysis.",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['purchase', 'purchase_requisition', 'purchase_requisition_stock', 'account', 'asn_request', 'product',
                'gulfco_vendor_customized_data', "stock_gl_account"],
    'data': [
        "security/ir.model.access.csv",
        "wizard/accured_order_view.xml",
        "reports/purchase_bill_matching_report.xml",
        "views/res_config_setting_views.xml",
        "views/account_journal_view.xml",
        "views/purchase_order_line_views.xml",
        'views/rfq_line_views.xml',
        'views/purchase_order_inherit_view.xml',
        'views/purchase_requisition_view_inehrit.xml',
        'views/product_view_inherit.xml',
        'views/purchase_requisition_views.xml',
        'views/excise_declaration.xml',
        'views/stock_picking_view.xml',
        'views/purchase_requisition_view.xml',
        'views/account_move_view.xml',
        'reports/purchase_external_layout.xml',
        'reports/report_rfq_purchase_order.xml',
        'data/purchase_email_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_line_views/static/src/scss/readonly_row.scss',
            'purchase_line_views/static/src/js/action_hide.js',
            'purchase_line_views/static/src/js/list_renderer.js',
        ],
    },
    'images': [
        'static/description/banner.jpg'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
