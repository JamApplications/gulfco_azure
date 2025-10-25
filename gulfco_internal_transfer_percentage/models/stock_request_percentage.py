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
from docutils.parsers.rst.directives import percentage
from odoo import fields, models, api, _

import logging

_logger = logging.getLogger(__name__)


class StockRequestPercentage(models.Model):
    _name = 'stock.request.percentage'
    _description = 'Stock Request Percentage Configuration'

    code = fields.Char(string="Code")
    name = fields.Char(string="Name")
    line_ids = fields.One2many(comodel_name='stock.request.percentage.line', inverse_name='percentage_id', string='Line IDs')
    active = fields.Boolean(string='Active', default='True')
    state = fields.Selection(selection=[('active','Active'),
                                        ('deactive','De-Active')], string='State', default='active')


    def action_deactive(self):
        return True

    def action_active(self):
        return True



class StockRequestPercentageLoad(models.Model):
    _name = 'stock.request.percentage.load'
    _description = 'Stock Request Percentage Load Configuration'

    code = fields.Char(string="Code")
    name = fields.Char(string="Name")
    line_ids = fields.One2many(comodel_name='stock.request.percentage.load.line', inverse_name='percentage_id', string='Line IDs')
    active = fields.Boolean(string='Active', default='True')
    state = fields.Selection(selection=[('active','Active'),
                                        ('deactive','De-Active')], string='State', default='active')


    def action_deactive(self):
        return True

    def action_active(self):
        return True


class StockRequestPercentageLoadLine(models.Model):
    _name = 'stock.request.percentage.load.line'
    _description = 'Stock Request Percentage Load Configuration Line'

    percentage_id = fields.Many2one(comodel_name='stock.request.percentage.load', string='Percentage Setup')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    category_id = fields.Many2one(comodel_name='product.category', string='Product Category')
    percentage = fields.Float(string='Percentage')



