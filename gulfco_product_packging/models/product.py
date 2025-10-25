# -*- coding: utf-8 -*-
#############################################################################
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
from odoo import fields, models, api, _
import ast
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning



class ProductPackage(models.Model):
    _inherit = "product.packaging"

    @api.depends('product_id')
    def _get_packaging_domain(self):
        for record in self:
            if record.product_id:
                record.p_domain = record.product_id.packaging_ids.ids
            else:
                record.p_domain = []


    product_id = fields.Many2one('product.product', string='Product', check_company=True, required=True,
                                 ondelete="cascade")
    secondary_package = fields.Many2one('product.packaging', string="Secondary Package",
                                        domain="[('id','in', p_domain)]")
    p_domain = fields.Many2many('product.packaging', string="Packaging Domain", compute=_get_packaging_domain)




class ProductTemplate(models.Model):
    _inherit = 'product.template'

    line_added = fields.Boolean(string="Added", default=False)

    # def open_packaging_wizard(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Add Product Packaging',
    #         'res_model': 'product.packaging',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_product_id': self.env['product.product'].search([('product_tmpl_id', '=', self.id), ('active', 'in', [True, False])]).id,
    #         }
    #     }