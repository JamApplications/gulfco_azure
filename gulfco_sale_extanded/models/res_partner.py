from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL, unique


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # @api.depends_context('company')
    # def _credit_debit_get(self):
    #     ''' Overrode the base method to count only debit values on teh credit field'''
    #     if not self.ids:
    #         self.debit = False
    #         self.credit = False
    #         return
    #
    #     query = self.env['account.move.line']._where_calc([
    #         ('parent_state', '=', 'posted'),
    #         ('company_id', 'child_of', self.env.company.root_id.id)
    #     ])
    #     self.env['account.move.line'].flush_model(
    #         ['account_id', 'debit', 'credit', 'amount_residual', 'company_id', 'parent_state', 'partner_id',
    #          'reconciled']
    #     )
    #     self.env['account.account'].flush_model(['account_type'])
    #
    #     sql = SQL("""
    #         SELECT account_move_line.partner_id, a.account_type,
    #                SUM(
    #                    CASE
    #                        WHEN a.account_type = 'asset_receivable' AND account_move_line.debit > 0 THEN account_move_line.amount_residual
    #                        WHEN a.account_type = 'liability_payable' AND account_move_line.credit > 0 THEN account_move_line.amount_residual
    #                        ELSE 0
    #                    END
    #                ) AS total
    #         FROM %s
    #         LEFT JOIN account_account a ON (account_move_line.account_id = a.id)
    #         WHERE a.account_type IN ('asset_receivable','liability_payable')
    #           AND account_move_line.partner_id IN %s
    #           AND account_move_line.reconciled IS NOT TRUE
    #           AND %s
    #         GROUP BY account_move_line.partner_id, a.account_type
    #     """, query.from_clause, tuple(self.ids), query.where_clause or SQL("TRUE"))
    #
    #     treated = self.browse()
    #     for pid, account_type, val in self.env.execute_query(sql):
    #         partner = self.browse(pid)
    #         if account_type == 'asset_receivable':
    #             partner.credit = val
    #             if partner not in treated:
    #                 partner.debit = False
    #                 treated |= partner
    #         elif account_type == 'liability_payable':
    #             partner.debit = -val
    #             if partner not in treated:
    #                 partner.credit = False
    #                 treated |= partner
    #
    #     remaining = self - treated
    #     remaining.debit = False
    #     remaining.credit = False

    location = fields.Char(string="Location")
    site_number = fields.Char('Site Number')
    specification = fields.Many2one('customer.specification',string='Specification')
    total_sales_order_count = fields.Integer(
        string="SO approved not invoiced",
        compute="_compute_total_sales_order_count"
    )
    credit_remaining = fields.Float('Credit Remaining',    compute="_compute_total_sales_order_count")

    @api.depends('sale_order_ids')
    def _compute_total_sales_order_count(self):
        for partner in self:
            # Filter out invoiced or cancelled orders
            filtered_orders = partner.sale_order_ids.filtered(
                lambda o: o.state in ('approved', 'sale') and not o.invoice_ids
            )
            partner.total_sales_order_count = sum(filtered_orders.mapped('amount_total'))
            credit_remaining = 0
            if partner.use_partner_credit_limit:
                credit_remaining = (partner.credit_limit - partner.credit - partner.total_sales_order_count) or 0
            partner.credit_remaining = credit_remaining