class StockRequestPercentageLine(models.Model):
    _name = 'stock.request.percentage.line'
    _description = 'Stock Request Percentage Configuration Line'

    percentage_id = fields.Many2one(comodel_name='stock.request.percentage', string='Percentage Setup')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    category_id = fields.Many2one(comodel_name='product.category', string='Product Category')
    percentage = fields.Float(string='Percentage')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

        # def action_assign(self):
        #     _logger.info("inside assign ->>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        #     if self.request_order_id.direction == 'branch_transfer':
        #         _logger.info("inside first if of  assign ->>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        #         for line in self.move_ids:
        #             for l in line.move_line_ids:
        #                 l.unlink()
        #             move_list = []
        #             child_list=[]
        #             remaining = line.product_uom_qty
        #             percentage_config = self.env['stock.request.percentage.line'].search([('warehouse_id', '=', self.location_id.warehouse_id.id)])
        #             if percentage_config and percentage_config[0].category_id:
        #                 child_list = self.env['product.category'].search([('id', 'child_of', percentage_config[0].category_id.id)]).ids
        #             if percentage_config and line.product_id.categ_id.id in child_list:
        #                 locations = self.env['stock.location'].search([('location_id', 'child_of', self.location_id.id),
        #                                                                ('usage','=','internal'),
        #                                                                ('is_saleable_location', '=', True),
        #                                                                ('tag_ids.name', '!=', 'Near Expiry')])
        #                 lots = self.env['stock.quant'].search([('product_id','=', line.product_id.id),
        #                                                     ('location_id', 'in', locations.ids)]).lot_id
        #                 lots=sorted(lots, key=lambda q: q.expiration_date)
        #                 for lot in lots:
        #                     current_days = (lot.expiration_date.date() - fields.date.today()).days + 1
        #                     life_days = 0
        #                     if lot.expiration_date and lot.production_date:
        #                         life_days = (lot.expiration_date.date() - lot.production_date).days + 1
        #                     if life_days > 0 and (current_days/life_days)*100 >= percentage_config.percentage:
        #                         quants = self.env['stock.quant'].search([('product_id', '=', line.product_id.id),
        #                                                                 ('location_id', 'in', locations.ids),
        #                                                                 ('lot_id', '=', lot.id),
        #                                                                 ('available_quantity', '>', 0)], order='expiration_date asc')
        #
        #                         if quants:
        #                             for q in quants:
        #                                 reserves = []
        #                                 if remaining <= 0:
        #                                     line.origin = line.picking_id.origin
        #                                     move_list.append({'quant_id': q.id,
        #                                                       'lot_id': lot.id,
        #                                                       'production_date': lot.production_date,
        #                                                       'expiration_date': lot.expiration_date,
        #                                                       'location_dest_id': self.location_dest_id.id,
        #                                                       'quantity': 0,
        #                                                       'move_id': line.id,
        #                                                       'origin': line.picking_id.origin,
        #                                                       'picking_id': line.picking_id.id})
        #                                 else:
        #                                     line.origin = line.picking_id.origin
        #                                     reserve = min(q.available_quantity, remaining)
        #                                     move_list.append({'quant_id': q.id,
        #                                                       'lot_id': lot.id,
        #                                                       'production_date': lot.production_date,
        #                                                       'expiration_date': lot.expiration_date,
        #                                                       'location_dest_id': self.location_dest_id.id,
        #                                                       'quantity': reserve,
        #                                                       'move_id': line.id,
        #                                                       'origin': line.picking_id.origin,
        #                                                       'picking_id': line.picking_id.id})
        #                                     remaining -= reserve
        #                 if move_list:
        #                     filtered = [d for d in move_list if d['quantity'] != 0]
        #                     for l in filtered:
        #                         line.write({
        #                             'move_line_ids': [
        #                                 (0, 0, l),
        #                             ]
        #                         })
        #     elif self.request_order_id.direction == 'van_load':
        #         _logger.info("inside assing van load ->>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        #         for line in self.move_ids:
        #             for l in line.move_line_ids:
        #                 l.unlink()
        #             move_list = []
        #             child_list=[]
        #             remaining = line.product_uom_qty
        #             percentage_config = self.env['stock.request.percentage.load.line'].search([('warehouse_id', '=', self.location_id.warehouse_id.id)])
        #             if percentage_config and percentage_config[0].category_id:
        #                 child_list = self.env['product.category'].search([('id', 'child_of', percentage_config[0].category_id.id)]).ids
        #             if percentage_config and line.product_id.categ_id.id in child_list:
        #                 locations = self.env['stock.location'].search([('location_id', 'child_of', self.location_id.id),
        #                                                                ('usage','=','internal'),
        #                                                                ('is_saleable_location', '=', True),
        #                                                                ('tag_ids.name', '!=', 'Near Expiry')])
        #                 lots = self.env['stock.quant'].search([('product_id','=', line.product_id.id),
        #                                                     ('location_id', 'in', locations.ids),
        #                                                     ('available_quantity', '>', 0)]).lot_id
        #                 lots=sorted(lots, key=lambda q: q.expiration_date)
        #                 for lot in sorted(lots, key=lambda q: q.expiration_date):
        #                     current_days = (lot.expiration_date.date() - fields.date.today()).days + 1
        #                     life_days = 0
        #                     if lot.expiration_date and lot.production_date:
        #                         life_days = (lot.expiration_date.date() - lot.production_date).days + 1
        #                     if life_days > 0 and (current_days/life_days)*100 >= percentage_config.percentage:
        #                         # quants = self.env['stock.quant'].search([('product_id', '=', line.product_id.id),
        #                         #                                         ('location_id', 'in', locations.ids),
        #                         #                                         ('lot_id', '=', lot.id),
        #                         #                                         ('available_quantity', '>', 0)], order='expiration_date asc')
        #                         quants = self.env['stock.quant']._get_reserve_quantity(
        #                             line.product_id,  self.location_id, line.product_uom_qty, product_packaging_id=line.product_packaging_id,
        #                             uom_id=line.product_uom, lot_id=lot, package_id=line.package_id, owner_id=line.partner_id,
        #                             strict=True)
        #                         # print(quants[0].quantity,quants[0].available_quantity, "111111111111111111111111111111111111111111111111111111111111")
        #                         if len(quants) > 0:
        #                         # if quants:
        #                             for q, quantity in quants:
        #                             # for q in quants:
        #
        #                                 reserves = []
        #                                 if remaining <= 0:
        #
        #                                     line.origin = line.picking_id.origin
        #                                     move_list.append({'quant_id': q.id,
        #                                                       'lot_id': lot.id,
        #                                                       'production_date': lot.production_date,
        #                                                       'expiration_date': lot.expiration_date,
        #                                                       'location_dest_id': self.location_dest_id.id,
        #                                                       'quantity': 0,
        #                                                       'move_id': line.id,
        #                                                       'origin': line.picking_id.origin,
        #                                                       'picking_id': line.picking_id.id})
        #                                 else:
        #                                     line.origin = line.picking_id.origin
        #                                     reserve = min(quantity, remaining)
        #                                     # reserve = min(q.available_quantity, remaining)
        #                                     move_list.append({'quant_id': q.id,
        #                                                       'lot_id': lot.id,
        #                                                       'production_date': lot.production_date,
        #                                                       'expiration_date': lot.expiration_date,
        #                                                       'location_dest_id': self.location_dest_id.id,
        #                                                       'quantity': reserve,
        #                                                       'move_id': line.id,
        #                                                       'origin': line.picking_id.origin,
        #                                                       'picking_id': line.picking_id.id})
        #                                     remaining -= reserve
        #                 if move_list:
        #                     filtered = [d for d in move_list if d['quantity'] != 0]
        #                     for l in filtered:
        #                         line.write({
        #                             'move_line_ids': [
        #                                 (0, 0, l),
        #                             ]
        #                         })
        #     else:
        #         _logger.info("inside else of assign")
        #         res = super(StockPicking, self).action_assign()
        #         _logger.info(res)
        #         return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        if self.parent_id and self.parent_id.category_id:
            return {
                'domain': {
                    'product_id': [('categ_id', '=', self.parent_id.category_id.id)]
                }
            }