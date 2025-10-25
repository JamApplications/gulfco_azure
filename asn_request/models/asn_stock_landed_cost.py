from odoo import _, api, fields, models

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]

class CustomStockLandedCost(models.Model):
    _name = "asn.stock.landed.cost"

    name = fields.Char("Description")
    asn_request_id = fields.Many2one('asn.request',string="ASN Request")
    product_id = fields.Many2one('product.product', 'Product', required=True,domain="[('type', '=', 'service')]")
    price_unit = fields.Monetary('Cost', required=True)
    split_method = fields.Selection(
                                    SPLIT_METHOD,
                                    string='Split Method',
                                    required=True,
                                    help="Equal: Cost will be equally divided.\n"
                                    "By Quantity: Cost will be divided according to product's quantity.\n"
                                    "By Current cost: Cost will be divided according to product's current cost.\n"
                                    "By Weight: Cost will be divided depending on its weight.\n"
                                    "By Volume: Cost will be divided depending on its volume.")
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])
    currency_id = fields.Many2one('res.currency')
    picking_id = fields.Many2one('stock.picking',string="GRN")
    partner_id = fields.Many2one('res.partner',string="Vendor")
    asn_picking_ids = fields.Many2many('stock.picking',string="Asn Pickings",compute="compute_asn_picking_ids")
    stock_landed_cost_id = fields.Many2one('stock.landed.cost',string="Stock Landed Cost")

    @api.depends_context('from_asn_landed_cost')
    @api.depends('asn_request_id','asn_request_id.picking_ids')
    def compute_asn_picking_ids(self):
        for record in self:
            if record.asn_request_id and record.asn_request_id.picking_ids:
                record.asn_picking_ids = record.asn_request_id.picking_ids
            else:
                record.asn_picking_ids = []

    @api.onchange('product_id')
    def _onchange_set_product_landed_cost(self):
        for rec in self:
            if rec.product_id and rec.product_id.landed_cost_ok:
                rec.product_id = rec.product_id
                rec.name = rec.product_id.name
                rec.account_id = rec.product_id.property_account_expense_id
                rec.split_method = rec.product_id.split_method_landed_cost