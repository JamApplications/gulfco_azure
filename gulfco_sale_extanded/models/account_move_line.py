from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        try:
            return super().action_post()
        except ValidationError:
            self.mapped('invoice_line_ids')._compute_analytic_distribution()
            return super().action_post()

    @api.depends('assign_to')
    def _compute_fiscal_position_id(self):
        super()._compute_fiscal_position_id()
        for move in self:
            assign_to_id = move.assign_to.state_id
            customer_fiscal_position_id = move.partner_id.property_account_position_id
            fiscal_position_id = self.env['account.fiscal.position'].search([('state_ids', 'in', assign_to_id.id)],
                                                                            limit=1)
            if fiscal_position_id and not customer_fiscal_position_id:
                move.fiscal_position_id = fiscal_position_id
            else:
                move.fiscal_position_id = customer_fiscal_position_id or False

    def _server_action_set_correct_fiscal_position(self):
        """Server action for Datafix of Invoices/Credit Note Fiscal Position and taxes.
            Model: account.move
            Action To Do: Execute Python Code
            First priority: Customer's configured Fiscal Position
            Second: Salesman(assign_to) Fiscal Position based on state
        """

        env = self.env
        for move in self:
            assign_to_state = move.assign_to.state_id if move.assign_to else False
            customer_fp = move.partner_id.property_account_position_id

            fiscal_position = False

            new_fp = False
            if customer_fp:
                new_fp = customer_fp
            elif assign_to_state and not customer_fp:
                fiscal_position = env['account.fiscal.position'].search(
                    [('state_ids', 'in', assign_to_state.id)],
                    limit=1
                )
                new_fp = fiscal_position or False

            if not new_fp or move.fiscal_position_id == new_fp:
                continue  # nothing to update

            old_fp = move.fiscal_position_id

            if move.state == 'draft':
                # Directly update draft moves
                move.fiscal_position_id = new_fp.id
                move.invoice_line_ids.with_context(update_fp_taxes=True)._compute_tax_ids()
                _logger.info(f"\nUpdated fiscal position in: '{move.name}'. Old: '{old_fp.name}' New: '{new_fp.name}'")

            elif move.state == 'posted':
                # For posted moves → Reset to draft → update → repost
                try:
                    matched_payments = False
                    if move.payment_state == 'paid':
                        matched_payments = move.matched_payment_ids
                    move.button_draft()
                    if move.fiscal_position_id != new_fp:
                        move.fiscal_position_id = new_fp.id
                        move.invoice_line_ids.with_context(update_fp_taxes=True)._compute_tax_ids()
                        _logger.info(
                            f"\nUpdated fiscal position in: '{move.name}'. Old: '{old_fp.name}' New: '{new_fp.name}'")
                    move.action_post()
                    if matched_payments:
                        invoice_lines = move.line_ids.filtered(
                            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
                        )
                        payment_lines = matched_payments.mapped('move_id.line_ids').filtered(
                            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
                        )

                        if invoice_lines and payment_lines:
                            (invoice_lines + payment_lines).reconcile()
                            _logger.info(
                                f"Re-applied reconciliation for invoice '{move.name}' "
                                f"with {len(matched_payments)} stored payment(s)."
                            )
                except Exception as e:
                    msg = f"Failed to re-post move {move.name}: {str(e)}"
                    _logger.error(msg)
                    raise UserError(msg)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    exercise_price = fields.Float(string="Exercise Tax", digits=(4, 4))
    product_packaging_id = fields.Many2one(
        comodel_name='product.packaging',
    )
    product_packaging_qty = fields.Float(
        string="Packaging Quantity",
    )
    product_packaging_price = fields.Float()

    expense_date = fields.Date(string="Expense Date")
    merchant_name = fields.Char(string="Merchant Name")
    merchant_document = fields.Char(string="Merchant Document")

    # @api.depends('account_id', 'partner_id', 'product_id','move_id.assign_to')
    # def _compute_analytic_distribution(self):
    #     super()._compute_analytic_distribution()
    #     if not self.env.context.get('create_bill'):
    #         for line in self:
    #             analytic_account_ids = self.env['account.analytic.account']
    #             if line.analytic_distribution:
    #                 for ids, percentage in line.analytic_distribution.items():
    #                     account_ids  = [int(i) for i in ids.split(',')]
    #                     analytic_account_ids += self.env['account.analytic.account'].browse(account_ids)
    #             if line.product_id and line.product_id.costing_dept_code_id:
    #                 analytic_account_ids += self.product_id.costing_dept_code_id
    #             if self.move_id.assign_to and self.move_id.assign_to.location_analytic_account_id:
    #                 analytic_account_ids += self.move_id.assign_to.location_analytic_account_id
    #             if analytic_account_ids:
    #                 # final_dist = dict(line.analytic_distribution or {})
    #                 # for acc_id in analytic_account_ids:
    #                 #     final_dist[acc_id.id] = 100.0
    #                 # line.analytic_distribution = final_dist
    #                 unique_ids = sorted(set(analytic_account_ids.ids))
    #                 line.analytic_distribution = {','.join(str(i) for i in unique_ids): 100}
    #                 # line.analytic_distribution = {','.join([str(i) for i in analytic_account_ids.ids]) : 100}

    @api.depends('account_id', 'partner_id', 'product_id', 'move_id.assign_to')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            analytic_account_ids = self.env['account.analytic.account']
            final_dist = dict(line.analytic_distribution or {})
            existing_account_sets = [set(map(int, k.split(','))) for k in final_dist.keys()]
            if line.product_id and line.product_id.costing_dept_code_id:
                analytic_account_ids |= line.product_id.costing_dept_code_id
            if line.move_id.assign_to and line.move_id.assign_to.location_analytic_account_id:
                analytic_account_ids |= line.move_id.assign_to.location_analytic_account_id
            if analytic_account_ids:
                for acc_id in analytic_account_ids.ids:
                    # Check if account already exists in any key set
                    if not any(acc_id in s for s in existing_account_sets):
                        # Add it into the first key (or make a new one with 0%)
                        first_key = next(iter(final_dist), None)
                        if first_key:
                            key_set = set(map(int, first_key.split(',')))
                            key_set.add(acc_id)
                            new_key = ','.join(str(i) for i in sorted(key_set))
                            final_dist[new_key] = final_dist.pop(first_key)
                        else:
                            # If no distribution exists, create new one with 100%
                            final_dist[str(acc_id)] = 100.0

            line.analytic_distribution = final_dist
