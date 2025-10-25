from odoo import models, fields, Command


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    test_discount = fields.Float(
        string="Test Discount(%)",
        digits="Discount",
        default=0.0,
        copy=False,
    )

    test_discount_value = fields.Float(
        string="Test Discount",
        digits="Discount",
        default=0.0,
        copy=False,
    )
    account_move_line_reward_ids = fields.One2many(
        "account.move.line.reward",
        "account_move_line_id",
        string="Applied Rewards",
        copy=False,
    )

    discount_unit_price = fields.Float("Disc Unit Price")


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, **optional_values):
        """Inject SO custom discount fields into invoice lines."""
        vals = super()._prepare_invoice_line(**optional_values)

        # Proportionality ratio for amounts stored at SO-line reward level to handle partial invoicing
        so_qty = self.product_uom_qty or 0.0
        aml_qty = vals.get('quantity', 0.0) or 0.0
        ratio = aml_qty / so_qty if so_qty else 1.0

        vals.update({
            "test_discount": self.test_discount,
            "test_discount_value": self.test_discount_value,

        })

        aml_reward_vals = []
        for so_reward in self.sale_order_line_reward_ids:
            aml_reward_vals.append(Command.create({
                "name": so_reward.name,
                "applied_reward_id": so_reward.applied_reward_id.id,
                "applied_discount_value": so_reward.applied_discount_value * ratio,
                "applied_discount": so_reward.applied_discount,
                "discount_type": so_reward.discount_type,
            }))
        vals["account_move_line_reward_ids"] = aml_reward_vals
        discount = 0
        discount_amount = self.discount_amount
        discount_unit_price = self.discount_unit_price
        if self.discount_amount > 0:
            qty = self.product_uom_qty
            if self.product_uom_qty != self.qty_delivered:
                qty = self.qty_delivered
            discount = (self.discount_amount * 100) / (qty * self.price_unit)
            discount_amount = qty * self.price_unit * discount
            discount_unit_price = discount / qty

        vals.update({
            "discount_amount": self.discount_amount,
            "discount_unit_price": self.discount_unit_price,
            "discount": discount,
        })
        return vals
