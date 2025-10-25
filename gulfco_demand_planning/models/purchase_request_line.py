from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    lrf_qty = fields.Float(
        string="LRF Qty",digits="Product Unit of Measure"
    )
    # vendor_id = fields.Many2one('res.partner',string="Vendor",compute="compute_vendor_id",store=True)
    supplier_code = fields.Char(string='Supplier Code',compute="compute_vendor_id",store=True,readonly=False)
    country_of_origin = fields.Many2one('res.country',string="Country of Origin")
    vendor_product_country_of_origin_ids = fields.Many2many('res.country',compute="compute_vendor_id")
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', domain="[('purchase', '=', True), ('product_id', '=', product_id)]", check_company=True,
                                           compute="_compute_product_packaging_id", store=True, readonly=False)
    product_packaging_qty = fields.Float('Packaging Quantity', compute="_compute_product_packaging_qty", store=True, readonly=False)
    purchased_qty = fields.Float(
        string="RFQ/PO Qty",
        digits="Product Unit of Measure",
        compute="_compute_purchased_qty",
        readonly=False,
        store=True
    )

    @api.depends('purchase_lines')
    def _compute_purchased_qty(self):
        for rec in self:
            if rec.purchased_qty:
                rec.purchased_qty = rec.purchased_qty
            else:
                rec.purchased_qty = 0.0
                for line in rec.purchase_lines.filtered(lambda x: x.state != "cancel"):
                    if rec.product_uom_id and line.product_uom != rec.product_uom_id:
                        rec.purchased_qty += line.product_uom._compute_quantity(
                            line.product_qty, rec.product_uom_id
                        )
                    else:
                        rec.purchased_qty += line.product_qty

    @api.onchange('purchased_qty')
    def onchange_purchase_qty(self):
        value = self.purchased_qty
        if round(value % 1, 2) != 0.00:
            raise ValidationError("Please Enter a whole number")

    # @api.constrains('purchased_qty')
    # def _check_final_order_qty(self):
    #     for record in self:
    #         if record.purchased_qty is not None and record.purchased_qty <= 0.0:
    #             raise ValidationError("Final Order Quantity must be a positive whole number.")
    #         elif record.purchased_qty > record.product_qty:
    #             raise ValidationError("Final Order Quantity must be a same or less than Order Quantity.")

    @api.depends('product_packaging_id', 'product_uom_id', 'purchased_qty')
    def _compute_product_packaging_qty(self):
        self.product_packaging_qty = 0
        for line in self:
            if not line.product_packaging_id:
                continue
            line.product_packaging_qty = line.product_packaging_id._compute_qty(line.purchased_qty, line.product_uom_id)
            line.product_qty = line.purchased_qty

    @api.depends('product_id', 'product_qty', 'product_uom_id')
    def _compute_product_packaging_id(self):
        for line in self:
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False
            if line.product_id and line.product_qty and line.product_uom_id:
                suggested_packaging = line.product_id.packaging_ids\
                        .filtered(lambda p: p.purchase and (p.product_id.company_id <= p.company_id <= line.company_id))\
                        ._find_suitable_product_packaging(line.product_qty, line.product_uom_id)
                line.product_packaging_id = suggested_packaging or line.product_packaging_id

    @api.depends('product_id','product_id.seller_ids','supplier_id')
    def compute_vendor_id(self):
        for record in self:
            if record.product_id and record.product_id.seller_ids:
                record.supplier_code = record.supplier_id.vendor_code
                if record.product_id.seller_ids.sorted(lambda s:s.sequence)[0].mapped('source_of_good_country_ids'):
                    record.vendor_product_country_of_origin_ids = record.product_id.seller_ids.sorted(lambda s:s.sequence)[0].mapped('source_of_good_country_ids').ids
                else:
                    record.vendor_product_country_of_origin_ids = []
            else:
                record.vendor_product_country_of_origin_ids = []
