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
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrderReport(models.AbstractModel):
    _name = 'report.purchase_line_views.report_rfq_purchase_order'
    _description = 'Purchase Order Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Get the purchase orders
        orders = self.env['purchase.order'].browse(docids)

        # Increment the print count(Revision) for each order
        for order in orders:
            order.revision += 1

        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': orders,
            # Add any other context you need for the report
        }
