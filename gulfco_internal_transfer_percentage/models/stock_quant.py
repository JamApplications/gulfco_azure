from odoo import _, api, fields, models, SUPERUSER_ID
from datetime import date
import logging
from odoo.tools.float_utils import float_compare,float_is_zero
from odoo.exceptions import UserError
from collections import defaultdict


_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, qty=0):
        res = super(StockQuant, self)._gather(product_id, location_id,
                                              lot_id=lot_id,
                                              package_id=package_id,
                                              owner_id=owner_id,
                                              strict=strict,
                                              qty=qty)
        _logger.info("Gether Res first value: %s" % res)
        if self.env.context.get('custom_request_order_id'):
            _logger.info("INTERNAL #########################################################################")
            removal_strategy = self._get_removal_strategy(product_id, location_id)
            _logger.info("RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR%s" % (removal_strategy))
            child_list = []
            stock_request_order_id = self.env['stock.request.order'].browse(
                self.env.context.get('custom_request_order_id'))
            if stock_request_order_id.direction in ['branch_transfer']:
                percentage_config = self.env['stock.request.percentage.line'].search(
                    [('warehouse_id', '=', location_id.warehouse_id.id)])
                if percentage_config and percentage_config[0].category_id:
                    child_list = self.env['product.category'].search(
                        [('id', 'child_of', percentage_config[0].category_id.id)]).ids
                if percentage_config and product_id.categ_id.id in child_list:
                    today = fields.Date.today()
                    res = res.filtered(lambda q: (
                            q.lot_id
                            and q.lot_id.expiration_date
                            and q.lot_id.production_date
                            and (q.lot_id.expiration_date.date() - q.lot_id.production_date).days + 1 > 0
                            and (((q.lot_id.expiration_date.date() - today).days + 1) /
                                 ((q.lot_id.expiration_date.date() - q.lot_id.production_date).days + 1)) * 100
                            >= percentage_config.percentage
                    ))
                    if removal_strategy in ['fifo', 'least_packages']:
                        res = res.sorted(lambda s: s.in_date and s.id)
                    elif removal_strategy == 'lifo':
                        res = res.sorted(lambda s: s.in_date and s.id, reverse=True)
                    elif removal_strategy == "closest":
                        res = res.sorted(lambda q: (q.location_id.complete_name, -q.id))
                    elif removal_strategy == 'fefo':
                        res = res.sorted(key=lambda r: (not r.expiration_date, r.expiration_date or False))
            if stock_request_order_id.direction in ['van_load']:
                _logger.info("LOAD #########################################################################")
                percentage_config = self.env['stock.request.percentage.load.line'].search(
                    [('warehouse_id', '=', location_id.warehouse_id.id)])
                if percentage_config and percentage_config[0].category_id:
                    child_list = self.env['product.category'].search(
                        [('id', 'child_of', percentage_config[0].category_id.id)]).ids

                if percentage_config and product_id.categ_id.id in child_list:
                    today = fields.Date.today()
                    res = res.filtered(lambda q: (
                            q.lot_id
                            and q.lot_id.expiration_date
                            and q.lot_id.production_date
                            and (q.lot_id.expiration_date.date() - q.lot_id.production_date).days + 1 > 0
                            and (((q.lot_id.expiration_date.date() - today).days + 1) /
                                 ((q.lot_id.expiration_date.date() - q.lot_id.production_date).days + 1)) * 100
                            >= percentage_config.percentage
                    ))
                    _logger.info(
                        "111111111111111111111111111111111111111111111111111111111111111111111111111111%s" % (res))
                    if removal_strategy in ['fifo', 'least_packages']:
                        _logger.info(
                            "2222222222222222222222222222222222222222222222222222222222222222222222222222%s" % (res))
                        res = res.sorted(lambda s: s.in_date and s.id)
                    elif removal_strategy == 'lifo':
                        _logger.info(
                            "33333333333333333333333333333333333333333333333333333333333333333333333333%s" % (res))
                        res = res.sorted(lambda s: s.in_date and s.id, reverse=True)
                    elif removal_strategy == "closest":
                        _logger.info(
                            "444444444444444444444444444444444444444444444444444444444444444444444444444%s" % (res))
                        res = res.sorted(lambda q: (q.location_id.complete_name, -q.id))
                    elif removal_strategy == 'fefo':
                        res = res.sorted(key=lambda r: (not r.expiration_date, r.expiration_date or False))
                        _logger.info(
                            "5555555555555555555555555555555555555555555555555555555555555555555555555555555%s" % (res))
        # if self.env.context.get('context_product_packaging_id'):
        #     _logger.info("inside context prodcut packagaig")
        #     removal_strategy = self._get_removal_strategy(product_id, location_id)
        #     _logger.info("inside context prodcut packagaig %s" % (removal_strategy))
        #     if location_id.location_group != 'van':
        #         _logger.info("location group not van")
        #         if product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full":
        #             res = res.filtered(lambda s: (s.quantity - s.reserved_quantity) >= qty)
        #             if removal_strategy in ['fifo', 'least_packages']:
        #                 res = res.sorted(lambda s: s.in_date and s.id)
        #             elif removal_strategy == 'lifo':
        #                 res = res.sorted(lambda s: s.in_date and s.id, reverse=True)
        #             elif removal_strategy == "closest":
        #                 res = res.sorted(lambda q: (q.location_id.complete_name, -q.id))
        #             elif removal_strategy == 'fefo':
        #                 _logger.info("the strategy is fefo")
        #                 res = res.sorted(key=lambda r: (not r.expiration_date, r.expiration_date or False))
        #     else:
        #         _logger.info("the location group is van so it should work as it's")
        _logger.info("Gether Res final values: %s" % res)
        return res

    # def _get_reserve_quantity(self, product_id, location_id, quantity, product_packaging_id=None, uom_id=None,
    #                           lot_id=None, package_id=None, owner_id=None, strict=False):
    #     return super(StockQuant,
    #                  self.with_context(context_product_packaging_id=product_packaging_id))._get_reserve_quantity(
    #         product_id, location_id, quantity, product_packaging_id, uom_id, lot_id, package_id, owner_id, strict)

    def _get_reserve_quantity(self, product_id, location_id, quantity, product_packaging_id=None, uom_id=None, lot_id=None, package_id=None, owner_id=None, strict=False):
        """ Get the quantity available to reserve for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. If no quants are in self, `_gather` will do a search to fetch the quants
        Typically, this method is called before the `stock.move.line` creation to know the reserved_qty that could be use.
        It's also called by `_update_reserve_quantity` to find the quant to reserve.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            could be done and how much the system is able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding

        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, qty=quantity)

        # avoid quants with negative qty to not lower available_qty
        available_quantity = quants._get_available_quantity(product_id, location_id, lot_id, package_id, owner_id, strict)

        # do full packaging reservation when it's needed
        if product_packaging_id and product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full":
            available_quantity = product_packaging_id._check_qty(available_quantity, product_id.uom_id, "DOWN")

        quantity = min(quantity, available_quantity)

        # `quantity` is in the quants unit of measure. There's a possibility that the move's
        # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
        # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
        # to convert `quantity` to the move's unit of measure with a down rounding method and
        # then get it back in the quants unit of measure with an half-up rounding_method. This
        # way, we'll never reserve more than allowed. We do not apply this logic if
        # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
        # will take care of changing the UOM to the UOM of the product.
        if not strict and uom_id and product_id.uom_id != uom_id:
            quantity_move_uom = product_id.uom_id._compute_quantity(quantity, uom_id, rounding_method='DOWN')
            quantity = uom_id._compute_quantity(quantity_move_uom, product_id.uom_id, rounding_method='HALF-UP')

        if product_id.tracking == 'serial':
            if float_compare(quantity, int(quantity), precision_rounding=rounding) != 0:
                quantity = 0

        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
        else:
            return reserved_quants

        negative_reserved_quantity = defaultdict(float)
        for quant in quants:
            if float_compare(quant.quantity - quant.reserved_quantity, 0, precision_rounding=rounding) < 0:
                negative_reserved_quantity[(quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)] += quant.quantity - quant.reserved_quantity
        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                negative_quantity = negative_reserved_quantity[(quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)]
                if negative_quantity:
                    negative_qty_to_remove = min(abs(negative_quantity), max_quantity_on_quant)
                    negative_reserved_quantity[(quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)] += negative_qty_to_remove
                    max_quantity_on_quant -= negative_qty_to_remove
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                if product_packaging_id and product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full" and location_id.location_group != 'van':
                    max_quantity_on_quant = product_packaging_id._check_qty(max_quantity_on_quant, product_id.uom_id, "DOWN")
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                if product_packaging_id and product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full" and location_id.location_group != 'van':
                    max_quantity_on_quant = product_packaging_id._check_qty(max_quantity_on_quant, product_id.uom_id,
                                                                            "DOWN")
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants
