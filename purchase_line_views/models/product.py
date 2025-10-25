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


class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    rdd = fields.Integer(
        'RDD', default=1, required=True,
        help="RDD time in days between the confirmation of the purchase order and the receipt of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning.")



class Product(models.Model):
    _inherit = "product.product"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self._context.get('po_type_context'):
            if self._context.get('po_type_context') == 'non_tradable':
                domain = domain.copy()
                domain.append((('item_type', '!=', 'tradable')))
            else:
                domain = domain.copy()
        return super()._search(domain, offset, limit, order)
