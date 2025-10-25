from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    production_date = fields.Date(string="Production Date")
    production_year = fields.Char(
        string="Production Year",
        compute="_compute_production_year",
        store=True
    )

    @api.depends('production_date')
    def _compute_production_year(self):
        for rec in self:
            rec.production_year = str(rec.production_date.year) if rec.production_date else False
