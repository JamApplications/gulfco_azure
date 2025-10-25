from odoo import models,fields,api,Command,_
from collections import defaultdict
from odoo.tools import lazy
import logging

_logger = logging.getLogger(__name__)

class SaleOrderLoyalty(models.Model):
    _inherit = 'sale.order'

    def _create_invoices(self, grouped=False, final=False):
        invoices = super()._create_invoices(grouped=grouped, final=final)

        for inv in invoices:
            for line in inv.invoice_line_ids:
                if any(sale_line.is_reward_line for sale_line in line.sale_line_ids):
                    sale_line = line.sale_line_ids[:1]
                    if sale_line:
                        order = sale_line.order_id

                        # Only *normal* product lines from SO
                        normal_lines = order.order_line.filtered(lambda l: not l.is_reward_line)
                        total_order_amount = sum(normal_lines.mapped('price_subtotal'))

                        # Amount of *normal* lines in this invoice only
                        this_invoice_amount = sum(
                            inv.invoice_line_ids.filtered(
                                lambda il: not any(sl.is_reward_line for sl in il.sale_line_ids)
                            ).mapped('price_subtotal')
                        )

                        if total_order_amount > 0:
                            proportion = this_invoice_amount / total_order_amount
                            line.price_unit = sale_line.price_unit * proportion

            # Add reward lines to invoices that don't have them yet
            for so in inv.invoice_line_ids.mapped('sale_line_ids.order_id'):
                reward_lines = so.order_line.filtered(lambda l: l.is_reward_line)
                for reward_line in reward_lines:
                    normal_lines = so.order_line.filtered(lambda l: not l.is_reward_line)
                    total_order_amount = sum(normal_lines.mapped('price_subtotal'))

                    this_invoice_amount = sum(
                        inv.invoice_line_ids.filtered(
                            lambda il: not any(sl.is_reward_line for sl in il.sale_line_ids)
                        ).mapped('price_subtotal')
                    )

                    proportion = this_invoice_amount / total_order_amount if total_order_amount else 0

                    create_line = False
                    if reward_line.product_id.type == 'service':
                        create_line = True
                    else:
                        # for goods/combo → only if delivered qty > 0
                        if reward_line.qty_delivered > 0:
                            create_line = True

                    # Only add if allowed, proportion > 0, and not already in this invoice
                    if create_line and proportion > 0 and not any(
                            reward_line in il.sale_line_ids for il in inv.invoice_line_ids):
                        inv_line_vals = {
                            'name': reward_line.name,
                            'product_id': reward_line.product_id.id,
                            'quantity': reward_line.product_uom_qty if reward_line.product_id.type == 'service' else reward_line.qty_delivered,
                            'price_unit': reward_line.price_unit * proportion,
                            'sale_line_ids': [(6, 0, [reward_line.id])],
                            'tax_ids': [(6, 0, reward_line.tax_id.ids)],
                            'move_id': inv.id,
                        }

                        acl = self.env['account.move.line'].create(inv_line_vals)
                        _logger.info("BEFORE CREATE INVOICE LINE Debit: %s --- Credit: %s" %(acl.debit, acl.credit))

            # Get FOC account (must be a Balance Sheet account)
        foc_account_id = self.env['ir.config_parameter'].sudo().get_param('loyalty_extension.foc_account_id')
        foc_account_id = int(foc_account_id) if foc_account_id else False

        invoices._postprocess_foc_lines(foc_account_id=foc_account_id)
        return invoices



    reward_discount_amount = fields.Monetary(
        string="Reward Discount",
        readonly=True,
        store=True,
        currency_field='currency_id',
        copy=False
    )
    applied_discount_reward_ids = fields.Many2many('loyalty.reward',string="Applied Discount Rewards",copy=False)



    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id','order_line.test_discount_value')
    def _compute_tax_totals(self):
        super(SaleOrderLoyalty,self)._compute_tax_totals()
        for order in self:
            total_discount_amount = 0.0
            reward_discount = 0.0
            for line in order.order_line:
                if line.reward_id:
                    reward_discount += line.price_subtotal
                else:
                    total_discount_amount += line.price_subtotal + line.discount_amount
            # before_discount_amount = sum(order.order_line.filtered(lambda s: not s.reward_id).mapped('price_subtotal')) + total_discount_amount
            order.tax_totals['before_discount_amount'] = str(total_discount_amount) + str(order.currency_id.symbol)
            # order.tax_totals['reward_discount_amount'] = "{:,.3f}".format(sum(order.order_line.mapped('test_discount_value'))) + str(order.currency_id.symbol)
            # order.tax_totals['reward_discount_amount'] = "{:,.3f}".format(reward_discount) + str(order.currency_id.symbol)

    # @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id','reward_discount_amount')
    # def _compute_amounts(self):
    #     res = super(SaleOrderLoyalty, self)._compute_amounts()
    #     for order in self:
    #         amount_total = order.amount_total - (order.reward_discount_amount or 0.0)
    #         order.amount_total = amount_total
    #     return res


    # def _get_claimable_rewards(self, forced_coupons=None):
    #     """
    #     Fetch all rewards that are currently claimable from all concerned coupons,
    #      meaning coupons from applied programs and applied rewards or the coupons given as parameter.
    #
    #     Returns a dict containing the all the claimable rewards grouped by coupon.
    #     Coupons that can not claim any reward are not contained in the result.
    #     """
    #     self.ensure_one()
    #     all_coupons = forced_coupons or (
    #                 self.coupon_point_ids.coupon_id | self.order_line.coupon_id | self.applied_coupon_ids)
    #     has_payment_reward = any(line.reward_id.program_id.is_payment_program for line in self.order_line)
    #     global_discount_reward = self._get_applied_global_discount()
    #     active_products_domain = self.env['loyalty.reward']._get_active_products_domain()
    #     discountable = lazy(lambda: self._discountable_amount(global_discount_reward))
    #
    #     total_is_zero = self.currency_id.is_zero(discountable)
    #     result = defaultdict(lambda: self.env['loyalty.reward'])
    #     for coupon in all_coupons:
    #         points = self._get_real_points_for_coupon(coupon)
    #
    #
    #         # rules_with_customer = coupon.program_id.rule_ids.filtered(
    #         #     lambda rule: rule.customer_ids and self.partner_id.id in rule.customer_ids.ids
    #         # )
    #         rules_with_customer = coupon.program_id.rule_ids.filtered(
    #             lambda rule: not rule.customer_ids or self.partner_id.id in rule.customer_ids.ids
    #         )
    #         if not rules_with_customer:
    #             rules_without_customers = coupon.program_id.rule_ids.filtered(lambda rule: rule.customer_ids)
    #             if rules_without_customers:
    #                 continue
    #         for reward in coupon.program_id.reward_ids:
    #
    #             if (
    #                     reward.is_global_discount
    #                     and global_discount_reward
    #                     and self._best_global_discount_already_applied(
    #                 global_discount_reward, reward, discountable
    #             )
    #             ):
    #                 continue
    #             # Discounts are not allowed if the total is zero unless there is a payment reward, in which case we allow discounts.
    #             # If the total is 0 again without the payment reward it will be removed.
    #             is_discount = reward.reward_type == 'discount'
    #             is_payment_program = reward.program_id.is_payment_program
    #             if is_discount and total_is_zero and (not has_payment_reward or is_payment_program):
    #                 continue
    #             # Skip discount that has already been applied if not part of a payment program
    #             if is_discount and not is_payment_program and reward in self.order_line.reward_id:
    #                 continue
    #             if reward.reward_type == 'product' and not reward.filtered_domain(
    #                     active_products_domain
    #             ):
    #                 continue
    #             if points >= reward.required_points:
    #                 result[coupon] |= reward
    #     return result

    # def _write_vals_from_reward_vals(self, reward_vals, old_lines, delete=True):
    #     actual_reward_val_list = []
    #     total_discount = 0.0
    #     applied_discount_reward_ids = []
    #     for val in reward_vals:
    #         if val.get('reward_id'):
    #             reward = self.env['loyalty.reward'].browse(val.get('reward_id'))
    #             if reward and reward.reward_type == 'discount' and reward in self.applied_discount_reward_ids:
    #                 continue
    #             elif reward and reward.reward_type == 'discount' and reward not in self.applied_discount_reward_ids:
    #                 amount = val.get('price_unit') or 0.0
    #                 qty = val.get('product_uom_qty') or 1.0
    #                 total_discount += (-amount * qty)
    #                 applied_discount_reward_ids.append(reward.id)
    #             else:
    #                 actual_reward_val_list.append(val)
    #     self.reward_discount_amount += total_discount
    #     self.write({'applied_discount_reward_ids': [(6,0, self.applied_discount_reward_ids.ids + applied_discount_reward_ids)]})
    #     res = super()._write_vals_from_reward_vals(actual_reward_val_list, old_lines, delete)
    #     return res

    def _write_vals_from_reward_vals(self, reward_vals, old_lines, delete=True):
        actual_reward_val_list = []
        for val in reward_vals:
            if val.get('reward_id'):
                reward = self.env['loyalty.reward'].browse(val.get('reward_id'))
                if reward and reward.reward_type == 'discount':
                    continue
                else:
                    actual_reward_val_list.append(val)
        res = super()._write_vals_from_reward_vals(actual_reward_val_list, old_lines, delete)
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    # rest
    def _get_display_price(self):
        # set zero when reward line type is free product
        if self.is_reward_line and self.reward_id.reward_type == 'product':
            return 0.00
        return super()._get_display_price()