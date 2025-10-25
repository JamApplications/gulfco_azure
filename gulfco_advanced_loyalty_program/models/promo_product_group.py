from odoo import models, fields,api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_round

class PromoProductGroup(models.Model):
    _name = 'promo.product.group'
    _description = 'Promotion Product Group'

    name = fields.Char(required=True)
    product_ids = fields.Many2many(
        'product.product', string="Products",
        domain=[('sale_ok', '=', True), ('type', '=', 'consu'), ('active','=', True)]
    )

class PromoCustomerGroup(models.Model):
    _name = 'promo.customer.group'
    _description = 'Promotion Customer Group'

    name = fields.Char(required=True)
    partner_ids = fields.Many2many('res.partner', string="Customers", domain=[('contact_type','in', ['customer','both']), ('active','=',True)])

class PromoLadderRule(models.Model):
    _name = 'promo.ladder.rule'
    _description = 'Promotion Ladder Rule'

    promo_program_id = fields.Many2one('loyalty.program', string="Promotion Program", required=True)
    distinct_item_count = fields.Integer(string="Distinct Items", required=True)
    discount_percentage = fields.Float(string="Discount %", required=True)
    reward_id = fields.Many2one('loyalty.reward')


    @api.constrains('distinct_item_count', 'discount_percentage', 'promo_program_id')
    def _check_ladder_rule_values(self):
        for rec in self:
            # only when it’s a ladder promotion
            if rec.promo_program_id.program_type != 'ladder_promotion':
                continue

            # 1️⃣ must buy at least one distinct item
            if rec.distinct_item_count <= 0:
                raise ValidationError(_("You must require at least one distinct item (got %s).")
                                      % rec.distinct_item_count)

            # 2️⃣ sane discount percentage: between 0 (exclusive) and 100 (inclusive)
            pct = float_round(rec.discount_percentage, precision_digits=2)
            if pct <= 0 or pct > 100:
                raise ValidationError(_("Discount %% must be > 0 and ≤ 100 (got %s).") % rec.discount_percentage)

            # 3️⃣ no duplicate “buy X items” in the same program
            domain = [
                ('promo_program_id', '=', rec.promo_program_id.id),
                ('distinct_item_count', '=', rec.distinct_item_count),
            ]
            if rec.id:
                domain.append(('id', '!=', rec.id))
            if self.search_count(domain):
                raise ValidationError(_(
                    "A ladder rule for buying %s distinct items already exists."
                ) % rec.distinct_item_count)