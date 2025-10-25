from odoo import fields, models, api, _
from odoo.addons.purchase_stock.models.account_invoice import AccountMove
from odoo.tools import  float_is_zero
from odoo.tools.misc import groupby
import logging
_logger = logging.getLogger(__name__)
import time
# Global (per-worker) counters
_POST_CALLS = 0
_POST_TOTAL_MS = 0.0

class AccountMoveCustom(models.Model):
    _inherit = 'account.move'

    original_diff_move_ids = fields.Many2many('account.move','diff_account_move_rel','move_id','diff_move_id',string="Original Diff Moves")
    is_diff_entries = fields.Boolean()

    def open_price_diff_journal_entries(self):
        move_ids = self.env['account.move'].sudo().search([('original_diff_move_ids','in',self.ids)])
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'domain':[('id','in',move_ids.ids)],
            'view_mode': 'list,form',
        }



def _post(self, soft=True):
    """
    Instrumented version of your current function.
    All original logic preserved; only timing/logging added.
    """
    global _POST_CALLS, _POST_TOTAL_MS

    batch_size = len(self)
    ids_preview = self.ids[:10]  # avoid logging huge lists
    t0 = time.perf_counter()
    _logger.info("PERF account.move._post START | batch=%s soft=%s ids=%s", batch_size, soft, ids_preview)

    # =========================
    # ----- ORIGINAL BODY -----
    # =========================
    t_pd0 = time.perf_counter()
    if not self._context.get('move_reverse_cancel'):
        self.env['account.move.line'].create(self._stock_account_prepare_anglo_saxon_in_lines_vals())

    stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
    valued_lines = self.env['account.move.line'].sudo()
    valuation_invoices = self.env['account.move']
    for invoice in self:
        if invoice.sudo().stock_valuation_layer_ids:
            continue
        if invoice.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
            vl = invoice.invoice_line_ids.filtered(lambda l: l.product_id and l.product_id.cost_method != 'standard')
            valued_lines |= vl
            if vl:
                valuation_invoices += invoice

    if valued_lines:
        svls, _amls = valued_lines._apply_price_difference()
        stock_valuation_layers |= svls
    t_pd1 = time.perf_counter()

    # Super call
    t_sup0 = time.perf_counter()
    posted = super(AccountMove, self.with_context(skip_cogs_reconciliation=True))._post(soft)
    t_sup1 = time.perf_counter()

    # Set layer descriptions
    for layer in stock_valuation_layers:
        description = f"{layer.account_move_line_id.move_id.display_name} - {layer.product_id.display_name}"
        layer.description = description

    # Validate accounting entries from price diff
    t_val0 = time.perf_counter()
    if stock_valuation_layers:
        stock_valuation_layers.with_context(from_price_diff_move=valuation_invoices)._validate_accounting_entries()
    t_val1 = time.perf_counter()

    # Reconcile + flag diff entries
    t_rec0 = time.perf_counter()
    self._stock_account_anglo_saxon_reconcile_valuation()
    valuation_invoices.sudo().write({'is_diff_entries': True})
    t_rec1 = time.perf_counter()

    # =========================
    # ---- END ORIGINAL  ------
    # =========================

    # Final timing and counters
    dt_ms = (time.perf_counter() - t0) * 1000.0
    _POST_CALLS += 1
    _POST_TOTAL_MS += dt_ms
    avg_ms = _POST_TOTAL_MS / max(_POST_CALLS, 1)

    # Sub-steps in ms
    pd_ms = (t_pd1 - t_pd0) * 1000.0
    sup_ms = (t_sup1 - t_sup0) * 1000.0
    val_ms = (t_val1 - t_val0) * 1000.0
    rec_ms = (t_rec1 - t_rec0) * 1000.0

    _logger.info(
        "PERF account.move._post END   | took=%.2f ms (price_diff=%.2f, super_post=%.2f, validate=%.2f, reconcile=%.2f) "
        "| batch=%s | calls=%s | avg=%.2f ms",
        dt_ms, pd_ms, sup_ms, val_ms, rec_ms, batch_size, _POST_CALLS, avg_ms
    )

    return posted

AccountMove._post = _post