from odoo import models, fields, api
from odoo.tools.float_utils import float_compare,float_is_zero

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # state = fields.Selection(related='order_id.state',  compute='_compute_po_line_status', store=True)


    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ("scm_confirm", "SCM Confirm"),
        ("financial_dep_approve", "Financial Dep approve"),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')
    ], string="Status hI BY", compute='_compute_po_line_state', store=True)

    @api.depends('order_id', 'asn_released_qty', 'product_qty', 'order_id.state', 'order_id.picking_id', 'order_id.picking_id.state')
    def _compute_po_line_state(self):
        for rec in self:
            rec.state = rec.order_id.state
            if rec.asn_released_qty == rec.product_qty:
                rec.state = 'done'


    @api.depends_context('is_from_asn_request')
    def _compute_display_name(self):
        for line in self:
            if self.env.context.get('is_from_asn_request'):
                line.display_name = line.po_line_index
            else:
                line.display_name = line.display_name

    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        if self.env.context.get('from_asn_request'):
            res = []
            if self.product_id.type != 'consu':
                return res
            price_unit = self._get_stock_move_price_unit()
            qty = self._get_qty_procurement()

            # move_dests = self.move_dest_ids or self.move_ids.move_dest_ids
            # move_dests = move_dests.filtered(lambda m: m.state != 'cancel' and not m._is_purchase_return())

            # if not move_dests:
            qty_to_attach = 0
            # if self.env.context.get('from_asn_request'):
            if self.env.context.get('asn_record'):
                line = self.env.context.get('asn_record').line_ids.filtered(
                    lambda s: s.purchase_order_line_id == self)
                # qty_to_push = line.asn_released_qty - qty
                qty_to_push = line.qty_in_invoice
                # qty_to_push = line.qty_in_invoice - qty
            else:
                line = self.order_id.asn_ids.line_ids.filtered(lambda s:s.purchase_order_id == self.order_id)
                # qty_to_push = line.asn_released_qty - qty
                qty_to_push = line.qty_in_invoice
                # qty_to_push = line.qty_in_invoice - qty
            # else:
            #     qty_to_push = self.product_qty - qty
            # else:
            #     move_dests_initial_demand = self._get_move_dests_initial_demand(move_dests)
            #     qty_to_attach = move_dests_initial_demand - qty
            #     if self.env.context.get('from_asn_request'):
            #         if self.env.context.get('asn_record'):
            #             line = self.env.context.get('asn_record').line_ids.filtered(lambda s: s.purchase_order_line_id == self)
            #             # if move_dests_initial_demand >= line.asn_released_qty:
            #             #     qty_to_push = line.asn_released_qty
            #             # if move_dests_initial_demand >= line.qty_in_invoice:
            #             #     qty_to_push = line.qty_in_invoice
            #             if line.qty_in_invoice:
            #                 qty_to_push = line.qty_in_invoice
            #             else:
            #                 qty_to_push = self.product_qty - move_dests_initial_demand

            #         else:
            #             line = self.order_id.asn_ids.line_ids.filtered(lambda s:s.purchase_order_id == self.order_id)

            #             # if move_dests_initial_demand >= line.asn_released_qty:
            #             #     qty_to_push = line.asn_released_qty
            #             # if move_dests_initial_demand >= line.qty_in_invoice:
            #             if line.qty_in_invoice:
            #                 qty_to_push = line.qty_in_invoice
            #             else:
            #                 qty_to_push = self.product_qty - move_dests_initial_demand
            #     else:
            #         qty_to_push = self.product_qty - move_dests_initial_demand
            # if float_compare(qty_to_attach, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            #     product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_attach, self.product_id.uom_id)
            #     res.append(self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom))
            if not float_is_zero(qty_to_push, precision_rounding=self.product_uom.rounding):
                product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_push, self.product_id.uom_id)
                extra_move_vals = self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
                extra_move_vals['move_dest_ids'] = False  # don't attach
                res.append(extra_move_vals)
            return res
        else:
            return super()._prepare_stock_moves(picking)


    @api.model
    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if self.env.context.get('from_asn_request'):
            if self.env.context.get('asn_record'):
                line = self.env.context.get('asn_record').line_ids.filtered(
                    lambda s: s.purchase_order_line_id == self)
                if line:
                    res.update({"asn_line_id": line.id})
        return res