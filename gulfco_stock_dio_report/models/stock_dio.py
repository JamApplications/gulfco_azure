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
from odoo import api, fields, models, tools


class StockDioReport(models.Model):
    _name = "stock.dio.report"
    _description = "Stock DIO Report"
    _auto = False

    product_id = fields.Many2one('product.template', string='Product')
    default_code = fields.Char("Internal Reference")
    categ_id = fields.Many2one("product.category", "Product Category")
    brand_id = fields.Many2one("product.brand", "Brand")
    division = fields.Selection([('food','Food'),
                                         ('non_food','Non Food'),
                                         ('3pl','3PL'),
                                         ('local','Local'),
                                         ('posm','POSM'),
                                         ('mars','Mars')], "Product Division")
    standard_price = fields.Float("Cost")
    quantity = fields.Float("Quantity")
    inventory_value = fields.Float("Inventory Value")
    cogs = fields.Float("COGS")
    days = fields.Float("Days")
    dio_days = fields.Float("DIO Days")

    """
    def _init_report_view(self):
        tools.drop_view_if_exists(self._cr, 'stock_dio_report')
        self._cr.execute("""
    """
            CREATE OR REPLACE VIEW stock_dio_report AS (
                SELECT
                    pt.id AS id,                -- use product template
                    pt.id AS product_id,
                    pt.default_code,
                    pt.categ_id,
                    pt.brand_id,
                    pt.division,

                    -- stock on hand
                    SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty ELSE 0 END) AS quantity,

                    -- average unit cost (simple avg, not weighted)
                    AVG(CASE WHEN svl.remaining_qty > 0 THEN svl.unit_cost END) AS standard_price,

                    -- inventory value (weighted sum)
                    SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty * svl.unit_cost ELSE 0 END) AS inventory_value,

                    -- total COGS till today (positive)
                    ABS(SUM(CASE WHEN svl.quantity < 0 AND svl.create_date::date <= CURRENT_DATE THEN svl.value ELSE 0 END)) AS cogs,

                    -- days since year start
                    EXTRACT(DAY FROM CURRENT_DATE - DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '1 day') AS days,

                    -- DIO calculation
                    CASE 
                        WHEN SUM(CASE WHEN svl.quantity < 0 AND svl.create_date::date <= CURRENT_DATE THEN svl.value ELSE 0 END) = 0 
                        THEN NULL
                        ELSE 
                            ( SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty * svl.unit_cost ELSE 0 END)
                              / 
                              ( ABS(SUM(CASE WHEN svl.quantity < 0 AND svl.create_date::date <= CURRENT_DATE THEN svl.value ELSE 0 END))
                                / EXTRACT(DAY FROM CURRENT_DATE - DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '1 day')
                              )
                            )
                    END AS dio_days

                FROM stock_valuation_layer svl
                JOIN product_product pp ON svl.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                GROUP BY pt.id, pt.default_code, pt.brand_id, pt.division, pt.categ_id
            );
        """    """)
    
    def init(self):
        self._init_report_view()
    """