# Copyright (c) 2019 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockRequestOrder(models.Model):
    _inherit = "stock.request.order"

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
            string="Request Type",
    )
    approved_by = fields.Many2one('res.users',string="Approved By")
    remarks = fields.Char(string="Remarks")
    vehicle_no = fields.Char(string="Vehicle No.")
    
    direction_account_id = fields.Many2one(
        "account.account",
        string="Default Account",
        compute="_compute_direction_account",
        store=True,
        domain="[('is_stock_control', '=', True)]"
    )
    journal_entry_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='stock_request_order_id',
        string='Journal Entries',
        copy=False,
    )
    journal_entry_count = fields.Integer(
        string="Journal Entries Count",
        compute="_compute_journal_entries_count"
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account", company_dependent=True
    )

    @api.depends('direction')
    def _compute_direction_account(self):
        mapping = {m.direction: m.account_id.id for m in self.env['stock.request.direction.account'].search([])}
        for rec in self:
            rec.direction_account_id = mapping.get(rec.direction, False)

    @api.onchange('direction')
    def set_virtual_location(self):
        if self.direction in ['miscellaneous_receiving']:
            self.location_id = self.env['stock.location'].browse(14).exists().id
            
    def _compute_journal_entries_count(self):
        for order in self:
            order.journal_entry_count = len(order.journal_entry_ids)

    def action_confirm(self):
        self.approved_by = self.env.user.id
        return super().action_confirm()
    
    def action_view_journal_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.journal_entry_ids.ids)],
        }


    @api.onchange('location_id','analytic_account_id','direction', 'destination_damage_id')
    def onchange_source_location_set_stock_request_lines(self):
        rec = self

        # for rec in self:
        if rec.direction in ['damage_expiry_issue_out','miscellaneous_issue_out'] and rec.location_id and rec.analytic_account_id and (rec.destination_id or rec.destination_damage_id):
            rec.stock_request_ids = [(5, 0, 0)]

            # Get all child locations except destination
            # locations = rec.location_id.with_context(active_test=False).search([
            #     ('id', 'child_of', rec.sudo().location_id.id)
            # ])
            locations = self.env['stock.location'].with_context(
                get_parents=True
            ).sudo().search([
                ('id', 'child_of', rec.location_id.id)
            ])

            locations = locations - rec.sudo().destination_id

            # Fetch eligible quants
            quants = self.env['stock.quant'].search([
                ('location_id', 'in', locations.ids),
                ('product_id.costing_dept_code_id','=',rec.analytic_account_id.id),
                ('quantity', '>', 0),
            ])

            product_lines = []
            for quant in quants:
                product = quant.product_id
                lot = quant.lot_id
                available_qty = quant.quantity - quant.reserved_quantity
                if available_qty > 0:
                    product_lines.append({
                        'product_id': product.id,
                        'product_uom_qty': available_qty,
                        'lot_id': lot.id,
                        'location_id': quant.location_id.id,
                        'source_location': quant.location_id.id,
                        'destination_location': rec.destination_id.id if rec.destination_id else rec.destination_damage_id.id,
                        'product_uom_id': product.uom_id.id,
                        'request_order_id': rec.id,
                        'package_id': quant.package_id,
                        'cost': product.standard_price,
                        'warehouse_id': rec.warehouse_id.id,
                        'direction_account_id': rec.direction_account_id.id or False
                    })
            if not product_lines:
                return {
                    'warning': {
                        'title': "No Stock Found",
                        'message': "No products found that are base on location and analytic account."
                    }
                }
            for line in product_lines:
                rec.stock_request_ids = [(0, 0, line)]

    @api.onchange("warehouse_id", "direction")
    def _onchange_location_id(self):
        # if self.direction == "outbound":
        #     # Stock Location set to Partner Locations/Customers
        #     self.location_id = self.company_id.partner_id.property_stock_customer.id
        # else:
        #     # Otherwise the Stock Location of the Warehouse
        #     self.location_id = self.warehouse_id.lot_stock_id.id
        for stock_request in self.stock_request_ids:
            if stock_request.route_id:
                stock_request.route_id = False

    def change_childs(self):
        res = super().change_childs()
        if not self._context.get("no_change_childs", False):
            for line in self.stock_request_ids:
                line.direction = self.direction
        return res
    
    def _generate_journal_entries(self):
        """Generate journal entries for the stock request order.
            CR / Inventory Valuation Account  (take it from product category)
            DR / Expense account take from line (stock.request).
        """
        AccountMove = self.env['account.move'].sudo()
        today = fields.Date.today()
        move_vals_list = []
        
        for rec in self:
            if rec.state != 'approved_done':
                continue
            
            partner = rec.customer_id
            
            for line in rec.stock_request_ids:
                if not line.product_id or not line.direction_account_id:
                    continue
                
                product = line.product_id
                categ_id = product.categ_id
                journal_id = categ_id.property_stock_journal or False
                valuation_account = categ_id.property_stock_valuation_account_id
                if not valuation_account:
                    raise UserError(_("No valuation account set for product category: %s") % categ_id.display_name)

                # Prepare journal entry values
                amount = line.product_uom_qty * product.standard_price
                move_vals_list.append({
                    'date': today,
                    'ref': f"{rec.name} - [{product.default_code}] {product.name}",
                    'partner_id': partner.id,
                    'journal_id': journal_id.id if journal_id else False,
                    'stock_request_order_id': rec.id,
                    'line_ids': [
                        (0, 0, {
                            'name': product.name,
                            'product_id': product.id,
                            'account_id': valuation_account.id,
                            'credit': amount,
                            'partner_id': partner.id,
                            'analytic_distribution': line.analytic_distribution,
                        }),
                        (0, 0, {
                            'name': product.name,
                            'product_id': product.id,
                            'account_id': line.direction_account_id.id,
                            'debit': amount,
                            'partner_id': partner.id,
                            'analytic_distribution': line.analytic_distribution,
                        }),
                    ],
                })
                
        journal_entries = AccountMove.create(move_vals_list)
        journal_entries.action_post()
        
    def action_approve(self):
        res = super(StockRequestOrder, self).action_approve()
        self.filtered(lambda r: r.state == 'approved_done')._generate_journal_entries()
        return res
