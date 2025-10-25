from odoo import api, fields, models, tools

class ExciseDeclaration(models.Model):
    _name = 'excise.declaration'
    _description = 'Excise Declaration Report'
    _auto = False

    sr = fields.Integer(string='Serial No')
    product_id = fields.Many2one('product.product', string='Description')
    gulfo_code = fields.Char(string='Gulfo Code')
    hs_code = fields.Char(string='HS Code')
    nestle_code = fields.Char(string='Nestle Code')
    packing = fields.Many2one('product.packaging', string='Packing')
    pallets = fields.Float(string='Pallets', default=0.0)
    conversion = fields.Float(string='Conversion', default=0.0)
    pallate_case = fields.Float(string='Pallet Case')
    qty_cs = fields.Float(string='Qty in CS', default=0.0)
    qty_pcs = fields.Float(string='Qty in PCS')
    barcode = fields.Char(string='Barcode')
    fta_price = fields.Float(string='FTA Price')
    fta_percentage = fields.Float(string='FTA Percentage')
    fta_total = fields.Float(string='FTA Total')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'excise_declaration')

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW excise_declaration AS (
                SELECT
                    row_number() OVER () AS id,
                     row_number() OVER (ORDER BY pol.id) AS sr,
                    pol.product_id,
                    pp.default_code AS gulfo_code,
                    pt.hs_code AS hs_code,
                    ps.product_code AS nestle_code,
                    pol.product_packaging_id AS packing,
                    0.0 AS pallets,
                    0.0 AS conversion,
                    pol.product_packaging_qty AS pallate_case,
                    0.0 AS qty_cs,
                    pol.product_qty AS qty_pcs,
                    pp.barcode AS barcode,
                    pt.exercise_price AS fta_price,
                    t.amount AS fta_percentage,
                    COALESCE(pt.exercise_price, 0) * pol.product_qty AS fta_total
                FROM purchase_order_line pol
                JOIN purchase_order po ON po.id = pol.order_id
                JOIN product_product pp ON pp.id = pol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pt.id AND ps.partner_id = po.partner_id
                LEFT JOIN account_tax t ON t.id = pt.exercise_tax_id
                WHERE pol.is_excise = TRUE
            )
        """)
