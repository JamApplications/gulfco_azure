from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare

class PromoSlabRule(models.Model):
    _name = 'promo.slab.rule'
    _description = 'Promotion Slab Rule'
    _order = 'min_amount'

    promo_program_id = fields.Many2one(
        'loyalty.program',
        string="Program",
        required=True,
        ondelete='cascade'
    )
    min_amount = fields.Float(string="Min Invoice Value", required=True)
    max_amount = fields.Float(string="Max Invoice Value", required=True)
    discount_percentage = fields.Float(string="Discount %", required=True)

    @api.constrains('min_amount', 'max_amount', 'discount_percentage', 'promo_program_id')
    def _check_slab_rule_values(self):
        for rec in self:
            # only enforce when the program is a slab_promotion
            if rec.promo_program_id.program_type != 'slab_promotion':
                continue

            # 1️⃣ must be non‑negative
            if rec.min_amount < 0 or rec.max_amount < 0:
                raise ValidationError(_("Min and Max amounts must be zero or positive."))

            # 2️⃣ min < max
            if rec.min_amount >= rec.max_amount:
                raise ValidationError(_(
                    "Invalid slab: Min (%.2f) must be less than Max (%.2f)."
                ) % (rec.min_amount, rec.max_amount))

            # 3️⃣ no duplicate ranges
            siblings = rec.promo_program_id.slab_rule_ids.filtered(lambda r: r.id != rec.id)
            for sib in siblings:
                if (float_compare(sib.min_amount, rec.min_amount, precision_digits=2) == 0
                        and float_compare(sib.max_amount, rec.max_amount, precision_digits=2) == 0):
                    raise ValidationError(_(
                        "A slab with Min %.2f and Max %.2f already exists."
                    ) % (rec.min_amount, rec.max_amount))

            # 4️⃣ discount sanity (optional but 🔥)
            if not (0 < rec.discount_percentage <= 100):
                raise ValidationError(_(
                    "Discount %% must be > 0 and ≤ 100 (got %.2f)."
                ) % rec.discount_percentage)