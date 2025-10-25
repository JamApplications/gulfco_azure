from odoo import models, fields,api, _
from odoo.exceptions import UserError

import logging
from odoo.tools.float_utils import float_round, float_is_zero
_logger = logging.getLogger("============API Authenticate========")

class AccountMove(models.Model):
    _inherit = 'account.move'

    # --- helper: version-safe totals/taxes recompute ---
    def _recompute_totals_version_safe(self):
        self.ensure_one()
        m = self.with_context(check_move_validity=False)
        # Mark taxes dirty if supported
        if hasattr(m.line_ids, '_onchange_mark_recompute_taxes'):
            try:
                m.line_ids._onchange_mark_recompute_taxes()
            except Exception:
                pass
        # Recompute tax lines if available
        if hasattr(m, '_recompute_tax_lines'):
            m._recompute_tax_lines()
        # Payment terms lines (receivable splits)
        if hasattr(m, '_recompute_payment_terms_lines'):
            m._recompute_payment_terms_lines()
        # Cash rounding lines
        if hasattr(m, '_recompute_cash_rounding_lines'):
            m._recompute_cash_rounding_lines()
        return m

    def _postprocess_foc_lines(self, foc_account_id=None):
        """
        1) Make FOC (free product) invoice lines not contribute to amount_total:
           - set price_unit=0, discount=0, tax_ids=[]
           - recompute taxes/terms/rounding via version-safe helper
        2) Post FOC cost in the ledger:
           - credit the FOC product line by its cost (company currency)
           - add a matching debit line to the FOC expense account
             (price/tax-neutral so it doesn't touch amount_total)
        3) Tiny penny-adjust on receivable if there's any ±0.01 drift.
        """
        for invoice in self:
            currency = invoice.company_currency_id or invoice.company_id.currency_id
            rounding = currency.rounding

            # only invoices created from SOs (as in your original guard)
            sale_orders = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')
            if not sale_orders:
                continue

            if not foc_account_id:
                raise UserError(_("FOC account is required."))

            # ------------------ 1) Normalize FOC product lines ------------------
            foc_product_lines = invoice.invoice_line_ids.filtered(
                lambda l: getattr(l, 'is_reward_line', False) and l.display_type == 'product'
            )
            if foc_product_lines:
                foc_product_lines.with_context(check_move_validity=False).sudo().write({
                    'price_unit': 0.0,
                    'discount': 0.0,
                    'tax_ids': [(5, 0, 0)],
                })
                # recompute using version-safe path (works w/out _recompute_dynamic_lines)
                invoice._recompute_totals_version_safe()

            # ------------------ 2) Receivable maturity (safe) ------------------
            receivable_line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable'
            )[:1]
            maturity_date = invoice.invoice_date_due or invoice.invoice_date or fields.Date.context_today(self)
            if receivable_line and not receivable_line.date_maturity:
                receivable_line.with_context(check_move_validity=False).write({'date_maturity': maturity_date})

            # ------------------ 3) Post FOC cost (ledger-only) ------------------
            new_foc_lines = []
            for line in foc_product_lines:
                qty = line.quantity or 0.0
                cost_value = float_round((line.product_id.standard_price or 0.0) * qty,
                                         precision_rounding=rounding)
                if float_is_zero(cost_value, precision_rounding=rounding):
                    continue

                # Credit the FOC product line (company currency). This does NOT affect amount_total.
                line.with_context(check_move_validity=False).sudo().write({
                    'credit': cost_value,
                    'debit': 0.0,
                })

                # Matching debit to FOC expense account (price/tax-neutral)
                new_foc_lines.append({
                    'name': _("FOC Adjustment: %s") % (line.product_id.display_name,),
                    'account_id': foc_account_id,
                    'debit': cost_value,
                    'credit': 0.0,
                    'price_unit': 0.0,  # keep totals neutral
                    'quantity': 0.0,
                    'tax_ids': [(5, 0, 0)],
                    # keep it as a real accounting line
                    'display_type': 'foc',  # (or False if your schema allows)
                    # optional tag (add Boolean field on account.move.line if you want):
                    # 'is_foc_line': True,
                    'analytic_distribution': line.analytic_distribution,
                    'move_id': invoice.id,
                    'date_maturity': maturity_date,
                })

            if new_foc_lines:
                self.env['account.move.line'].with_context(check_move_validity=False).sudo().create(new_foc_lines)

            # ------------------ 4) Tiny drift absorber on receivable ------------------
            if receivable_line:
                debit_total = sum(invoice.line_ids.mapped('debit'))
                credit_total = sum(invoice.line_ids.mapped('credit'))
                diff = float_round(debit_total - credit_total, precision_rounding=rounding)
                if not float_is_zero(diff, precision_rounding=rounding):
                    new_debit = float_round(receivable_line.debit - diff, precision_rounding=rounding)
                    if new_debit >= 0:
                        receivable_line.with_context(check_move_validity=False).sudo().write({'debit': new_debit})
                    else:
                        receivable_line.with_context(check_move_validity=False).sudo().write({
                            'debit': 0.0,
                            'credit': float_round(receivable_line.credit + (-new_debit),
                                                  precision_rounding=rounding),
                        })

            # ------------------ 5) Final hard check ------------------
            debit_total = sum(invoice.line_ids.mapped('debit'))
            credit_total = sum(invoice.line_ids.mapped('credit'))
            if round(debit_total - credit_total, 2) != 0.0:
                raise UserError(_(
                    "Invoice %s still unbalanced after FOC processing! Debit=%s, Credit=%s"
                ) % (invoice.name, debit_total, credit_total))

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'state')
    def _compute_amount(self):
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding', 'foc'):
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_untaxed_in_currency_signed = -total_untaxed_currency
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_reward_line = fields.Boolean(related='sale_line_ids.is_reward_line', store=True)
    display_type = fields.Selection(selection_add=[("foc","FOC")],ondelete={'foc': 'cascade'})

