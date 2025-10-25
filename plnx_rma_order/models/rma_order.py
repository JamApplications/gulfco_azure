# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RMA(models.Model):
    _inherit = 'rma'

    rma_order_id = fields.Many2one(comodel_name='rma.order', string='RMA Order')


class RMAOrder(models.Model):
    _name = 'rma.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'RMA Order'

    name = fields.Char(default=lambda self: _('New RMA Order'), copy=False)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', tracking=True)

    def confirm(self):
        rma_obj = self.env['rma']
        for rec in self:
            for line in rec.rma_line_ids:
                vals = {
                    'picking_id':line.origin_delivery_id.id,
                    'move_id':line.orign_move.id,
                    'product_id':line.product_id.id,
                    'product_uom_qty':line.product_uom_qty,
                    'operation_id':line.operation_id.id,
                    'rma_order_id':self.id,
                }
                if not line.rma_id or line.rma_id.state == 'cancelled':
                    rma_id = rma_obj.create(vals)
                    line.rma_id = rma_id.id
                else:
                    line.rma_id.write(vals)
            rec.write({'status': 'confirmed'})

    def draft(self):
        for rec in self:
            if any(line.state not in ('draft', 'cancelled') for line in rec.rma_ids):
                raise ValidationError(_('You cannot change status when there are RMAs with status other than draft or cancelled'))
            rec.write({'status': 'draft'})

    partner_id = fields.Many2one(
        string="Customer",
        comodel_name="res.partner",
        index=True,
        tracking=True,
    )
    partner_shipping_id = fields.Many2one(
        string="Shipping Address",
        comodel_name="res.partner",
        help="Shipping address for current RMA.",
        compute="_compute_partner_shipping_id",
        store=True,
        readonly=False,
    )
    partner_invoice_id = fields.Many2one(
        string="Invoice Address",
        comodel_name="res.partner",
        help="Refund address for current RMA.",
        compute="_compute_partner_invoice_id",
        store=True,
        readonly=False,
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="partner_id.commercial_partner_id",
    )

    @api.depends("partner_id")
    def _compute_partner_invoice_id(self):
        self.partner_invoice_id = False
        for record in self.filtered("partner_id"):
            address = record.partner_id.address_get(["invoice"])
            record.partner_invoice_id = address.get("invoice", False)

    @api.depends("partner_id")
    def _compute_partner_shipping_id(self):
        self.partner_shipping_id = False
        for record in self.filtered("partner_id"):
            address = record.partner_id.address_get(["delivery"])
            record.partner_shipping_id = address.get("delivery", False)

    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order', tracking=True)

    date = fields.Date(string='Date', tracking=True)
    responsible_id = fields.Many2one(comodel_name='res.users', string='Responsible', tracking=True)
    team_id = fields.Many2one(comodel_name='rma.team', string='Team', tracking=True)
    source_document = fields.Char(string='Source Document', tracking=True)
    remarks = fields.Text(string='Remarks', tracking=True)
    deadline_date = fields.Date(string='Deadline Date', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', tracking=True)


    rma_ids = fields.One2many(comodel_name='rma', string='RMA', inverse_name='rma_order_id')
    rma_count = fields.Integer(string='RMA count', compute='_compute_rma_count')

    @api.depends('rma_ids')
    def _compute_rma_count(self):
        for rec in self:
            rec.rma_count = len(rec.rma_ids)

    def action_view_rma(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': _('RMA'),
            'res_model': 'rma',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.rma_ids.ids)],
            'context': {'create': False},
        }
        return action

    rma_line_ids = fields.One2many(comodel_name='rma.order.line', inverse_name='rma_order_id')

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        for rec in self:
            rec.rma_line_ids.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New RMA Order')) == _('New RMA Order'):
                vals['name'] = (self.env['ir.sequence'].next_by_code('rma.order'))
        return super().create(vals_list)


class RMAOrderLine(models.Model):
    _name = 'rma.order.line'
    _description = 'RMA Order Line'

    rma_order_id = fields.Many2one(comodel_name='rma.order', string='RMA Order')

    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order',
                                    related='rma_order_id.sale_order_id')
    origin_delivery_domain = fields.Binary(compute='_compute_origin_delivery_domain')

    @api.depends('sale_order_id')
    def _compute_origin_delivery_domain(self):
        for rec in self:
            domain = [('picking_type_code', '=', 'outgoing')]
            if rec.sale_order_id:
                domain.append(('sale_id', '=', rec.sale_order_id.id))
            rec.origin_delivery_domain = domain

    origin_delivery_id = fields.Many2one(comodel_name='stock.picking', string='Origin Delivery',
                                         domain='origin_delivery_domain')
    orign_move = fields.Many2one(comodel_name='stock.move', string='Origin Move',)
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    product_uom_qty = fields.Float(string='Product qty')
    remaining_qty = fields.Float(string='Remaining qty', related='orign_move.remaining_qty')
    operation_id = fields.Many2one(comodel_name='rma.operation', string='Request Operation', required=1)
    rma_id = fields.Many2one(comodel_name='rma', string='RMA')

    @api.onchange('orign_move')
    def _onchange_origin_move(self):
        for rec in self:
            rec.product_id = rec.orign_move.product_id
            rec.product_uom_qty = rec.orign_move.product_uom_qty

            rec.origin_delivery_id = rec.orign_move.picking_id

    @api.onchange('origin_delivery_id')
    def _onchange_origin_delivery(self):
        for rec in self:
            rec.orign_move = False
