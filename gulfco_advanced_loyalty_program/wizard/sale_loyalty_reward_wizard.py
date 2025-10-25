from odoo import models, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)
class SaleLoyaltyRewardWizard(models.TransientModel):
    _inherit = 'sale.loyalty.reward.wizard'

    def action_apply(self):
        self.ensure_one()
        order = self.order_id
        reward = self.selected_reward_id
        if not reward:
            return super().action_apply()

        # --- Idempotency guard: if this reward is already applied, do nothing ---
        already = (
            order.order_line.mapped('reward_id')
            | order.order_line.sale_order_line_reward_ids.mapped('applied_reward_id')
        )
        if reward in already:
            return {'type': 'ir.actions.act_window_close'}

        # --- Custom types: apply once, then close (no super) ---
        if reward.program_id.program_type in ('ladder_promotion', 'slab_promotion', 'flat_discount'):
            order.apply_promotions(reward.program_id)
            return {'type': 'ir.actions.act_window_close'}

        # --- Core promotion (percent on cheapest/specific) you handle manually: apply then close ---
        if (
            reward.program_id.program_type == "promotion"
            and reward.reward_type == "discount"
            and reward.discount_mode == "percent"
            and not reward.is_global_discount
            and reward.discount_applicability in ("cheapest", "specific")
        ):
            claimable = order._get_claimable_rewards()
            selected_coupon = False
            for coupon, rewards in claimable.items():
                if reward in rewards:
                    selected_coupon = coupon
                    break
            if not selected_coupon:
                # keep the original validation semantics
                raise ValidationError(_('Coupon not found while trying to add the following reward: %s') % reward.description)

            order._apply_promotion_discount(reward)
            return {'type': 'ir.actions.act_window_close'}

        # --- Buy X Get Y: you create the link records yourself; then close (no super) ---
        if reward.program_id.program_type == 'buy_x_get_y':
            if reward.multi_product and not self.selected_product_id:
                candidates = reward.reward_product_ids & order.order_line.product_id
                self.selected_product_id = (candidates[:1] or reward.reward_product_ids[:1]).id

            res = super(SaleLoyaltyRewardWizard, self).action_apply()

            # (Optional) add a tracking row linked to the new reward lines
            gift_lines = order.order_line.filtered(lambda l: l.reward_id == reward)
            for gl in gift_lines:
                self.env['sale.order.line.reward'].create({
                    'name': reward.program_id.name,
                    'sale_order_line_id': gl.id,
                    'applied_reward_id': reward.id,
                    'applied_discount': 0.0,
                    'applied_discount_value': 0.0,
                    'active': True,
                })
            # return self._reopen_or_close()

            return res

        # if reward.program_id.program_type == 'buy_x_get_y':
        #     rules = reward.program_id.rule_ids
        #     so_products_per_rule = reward.program_id._get_valid_products(order.order_line.product_id)
        #     for rule in so_products_per_rule.keys():
        #         product = so_products_per_rule.get(rule)
        #         lines = order.order_line.filtered(lambda s: s.product_id == product and s.product_uom_qty >= reward.required_points)
        #         rule_amount = rule._compute_amount(order.currency_id)
        #         if rule_amount > 0.0:
        #             if rule.minimum_amount_tax_mode == 'incl':
        #                 lines = lines.filtered(lambda s: rule_amount <= s.price_total)
        #             else:
        #                 lines = lines.filtered(lambda s: rule_amount <= s.price_subtotal)
        #         for line in lines:
        #             self.env['sale.order.line.reward'].create({
        #                 'name': reward.program_id.name,
        #                 'sale_order_line_id': line.id,
        #                 'applied_reward_id': reward.id,
        #                 'applied_discount': 0.0,
        #                 'applied_discount_value': 0.0,
        #                 'active': True,
        #             })
        #     return {'type': 'ir.actions.act_window_close'}

        # Fallback to core only if we didn't handle it above
        return super().action_apply()

    @api.depends('order_id')
    def _compute_claimable_reward_ids(self):
        for wiz in self:
            order = wiz.order_id
            if not order:
                wiz.reward_ids = self.env['loyalty.reward']
                continue

            # 1) Grab Odoo’s built‑in claimable rewards (safe)
            try:
                core_claims = self.order_id._get_claimable_rewards()
            except Exception:
                _logger.exception("Could not fetch core claimable rewards, defaulting to none")
                core_claims = {}

            _logger.info("Core rewards")
            _logger.info(core_claims)
            rewards = self.env['loyalty.reward']
            for rw_set in core_claims.values():
                rewards |= rw_set

            # 2) Add one reward per custom promo
            # custom_progs = self.env['loyalty.program'].search([
            #     ('program_type', 'in', ['ladder_promotion','slab_promotion','flat_discount']),
            #     ('active', '=', True),
            #     # ('promo_customer_group_id.partner_ids', 'in', order_partner_id.ids),
            # ])
            # for prog in custom_progs:
            #     # skip if already applied on a line
            #     if prog in order.order_line.mapped('reward_id.program_id'):
            #         continue
            #     try:
            #         reward = False
            #         if prog.program_type == 'ladder_promotion' and prog.is_ladder_applicable(order):
            #             distinct = len({
            #                 l.product_id
            #                 for l in order.order_line
            #                 if l.product_id in prog.promo_product_group_id.product_ids
            #             })
            #             best = prog.ladder_rule_ids.filtered(
            #                 lambda r: r.distinct_item_count <= distinct
            #             ).sorted('distinct_item_count', reverse=True)[:1]
            #             if best:
            #                 reward = prog.update_ladder_reward_from_rule(best[0])
            #
            #         elif prog.program_type == 'slab_promotion' and prog.is_slab_applicable(order):
            #             total = sum(order.order_line
            #                             .filtered(lambda l: l.product_id in prog.promo_product_group_id.product_ids)
            #                             .mapped('price_subtotal'))
            #             best = prog.slab_rule_ids.filtered(
            #                 lambda r: total >= r.min_amount and total <= r.max_amount
            #             ).sorted('min_amount', reverse=True)[:1]
            #             if best:
            #                 reward = prog.update_slab_reward_from_rule(best[0])
            #
            #         elif prog.program_type == 'flat_discount' and prog.is_flat_applicable(order):
            #             reward = prog.update_flat_reward()
            #
            #         if reward:
            #             rewards |= reward
            #     except Exception:
            #         _logger.exception("Error computing reward for program %s", prog.id)

            # 3) Filter out any reward whose program was already used
            # applied = order.order_line.mapped('reward_id.program_id')
            # rewards = rewards.filtered(
            #     lambda r: r.program_id not in applied
            # )

            wiz.reward_ids = rewards
