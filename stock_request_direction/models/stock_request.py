# Copyright (c) 2019 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class StockRequest(models.Model):
    _inherit = "stock.request"
        
    direction = fields.Selection(
        [   ('internal_transfer', 'Internal Transfer'),
            ('branch_transfer', 'Branch Transfer'),
            ('sample_issue_out', 'Sample Issue Out'),
            ('damage_expiry_issue_out', 'Damage & Expiry Issue Out'),
            ('miscellaneous_issue_out', 'Miscellaneous Issue Out'),
            ('foc_receiving', 'FOC Receiving'),
            ('miscellaneous_receiving', 'Miscellaneous Receiving'),
            ('consumable_issuance', 'Consumable Issuance'),
            ('scrap_issuance', 'Scrap Issuance'),
            ('van_load', 'Van Load'),
            ('van_off_load', 'Van Off Load'),
            ('stock_takeover', 'Stock Takeover')],
    )
    remarks = fields.Char(string="Remarks")
    
    direction_account_id = fields.Many2one(
        "account.account",
        string="Default Account",
        domain="[('is_stock_control', '=', True)]"
    )
    analytic_distribution = fields.Json("Analytic Distribution",compute="_compute_analytic_distribution", store=True, copy=True)
    analytic_precision = fields.Integer(string="Analytic Precision", default=2)
    order_state = fields.Selection(related="order_id.state", string="Order State")

    @api.depends('warehouse_id','product_id')
    def _compute_analytic_distribution(self):
        for line in self:
            analytic_distribution = {}
            analytic_account_ids = self.env['account.analytic.account']
            if line.product_id and line.product_id.costing_dept_code_id:
                analytic_account_ids |= line.product_id.costing_dept_code_id
            if line.warehouse_id and line.warehouse_id.stock_analytic_account_id:
                analytic_account_ids |= line.warehouse_id.stock_analytic_account_id
            channel_plan = self.env['account.analytic.plan'].sudo().search([('is_channel_plan', '=', True)],
                                                                           limit=1)
            channel_accounts = channel_plan.account_ids.filtered('is_channel_common') if channel_plan else self.env[
                'account.analytic.account']
            if channel_accounts:
                analytic_account_ids |= channel_accounts[0]
            if analytic_account_ids:
                unique_ids = sorted(set(analytic_account_ids.ids))
                analytic_distribution = {','.join(str(i) for i in unique_ids): 100}
            line.analytic_distribution = analytic_distribution
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("order_id") and not vals.get("direction_account_id"):
                order = self.env["stock.request.order"].browse(int(vals["order_id"]))
                if order.direction_account_id:
                    vals["direction_account_id"] = order.direction_account_id.id
            if vals.get('product_id') and not vals.get("analytic_distribution"):
                # Set Department automatically from product's Costing Dept Code
                product_analytic_account_ids = self.env['product.product'].sudo().browse(int(vals.get('product_id'))).costing_dept_code_id
                if product_analytic_account_ids:
                    vals['analytic_distribution'] = {str(account_id) : 100 for account_id in product_analytic_account_ids.ids}
        return super(StockRequest, self).create(vals_list)

    @api.onchange("direction")
    def _onchange_location_id(self):
        if not self._context.get("default_location_id"):
            # if self.direction == "outbound":
            #     # Stock Location set to Partner Locations/Customers
            #     self.location_id = self.company_id.partner_id.property_stock_customer.id
            # else:
                # Otherwise the Stock Location of the Warehouse
            self.location_id = self.warehouse_id.lot_stock_id.id
        
        if self.order_id:
            self.direction_account_id = self.order_id.direction_account_id
