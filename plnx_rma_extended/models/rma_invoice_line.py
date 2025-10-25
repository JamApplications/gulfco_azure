
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import float_compare


rma_return_caused_by = [('admin_error', 'Administrative Error'),
                        ('customer_error', 'Customer'),
                        ('logistic_error', 'Logistic'),
                        ('order_entry_error', 'Order Entry'),
                        ('sales_error', 'Sales'),
                        ('warehouse_error', 'Warehouse'),
                        ]


class RMALine(models.Model):
    _name = 'rma.invoice.line'
    _inherit = "analytic.mixin"
    _description = 'RMA Invocie Line'

    product_id = fields.Many2one('product.product',string="Product")
    item_code = fields.Char(related="product_id.default_code", string="Item Code",store=True)
    brand_id = fields.Many2one(related="product_id.brand_id", string="Brand", store=True)
    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        digits='Product Price',
        store=True, readonly=False, required=True, precompute=True)
    product_uom_qty = fields.Float(string="Quantity")
    product_uom_id = fields.Many2one('uom.uom',string="Product UOM")
    rma_id = fields.Many2one('rma',string="RMA")
    move_id = fields.Many2one('stock.move',string="Stock Move")
    move_line_id = fields.Many2one('account.move.line', string="Account Move")
    return_reason_id = fields.Many2one(
        comodel_name="rma.return.reason",
        string="Return Reason",
        copy=False,
        tracking=True,
        required=True,
    )
    system_unit_price = fields.Float(
        related="product_id.lst_price",
        string="System Current Unit Price",
        store=True
    )
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        store=True, readonly=False,
        context={'active_test': False},
        check_company=True)
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
    )

    return_reason_type_id = fields.Many2one(related="return_reason_id.type", string="Type", store=True)

    return_caused_by = fields.Selection(
        selection=rma_return_caused_by,
        string="Return Caused By",
        copy=False,
        tracking=True,
    )
    return_caused_by_id = fields.Many2one(related='rma_id.return_caused_by_id', )
    total = fields.Monetary(
        string="Total",
        compute="_compute_total",
        store=True,
        currency_field='currency_id'
    )
    amount_tax = fields.Monetary(string="Vat Amount", compute="_compute_total", store=True, currency_field="currency_id")
    exercise_price = fields.Float(string="Exercise Tax", digits=(4, 4))
    product_packaging_price = fields.Float()

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='rma_id.currency_id',
        store=True,
        readonly=True
    )
    analytic_distribution = fields.Json()
    lot_ids = fields.Many2many('stock.lot',string="Lots Numbers",compute="compute_lot_ids",store=True)
    lot_number = fields.Char(string="Lot Number",store=True)
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', domain="[('purchase', '=', True), ('product_id', '=', product_id)]", check_company=True,
                                           compute="_compute_product_packaging_id", store=True, readonly=False)
    product_packaging_qty = fields.Float('Packaging Quantity', compute="_compute_product_packaging_qty", store=True, readonly=False)
    quant_package_id = fields.Many2one('stock.quant.package',string="Package")


    @api.onchange('product_packaging_qty')
    def onchange_product_packaging_qty(self):
        if self.product_packaging_id:
            packaging_uom = self.product_packaging_id.product_uom_id
            qty_per_packaging = self.product_packaging_id.qty
            product_qty = packaging_uom._compute_quantity(self.product_packaging_qty * qty_per_packaging, self.product_uom_id)
            if float_compare(product_qty, self.product_uom_qty, precision_rounding=self.product_uom_id.rounding) != 0:
                self.product_uom_qty = product_qty

    @api.depends('product_id', 'product_uom_qty', 'product_uom_id')
    def _compute_product_packaging_id(self):
        for line in self:
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False
            if line.product_id and line.product_uom_qty and line.product_uom_id and line.product_id.uom_id and line.product_uom_id == line.product_id.uom_id:
                suggested_packaging = line.product_id.packaging_ids\
                        .filtered(lambda p: p.purchase and (p.product_id.company_id <= p.company_id <= line.rma_id.company_id))\
                        ._find_suitable_product_packaging(line.product_uom_qty, line.product_uom_id)
                if not line.product_packaging_id:
                    line.product_packaging_id = suggested_packaging or line.product_packaging_id

    @api.depends('product_packaging_id', 'product_uom_id', 'product_uom_qty')
    def _compute_product_packaging_qty(self):
        self.product_packaging_qty = 0
        for line in self:
            if not line.product_packaging_id:
                continue
            line.product_packaging_qty = line.product_packaging_id._compute_qty(line.product_uom_qty, line.product_uom_id)


    @api.depends('rma_id.reception_move_ids.move_line_ids.lot_id',
                 'rma_id.reception_move_id.move_line_ids.lot_id',
                 'rma_id.reception_move_ids.state',
                 'rma_id.reception_move_id.state')
    def compute_lot_ids(self):
        for rec in self:
            lots = rec.rma_id.reception_move_ids.mapped('move_line_ids.lot_id') | rec.rma_id.reception_move_id.mapped('move_line_ids.lot_id')
            if lots:
                rec.lot_number = lots[0].display_name
            rec.lot_ids = lots.filtered(lambda l: l)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'currency_id')
    def _compute_total(self):
        for line in self:
            price_subtotal = (line.product_uom_qty * line.price_unit)
            if line.discount:
                price_subtotal = price_subtotal - (price_subtotal * (line.discount/100))
            taxes = line.tax_id.compute_all(
                price_subtotal,
                currency=line.currency_id,
                quantity=1.0,
                product=line.product_id,
                partner=None
            )
            total_tax = taxes['total_included'] - taxes['total_excluded']
            line.amount_tax = total_tax
            line.total = -1 * price_subtotal


    @api.depends('move_id')
    def _compute_price_unit(self):
        for line in self:
            line.price_unit = line.move_id.sale_line_id.price_unit if line.move_id and line.move_id.sale_line_id else 0.0

    @api.onchange('product_uom_qty')
    def onchange_product_uom_qty(self):
        if self.rma_id.rma_type in ['base_on_invoice']:
            if self.product_uom_qty > self.move_line_id.quantity:
                raise UserError("you can't set value more than order quantity")
        else:
            if self.product_uom_qty > self.move_id.quantity:
                raise UserError("you can't set value more than order quantity")
            if (self.product_uom_qty > self.move_id.remaining_qty) and self.move_id:
                raise UserError("RMA quantity can't be greater than move remaining quantity quantity")