from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare, float_is_zero
import logging
from collections import defaultdict

from odoo.tools.safe_eval import safe_eval
_logger = logging.getLogger(__name__)
import random

def _gen_reward_code(order_id=None):
    base = str(random.getrandbits(32))
    return f"cust-{order_id or '0'}-{base}"

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # in your SaleOrder model (same custom module)
    def _ensure_reward_codes(self):
        for order in self:
            bad = order.order_line.filtered(lambda l: l.reward_id and not l.reward_identifier_code)
            for ln in bad:
                ln.reward_identifier_code = f"cust-{order.id}-{random.getrandbits(32)}"

    def action_confirm(self):
        for order in self:
            order._ensure_reward_codes()
        return super(SaleOrder, self).action_confirm()


    def _get_program_domain(self):
        self.ensure_one()
        base_domain = super()._get_program_domain()
        customer = self.partner_id
        customer_group_domain = [
            '|',
            ('program_type', 'not in', ['buy_x_get_y', 'promotion']),
            '|',
            '&', ('program_type', 'in', ['buy_x_get_y', 'promotion']),
            ('promo_customer_group_id', '=', False),
            '&', ('program_type', 'in', ['buy_x_get_y', 'promotion']),
            ('promo_customer_group_id.partner_ids', 'in', [customer.id]),
        ]
        return base_domain + customer_group_domain

    # def _get_program_domain(self):
    #     self.ensure_one()
    #     today = fields.Date.context_today(self)
    #     base_domain = super()._get_program_domain()
    #     # Add filter for buy_x_get_y programs
    #     customer = self.partner_id
    #     customer_group_domain = [
    #         '|',
    #         ('program_type', 'not in', ['buy_x_get_y', 'promotion']),
    #         '&',
    #             ('program_type', 'in', ['buy_x_get_y', 'promotion']),
    #             ('promo_customer_group_id.partner_ids', 'in', [customer.id])
    #     ]
    #     return base_domain + customer_group_domain

    def action_open_reward_wizard(self):
        self.ensure_one()
        # refresh everything built‑in
        self._update_programs_and_rewards()

        # 1) grab core claimable (safely)
        try:
            claimable = self._get_claimable_rewards()
        except Exception as e:
            _logger.exception("⚠️ couldn’t get core claimable rewards, falling back to empty")
            claimable = {}

        # 2) merge in your custom slab/ladder/flat promos
        applied_progs = self.order_line.mapped('reward_id.program_id')
        dummy_card = self.env['loyalty.card']  # placeholder key
        for prog in self.env['loyalty.program'].search([
            ('program_type', 'in', ['ladder_promotion','slab_promotion','flat_discount']),
            ('active', '=', True),
        ]):
            if prog in applied_progs:
                continue

            reward = False
            if prog.program_type == 'ladder_promotion' and prog.is_ladder_applicable(self):
                distinct = len({
                    l.product_id for l in self.order_line
                    if l.product_id in prog.promo_product_group_id.product_ids
                })
                best = prog.ladder_rule_ids.filtered(
                    lambda r: r.distinct_item_count <= distinct
                ).sorted('distinct_item_count', reverse=True)[:1]
                if best:
                    reward = prog.update_ladder_reward_from_rule(best[0])

            elif prog.program_type == 'slab_promotion' and prog.is_slab_applicable(self):
                exercise_price = [(i.exercise_price * i.product_uom_qty) for i in self.order_line.filtered(
                    lambda l: l.product_id in prog.promo_product_group_id.product_ids)]
                total = sum(self.order_line
                                .filtered(lambda l: l.product_id in prog.promo_product_group_id.product_ids)
                                .mapped('price_subtotal')) - sum(exercise_price)
                best = prog.slab_rule_ids.filtered(
                    lambda r: total >= r.min_amount and total <= r.max_amount
                ).sorted('min_amount', reverse=True)[:1]
                if best:
                    reward = prog.update_slab_reward_from_rule(best[0])

            elif prog.program_type == 'flat_discount' and prog.is_flat_applicable(self):
                reward = prog.update_flat_reward()

            if reward:
                claimable.setdefault(dummy_card, self.env['loyalty.reward'])
                claimable[dummy_card] |= reward

        # 3) if nothing claimable, just exit
        if not claimable:
            return True

        # 4) auto‑apply single **core** reward (skip your custom ones)
        if len(claimable) == 1:
            coupon, rewards = next(iter(claimable.items()))
            if len(rewards) == 1 and not rewards.multi_product:
                single = rewards[0]
                if single.program_id.program_type not in (
                    'ladder_promotion','slab_promotion','flat_discount'
                ):
                    self._apply_program_reward(rewards, coupon)
                    return True

        action = self.env['ir.actions.actions']._for_xml_id('sale_loyalty.sale_loyalty_reward_wizard_action')
        ctx = action.get('context') or {}
        if isinstance(ctx, str):
            ctx = safe_eval(ctx)
        ctx.update({'loyalty_wizard': True})  # <<< add this
        action['context'] = ctx
        return action

        # 5) otherwise pop the wizard
        # return self.env['ir.actions.actions']._for_xml_id(
        #     'sale_loyalty.sale_loyalty_reward_wizard_action'
        # )

    sale_journal = fields.Many2one('account.journal')

    def _get_custom_programs(self):
        """Return all active slab/ladder/flat programs that could apply."""
        return self.env['loyalty.program'].search([
            ('program_type', 'in', ['ladder_promotion','slab_promotion','flat_discount']),
            ('active', '=', True),
        ])

    def apply_promotions(self, program=None):
        """
        Apply *only* the given program (if provided), otherwise all custom promotions.
        This replaces your old apply_promotions() which always did *every* promotion.
        """
        for order in self:
            partner = order.partner_id
            to_apply = program and program or order._get_custom_programs()

            for prog in to_apply:
                # Clean up any old discount line for this prog (by matching discount_line_product_id)
                old = order.order_line.filtered(lambda l: l.reward_id
                    and l.reward_id.program_id == prog
                    and l.product_id == prog.discount_line_product_id)
                if old:
                    old.unlink()
                order._cleanup_old_rewards(prog)

                # LADDER
                if prog.program_type == 'ladder_promotion' and prog.is_ladder_applicable(order):
                    # pick best rule
                    distinct = len({
                        l.product_id
                        for l in order.order_line
                        if l.product_id.id in prog.promo_product_group_id.product_ids.ids
                    })
                    best = prog.ladder_rule_ids.filtered(
                        lambda r: r.distinct_item_count <= distinct
                    ).sorted('distinct_item_count', reverse=True)[:1]
                    if best:
                        exercise_price = [(i.exercise_price * i.product_uom_qty) for i in self.order_line.filtered(
                            lambda l: l.product_id in prog.promo_product_group_id.product_ids)]
                        rule = best[0]
                        total = sum(order.order_line
                                        .filtered(lambda l: l.product_id.id in prog.promo_product_group_id.product_ids.ids)
                                        .mapped('price_subtotal')) - sum(exercise_price)
                        discount_amt = total * (rule.discount_percentage / 100.0)
                        reward = prog.update_ladder_reward_from_rule(rule)
                        if reward.reward_type != 'discount':
                            order._add_custom_discount_line(prog, discount_amt, reward.id)

                        lines = order.order_line.filtered(lambda l: l.product_id.id in prog.promo_product_group_id.product_ids.ids)
                        lines._apply_reward_discount(reward, prog, rule.discount_percentage, 'percent')

                        # applied_reward_ids = self.env['sale.order.line.reward'].with_context(active_test=False).search([
                        #     ('applied_reward_id', '=', reward.id),
                        #     ('sale_order_line_id.order_id', '=', order.id),  # <— add this
                        # ])
                        # applied_reward_ids.sudo().write({'active': True})
                        # applied_reward_ids = self.env['sale.order.line.reward'].with_context(active_test=False).search(
                        #     [('applied_reward_id', '=', reward.id)])
                        # applied_reward_ids.sudo().write({'active': True})

                # SLAB
                elif prog.program_type == 'slab_promotion' and prog.is_slab_applicable(order):
                    exercise_price = [(i.exercise_price * i.product_uom_qty) for i in self.order_line.filtered(
                        lambda l: l.product_id in prog.promo_product_group_id.product_ids)]
                    total = sum(order.order_line
                                    .filtered(lambda l: l.product_id.id in prog.promo_product_group_id.product_ids.ids)
                                    .mapped('price_subtotal')) - sum(exercise_price)
                    best = prog.slab_rule_ids.filtered(
                        lambda r: total >= r.min_amount and total <= r.max_amount
                    ).sorted('min_amount', reverse=True)[:1]
                    if best:
                        rule = best[0]
                        discount_amt = total * (rule.discount_percentage / 100.0)
                        reward = prog.update_slab_reward_from_rule(rule)
                        if reward.reward_type != 'discount':
                            order._add_custom_discount_line(prog, discount_amt, reward.id)

                        lines = order.order_line.filtered(lambda l: l.product_id.id in prog.promo_product_group_id.product_ids.ids)
                        lines._apply_reward_discount(reward, prog, rule.discount_percentage, 'percent')
                        # applied_reward_ids = self.env['sale.order.line.reward'].with_context(active_test=False).search([
                        #     ('applied_reward_id', '=', reward.id),
                        #     ('sale_order_line_id.order_id', '=', order.id),  # <— add this
                        # ])
                        # applied_reward_ids.sudo().write({'active': True})


                # FLAT
                elif prog.program_type == 'flat_discount' and prog.is_flat_applicable(order):
                    # filter lines exactly as before
                    lines = order.order_line
                    if prog.flat_discount_apply_options == 'division':
                        lines = lines.filtered(lambda l: l.product_id.division == prog.flat_division)
                    elif prog.flat_discount_apply_options == 'product_group':
                        gids = prog.promo_product_group_id.product_ids.ids
                        lines = lines.filtered(lambda l: l.product_id.id in gids)
                    elif prog.flat_discount_apply_options == 'products':
                        pids = prog.flat_product_ids.ids
                        lines = lines.filtered(lambda l: l.product_id.id in pids)

                    exercise_price = [(i.exercise_price * i.product_uom_qty) for i in lines]
                    total = sum(lines.mapped('price_subtotal')) - sum(exercise_price)
                    discount_amt = total * (prog.flat_discount_percentage / 100.0)
                    reward = prog.update_flat_reward()
                    if reward.reward_type != 'discount':
                        order._add_custom_discount_line(prog, discount_amt, reward.id)

                    lines._apply_reward_discount(reward, prog, prog.flat_discount_percentage, 'percent')
                    # applied_reward_ids = self.env['sale.order.line.reward'].with_context(active_test=False).search([
                    #     ('applied_reward_id', '=', reward.id),
                    #     ('sale_order_line_id.order_id', '=', order.id),  # <— add this
                    # ])
                    # applied_reward_ids.sudo().write({'active': True})

    def _apply_promotion_discount(self, reward):
        self.ensure_one()
        assert reward.reward_type == 'discount'

        reward_applies_on = reward.discount_applicability
        reward_program = reward.program_id
        reward_currency = reward.currency_id

        discountable = 0
        discountable_per_tax = defaultdict(int)
        if reward_applies_on == 'specific':
            discountable, discountable_per_tax = self._discountable_specific(reward)

        elif reward_applies_on == 'cheapest':
            discountable, discountable_per_tax = self._discountable_cheapest(reward)

        if not discountable:
            raise UserError(_('There is nothing to discount'))

        max_discount = reward_currency._convert(reward.discount_max_amount, self.currency_id, self.company_id, fields.Date.today()) or float('inf')
        # discount should never surpass the order's current total amount
        max_discount = min(self.amount_total, max_discount)
        if reward.discount_mode == 'percent':
            max_discount = min(max_discount, discountable * (reward.discount / 100))

        discount_factor = min(1, (max_discount / discountable)) if discountable else 1
        discount_percent = discount_factor * 100
        if reward_applies_on == 'specific':
            lines_to_discount = self._get_specific_discountable_lines(reward).filtered(
                        lambda line: bool(line.product_uom_qty and line.price_total)
                    )
            lines_to_discount._apply_reward_discount(reward, reward_program, discount_percent, 'percent')
        elif reward_applies_on == 'cheapest':
            cheapest_line = self._cheapest_line()
            cheapest_line._apply_reward_discount(reward, reward_program, discount_percent, 'percent')

    def _gen_reward_code(self):
        return f"cust-{self.id}-{random.getrandbits(32)}"

    def _add_custom_discount_line(self, program, amount, reward_id):
        self.env['sale.order.line'].create({
            'order_id': self.id,
            'product_id': program.discount_line_product_id.id,
            'name': _("Promo Discount (%s)") % program.name,
            'product_uom_qty': 1,
            'price_unit': -amount,
            'reward_id': reward_id,
            'reward_identifier_code': self._gen_reward_code(),  # <<< IMPORTANT
            'sequence': max(self.order_line.mapped('sequence'), default=0) + 1,
        })


    def _get_claimable_rewards(self):
        # 1) start with Odoo’s built‑in claimable rewards
        claimable = super()._get_claimable_rewards()  # returns {program: recordset}

        # To filter out any reward whose program is already used in sales order
        applied = self.order_line.mapped('reward_id.program_id') | self.order_line.sale_order_line_reward_ids.applied_reward_id.program_id
        # applied = self.order_line.sale_order_line_reward_ids.applied_reward_id.program_id

        excluded_program_types = {'ladder_promotion', 'slab_promotion', 'flat_discount'}
        # Remove rewards whose program's type is in custom program types (as we handle them separately)
        for key, reward in claimable.items():
            program = reward.program_id
            if program.program_type in excluded_program_types or (
                program.program_type in ['buy_x_get_y', 'promotion']
                and not program._is_customer_allowed(self)
            ):
                claimable[key] = self.env["loyalty.reward"]

            if not self.env.context.get('loyalty_wizard'):
                if (
                        program.program_type == "promotion"
                        and reward.reward_type == "discount"
                        and reward.discount_mode == "percent"
                        and not reward.is_global_discount
                        and reward.discount_applicability in ("cheapest", "specific")
                        and program in applied
                ):
                    claimable[key] = self.env["loyalty.reward"]

            # elif (
            #     program.program_type == "promotion"
            #     and reward.reward_type == "discount"
            #     and reward.discount_mode == "percent"
            #     and not reward.is_global_discount
            #     and reward.discount_applicability in ("cheapest", "specific")
            #     and program in applied
            # ):
            #     claimable[key] = self.env["loyalty.reward"]

        _logger.info("from sale order")
        _logger.info(claimable)

        # Applied reward program is not applicable as per customer group, so remove those lines
        # AFTER (no functional change for normal flows; wizard stays pure/read-only)
        if not self.env.context.get('loyalty_wizard'):
            to_remove_lines = self.order_line.filtered(
                lambda l: l.reward_id and l.reward_id.program_id.program_type in ['buy_x_get_y', 'promotion']
                          and not l.reward_id.program_id._is_customer_allowed(self)
            )
            to_remove_lines._reset_loyalty(complete=True)
            to_remove_lines.unlink()

        # to_remove_lines = self.order_line.filtered(
        #     lambda l: l.reward_id and l.reward_id.program_id.program_type in ['buy_x_get_y', 'promotion']
        #     and not l.reward_id.program_id._is_customer_allowed(self)
        # )
        # to_remove_lines._reset_loyalty(complete=True)
        # to_remove_lines.unlink()

        # 2) find your custom programs
        custom_domain = [
            ('program_type', 'in', ['ladder_promotion', 'slab_promotion', 'flat_discount']),
            ('active', '=', True)
        ]
        for program in self.env['loyalty.program'].search(custom_domain, order="id"):
            # skip if already applied on a line
            if program in applied:
                claimable[program] = claimable.get(program, self.env['loyalty.reward'])
                continue

            reward = False
            if program.program_type == 'ladder_promotion' and program.is_ladder_applicable(self):
                best = program.ladder_rule_ids.filtered(lambda r: r.distinct_item_count <= len(
                    set(self.order_line.filtered(lambda l: l.product_id in program.promo_product_group_id.product_ids).mapped('product_id'))
                )).sorted('distinct_item_count', reverse=True)[:1]
                if best:
                    reward = program.update_ladder_reward_from_rule(best[0])
            elif program.program_type == 'slab_promotion' and program.is_slab_applicable(self):
                # similar logic for slab...

                exercise_price = [(i.exercise_price * i.product_uom_qty) for i in self.order_line.filtered(lambda l: l.product_id in program.promo_product_group_id.product_ids)]
                rule = program.slab_rule_ids.filtered(lambda r: sum(self.order_line.filtered(
                    lambda l: l.product_id in program.promo_product_group_id.product_ids
                ).mapped('price_subtotal')) >= r.min_amount and
                    (sum(self.order_line.filtered(lambda l: l.product_id in program.promo_product_group_id.product_ids).mapped('price_subtotal')) - sum(exercise_price)) <= r.max_amount
                ).sorted('min_amount', reverse=True)[:1]
                if rule:
                    reward = program.update_slab_reward_from_rule(rule[0])
            elif program.program_type == 'flat_discount' and program.is_flat_applicable(self):
                reward = program.update_flat_reward()

            # 3) add it to the dict
            if reward:
                claimable[program] = claimable.get(program, self.env['loyalty.reward']) | reward
        if self.env.context.get('loyalty_wizard'):
            applied_rewards = (
                    self.order_line.mapped('reward_id') |
                    self.order_line.sale_order_line_reward_ids.mapped('applied_reward_id')
            )
            for key in list(claimable.keys()):
                remaining = claimable[key] - applied_rewards
                claimable[key] = remaining if remaining else self.env['loyalty.reward']

        return claimable

    def _cleanup_old_rewards(self, program):
        for order in self:
            old_rewards = order.order_line.sale_order_line_reward_ids.filtered(
                lambda r: r.applied_reward_id.program_id == program
            )
            if old_rewards:
                old_rewards.unlink()


