from odoo import models, fields, api

class StockDioWizard(models.TransientModel):
    _name = 'stock.dio.wizard'
    _description = 'Stock DIO Report Wizard'

    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)
    product_id = fields.Many2one('product.product', string="Product")
    categ_id = fields.Many2one('product.category', string="Product Category")
    brand_id = fields.Many2one('product.brand', string="Product Brand")
    product_type = fields.Selection([('REGULAR','REGULAR'),
                                     ('FOC','FOC'),
                                     ('PROMOTION','PROMOTION'),], "Type")

    def run_dio_report(self):
        # Ensure this is an instance method (self)
        date_from = self.date_from
        date_to = self.date_to

        # Build dynamic SQL filters
        product_filter = f"AND svl.product_id = {self.product_id.id}" if self.product_id else ""
        category_filter = f"AND pt.categ_id = {self.categ_id.id}" if self.categ_id else ""
        brand_filter = f"AND pt.brand_id = {self.brand_id.id}" if self.brand_id else ""
        type_filter = f"AND pt.x_studio_promotionregular = {self.product_type}" if self.product_type else ""

        query = f"""
        CREATE OR REPLACE VIEW stock_dio_report AS (
            SELECT
                pt.id AS id,
                pt.id AS product_id,
                pt.default_code,
                pt.categ_id,
                pt.brand_id,
                pt.division,
                SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty ELSE 0 END) AS quantity,
                AVG(CASE WHEN svl.remaining_qty > 0 THEN svl.unit_cost END) AS standard_price,
                SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty * svl.unit_cost ELSE 0 END) AS inventory_value,
                ABS(SUM(CASE WHEN svl.quantity < 0 
                             AND svl.create_date::date >= '{date_from}' 
                             AND svl.create_date::date <= '{date_to}' 
                        THEN svl.value ELSE 0 END)) AS cogs,
                (DATE '{date_to}' - DATE '{date_from}') + 1 AS days,
                CASE 
                    WHEN SUM(CASE WHEN svl.quantity < 0 
                                  AND svl.create_date::date >= '{date_from}' 
                                  AND svl.create_date::date <= '{date_to}' 
                             THEN svl.value ELSE 0 END) = 0 
                    THEN NULL
                    ELSE SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty * svl.unit_cost ELSE 0 END)
                         / (ABS(SUM(CASE WHEN svl.quantity < 0 
                                          AND svl.create_date::date >= '{date_from}' 
                                          AND svl.create_date::date <= '{date_to}' 
                                     THEN svl.value ELSE 0 END))
                            / ((DATE '{date_to}' - DATE '{date_from}') + 1)
                           )
                END AS dio_days
            FROM stock_valuation_layer svl
            JOIN product_product pp ON svl.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE 1=1
                    {product_filter}
                    {category_filter}
                    {brand_filter}
                    {type_filter}
            GROUP BY pt.id, pt.default_code, pt.brand_id, pt.division, pt.categ_id
        );
        """
        self.env.cr.execute(query)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock DIO Report',
            'res_model': 'stock.dio.report',  # make sure this model exists
            'view_mode': 'list',
            'target': 'current',
        }
