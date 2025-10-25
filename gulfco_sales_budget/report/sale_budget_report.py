from odoo import api, fields, models, tools, _
from datetime import date

class SaleBudgetReport(models.Model):
    _name = "sale.budget.report"
    _description = 'Sale Budget Report'
    _auto = False
    _order = False

    @api.model
    def _group_expand_sale_budget_month(self, sale_budget_month, domain):
        return ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']

    sale_budget_month = fields.Selection(
        [('01', 'Jan'), ('02', 'Feb'), ('03', 'March'), ('04', 'April'), ('05', 'May'), ('06', 'June'),
         ('07', 'July'), ('08', 'Aug'), ('09', 'Sep'), ('10', 'Oct'), ('11', 'Nov'), ('12', 'Dec')],string="Month",group_expand='_group_expand_sale_budget_month')

    sales_volume = fields.Float(string="Sales Volume",default=0.0)
    sales_value = fields.Float(string="Sales Value",default=0.0)
    cogs = fields.Float(string="Cogs",default=0.0)
    margin = fields.Float(string="Margin",default=0.0)
    gp = fields.Float(string="GP(%)",default=0.0)
    sales_budget_line_id = fields.Many2one('sales.budget.line',string="Budget line")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    product_id = fields.Many2one('product.product',string="Product")


    def _get_default_start_date(self):
        # Get the first day of the current year
        current_year = date.today().year
        return f'{current_year}-01-01'

    def _get_default_end_date(self):
        # Get the last day of the current year
        current_year = date.today().year
        return f'{current_year}-12-31'

    month_start_date = fields.Date(string='Start Date',  required=False)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self.env.cr.execute("""CREATE OR REPLACE VIEW %s AS
        SELECT
        row_number() OVER () AS id,
        *
FROM (
SELECT '01' AS sale_budget_month,
        CASE WHEN jan_sales_volume is not null THEN jan_sales_volume ELSE 0.00 END AS sales_volume,
        jan_sales_value AS sales_value,
        product_id AS product_id,
        jan_cogs AS cogs, jan_gross_margin AS margin, jan_gp AS gp,
        id AS sales_budget_line_id,
        to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '02' AS sale_budget_month,
       CASE WHEN feb_sales_volume is not null THEN feb_sales_volume ELSE 0.00 END AS sales_volume , feb_sales_value AS sales_value,
       product_id AS product_id,
       feb_cogs AS cogs, feb_gross_margin AS margin, feb_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '03' AS sale_budget_month,
       CASE WHEN march_sales_volume is not null THEN march_sales_volume ELSE 0.00 END AS sales_volume,
       march_sales_value AS sales_value,
       product_id AS product_id,
       march_cogs AS cogs, march_gross_margin AS margin, march_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '04' AS sale_budget_month,
       CASE WHEN april_sales_volume is not null THEN april_sales_volume ELSE 0.00 END AS sales_volume,
       april_sales_value AS sales_value,
       product_id AS product_id,
       april_cogs AS cogs, april_gross_margin AS margin, april_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '05' AS sale_budget_month,
       CASE WHEN may_sales_volume is not null THEN may_sales_volume ELSE 0.00 END AS sales_volume,
       may_sales_value AS sales_value,
       product_id AS product_id,
       may_cogs AS cogs, may_gross_margin AS margin, may_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '06' AS sale_budget_month,
       CASE WHEN june_sales_volume is not null THEN june_sales_volume ELSE 0.00 END AS sales_volume,
       june_sales_value AS sales_value,
       product_id AS product_id,
       june_cogs AS cogs, june_gross_margin AS margin, june_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '07' AS sale_budget_month,
       CASE WHEN july_sales_volume is not null THEN july_sales_volume ELSE 0.00 END AS sales_volume,
       july_sales_value AS sales_value,
       product_id AS product_id,
       july_cogs AS cogs, july_gross_margin AS margin, july_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '08' AS sale_budget_month,
       CASE WHEN aug_sales_volume is not null THEN aug_sales_volume ELSE 0.00 END AS sales_volume,
       aug_sales_value AS sales_value,
       product_id AS product_id,
       aug_cogs AS cogs, aug_gross_margin AS margin, aug_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '09' AS sale_budget_month,
       CASE WHEN sep_sales_volume is not null THEN sep_sales_volume ELSE 0.00 END AS sales_volume,
       sep_sales_value AS sales_value,
       product_id AS product_id,
       sep_cogs AS cogs, sep_gross_margin AS margin, sep_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '10' AS sale_budget_month,
       CASE WHEN oct_sales_volume is not null THEN oct_sales_volume ELSE 0.00 END AS sales_volume,
       oct_sales_value AS sales_value,
       product_id AS product_id,
       oct_cogs AS cogs, oct_gross_margin AS margin, oct_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '11' AS sale_budget_month,
       CASE WHEN nov_sales_volume is not null THEN nov_sales_volume ELSE 0.00 END AS sales_volume,
       nov_sales_value AS sales_value,
       product_id AS product_id,
       nov_cogs AS cogs, nov_gross_margin AS margin, nov_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
UNION ALL
SELECT '12' AS sale_budget_month,
       CASE WHEN dec_sales_volume is not null THEN dec_sales_volume ELSE 0.00 END AS sales_volume,
       dec_sales_value AS sales_value,
       product_id AS product_id,
       dec_cogs AS cogs, dec_gross_margin AS margin, dec_gp AS gp,
       id AS sales_budget_line_id,
       to_date(EXTRACT(YEAR FROM CURRENT_DATE)::text || '-01-01', 'YYYY-MM-DD') AS month_start_date
FROM sales_budget_line
) AS combined""" % (self._table))
