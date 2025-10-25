from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    gl_account_id = fields.Many2one(
        'account.account',
        string='Stock GL Account',
    )
    stock_analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Stock analytic account", company_dependent=True
    )