class SaleOrderLineImportant(models.Model):
    _inherit = 'sale.order.line'

    test_discount = fields.Float(
        string='Test Discount(%)',
        digits='Discount',
        default=0.0,
        copy=False
    )
    test_discount_value = fields.Float(
        string='Test Discount',
        digits='Discount',
        default=0.0,
        copy=False
    )
    discount_unit_price = fields.Float("Disc Unit Price")
    original_total = fields.Float(compute='_compute_original_total', string="Original Total",store=True)
    sale_order_line_reward_ids = fields.One2many('sale.order.line.reward', 'sale_order_line_id', string="Applied Rewards", copy=False)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','discount_unit_price')
    def _compute_amount(self):
        super()._compute_amount()


    @api.depends('price_unit', 'product_uom_qty')
    def _compute_original_total(self):
        for line in self:
            line.original_total = line.price_unit * line.product_uom_qty

    def _apply_reward_discount(self, reward_id, program_id, discount_to_apply, discount_type='percent'):
        program_id = program_id or reward_id.program_id
        for line in self:
            currency = line.currency_id  # use line, not self
            # keep your running % fields
            line.test_discount = line.test_discount + discount_to_apply
            line.discount = line.discount + discount_to_apply

            excise_amount = (line.exercise_price or 0.0) * line.product_uom_qty

            # ✅ use the current effective unit price; no dependency on stale discount_amount
            effective_unit = line.discount_unit_price or line.price_unit
            base = (effective_unit * line.product_uom_qty) - excise_amount

            if discount_type == 'percent':
                applied_discount = currency.round(base * (discount_to_apply / 100.0))
                # keep your progressive effective price update
                line.discount_unit_price = effective_unit * (1 - (discount_to_apply / 100.0))
                name = f"{program_id.name} - {round(discount_to_apply, 2)}%"
                new_discount_value = line.test_discount_value + applied_discount
            else:
                applied_discount = currency.round(discount_to_apply)
                name = f"{program_id.name} - {round(discount_to_apply, 2)} {line.currency_id.name}"
                new_discount_value = line.test_discount_value + applied_discount

            line.test_discount_value = currency.round(new_discount_value)


            if not float_is_zero(applied_discount, precision_digits=2):
                self.env['sale.order.line.reward'].create({
                    'name': name,
                    'sale_order_line_id': line.id,
                    'applied_reward_id': reward_id.id,
                    'applied_discount': discount_to_apply,
                    'applied_discount_value': applied_discount,
                    'discount_type': discount_type,
                    'active': True,
                })

    @api.model
    def create(self, vals):
        if vals.get('reward_id') and not vals.get('reward_identifier_code'):
            vals['reward_identifier_code'] = _gen_reward_code(vals.get('order_id'))
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            if line.reward_id and not line.reward_identifier_code:
                line.reward_identifier_code = _gen_reward_code(line.order_id.id)
        return res

    def _reset_loyalty(self, complete=False):
        return super(SaleOrderLineImportant,self.filtered(lambda s: not s.is_reward_line))._reset_loyalty(complete)
