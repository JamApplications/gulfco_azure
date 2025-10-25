from odoo import models, fields, api, _

class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    wh_manager = fields.Many2many(
        'res.users',
        string="WH Manager",
        help="The employee responsible for this warehouse",
        widget='many2many_checkboxes',
    )

class StockLocation(models.Model):
    _inherit = 'stock.location'

    responsible_id = fields.Many2many(
        'res.users',
        string="Responsible",
        # widget='many2many_checkboxes',
    )

    stock_keeper_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_stock_keeper_users',
        store=False,
    )

    @api.depends()
    def _compute_stock_keeper_users(self):
        group = self.env.ref('stock_request.stock_group_stock_keeper')
        users = group.users
        for rec in self:
            rec.stock_keeper_user_ids = users

