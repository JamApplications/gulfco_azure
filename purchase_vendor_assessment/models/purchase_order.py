# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    assessment_purchase_id = fields.Many2one(
        comodel_name="assessment.purchase",
        copy=False,
    )
    # assessment_purchase_state = fields.Selection(
    #     related="assessment_purchase_id.state",
    #     store=True,
    #     copy=False
    # )

    # Criteria mapping fields
    # ETA_score = fields.Float()
    has_return_receipt = fields.Boolean(string='Has Return Receipt', compute='_compute_has_return_receipt', store=True, default=False)

    @api.depends('picking_ids','picking_ids.state')
    def _compute_has_return_receipt(self):
        for order in self:
            # Check if there are any related return receipts
            order.has_return_receipt = any(
                picking.picking_type_id.code == 'outgoing' and picking.return_id for picking
                in order.picking_ids)

    no_price_diff = fields.Boolean(string='Price Not Changed', compute='_compute_price_changed', store=True, default=True)

    @api.depends('order_line.price_subtotal', 'order_line.price_unit')
    def _compute_price_changed(self):
        for order in self:
            # Initialize the price changed flag
            if order.picking_ids:
                order.no_price_diff = False

    received_less_qty = fields.Boolean(string='Received Less Quantity',  compute='_compute_received_less_qty',default=False)
    quality_check_fail = fields.Boolean(compute='_compute_received_less_qty',default=False)

    # @api.depends('order_line.qty_received', 'order_line.product_qty', 'picking_ids','picking_ids.state', 'picking_ids.quality_check_fail')
    def _compute_received_less_qty(self):
        for order in self:
            order.received_less_qty = False
            order.quality_check_fail = False
            if order.state in ['purchase', 'done'] and 'done' in order.picking_ids.mapped('state'):
                order.received_less_qty = any(line.qty_received < line.product_qty for line in order.order_line)

            order.quality_check_fail = any(picking.quality_check_fail == True for picking in order.picking_ids)

