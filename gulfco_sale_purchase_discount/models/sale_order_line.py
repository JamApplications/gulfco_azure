from odoo import models, fields, api, _
import logging
from odoo.tools import float_round, float_is_zero
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount_amount = fields.Monetary(compute='_compute_discount_amount', string='Discount Amount', store=True)
    original_total = fields.Float(compute='_compute_original_total', string="Original Total",store=True)

    effective_discount_pct = fields.Float(
        string='Effective Discount (%)',
        compute='_compute_effective_discount_pct',
        store=True,
        help="Manual discount stacked with reward discounts, converted to a single equivalent percentage."
    )
    @api.depends('price_unit', 'product_uom_qty')
    def _compute_original_total(self):
        for line in self:
            line.original_total = line.price_unit * line.product_uom_qty


    @api.depends(
        'discount',
        'sale_order_line_reward_ids',
        'reward_id',
    )
    def _compute_effective_discount_pct(self):
        def _clamp_pct(v):
            try:
                f = float(v or 0.0)
            except Exception:
                f = 0.0
            return max(0.0, min(100.0, f))

        def _pct_from_reward(rec):
            # Only percent-like rewards contribute
            for name in ('discount_percentage', 'discount', 'percent', 'percentage'):
                if hasattr(rec, name):
                    try:
                        return _clamp_pct(getattr(rec, name) or 0.0)
                    except Exception:
                        return 0.0
            return 0.0

        for line in self:
            # Reward lines themselves don’t carry discount math
            if getattr(line, 'reward_id', False):
                line.effective_discount_pct = 0.0
                continue

            # start factor at 1.00 and multiply by (1 - pct/100) for each step
            factor = 1.0

            # 1) manual discount first
            factor *= (1.0 - _clamp_pct(line.discount or 0.0) / 100.0)

            # 2) then rewards in sequence
            rewards = line.sale_order_line_reward_ids
            try:
                rewards = rewards.sorted(key=lambda r: (getattr(r, 'sequence', 9999), r.id))
            except Exception:
                pass

            for r in rewards:
                p = _pct_from_reward(r)
                if p > 0.0:
                    factor *= (1.0 - p / 100.0)

            # convert back to an equivalent single percentage
            # eff = 100 * (1 - factor)
            eff_pct = 100.0 * (1.0 - factor)
            # clamp for safety
            line.effective_discount_pct = max(0.0, min(100.0, eff_pct))

    @api.depends(
        'price_unit', 'product_uom_qty', 'discount',
        'original_total', 'discount_unit_price',
        'reward_id', 'order_id.currency_id',
        'price_subtotal', 'sale_order_line_reward_ids',
        'exercise_price',  # <-- important: include this
    )
    def _compute_discount_amount(self):
        def clamp_pct(v):
            try:
                return max(0.0, min(100.0, float(v or 0.0)))
            except Exception:
                return 0.0

        for line in self:
            # No discount on reward/FOC lines themselves
            if getattr(line, 'reward_id', False):
                line.discount_amount = 0.0
                continue

            qty = float(line.product_uom_qty or 0.0)

            # --- 1) pre-discount base ---
            if line.original_total:
                base = float(line.original_total)
            else:
                unit = line.discount_unit_price if line.discount_unit_price not in (None, False) else line.price_unit
                base = float(unit or 0.0) * qty

            if base <= 0.0:
                line.discount_amount = 0.0
                continue

            currency = (line.order_id and line.order_id.currency_id) or line.env.company.currency_id
            rounding = getattr(currency, 'rounding', 0.01) if currency else 0.01
            roundf = (lambda x: float_round(x, precision_rounding=rounding)) if currency else (
                lambda x: float(f"{x:.2f}"))

            # --- 2) prefer the delta implied by subtotal (ground truth), net of exercise_price ---
            exercise_total = float(line.exercise_price or 0.0) * qty
            subtotal_net = float(line.price_subtotal or 0.0) - exercise_total
            # guard: subtotal cannot exceed base; cannot be negative
            subtotal_net = max(0.0, min(base, subtotal_net))

            implied = roundf(max(0.0, min(base, base - subtotal_net)))

            # treat tiny values as zero in the current currency
            if not float_is_zero(implied, precision_rounding=rounding):
                line.discount_amount = implied
                continue

            # --- 3) FALLBACK: manual % + explicit rewards (sequential), no double counting ---
            manual_pct = clamp_pct(line.discount)
            manual_amt = base * (manual_pct / 100.0)
            after_manual = base - manual_amt

            abs_total = 0.0
            pct_list = []
            for rw in (line.sale_order_line_reward_ids or self.env['sale.order.line.reward']):
                val = getattr(rw, 'applied_discount_value', None)
                if val:
                    abs_total += float(val or 0.0)
                else:
                    p = clamp_pct(getattr(rw, 'applied_discount', 0.0))
                    if p > 0.0:
                        pct_list.append(p)

            if abs_total > 0.0:
                reward_amt = min(after_manual, abs_total)
            else:
                remaining = after_manual
                for p in pct_list:
                    remaining *= (1.0 - p / 100.0)  # sequential
                reward_amt = after_manual - remaining

            amount = manual_amt + reward_amt
            amount = roundf(max(0.0, min(base, amount)))
            line.discount_amount = amount