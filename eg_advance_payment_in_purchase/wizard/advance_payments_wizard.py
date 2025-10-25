from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError


class AdvancePaymentsWizard(models.TransientModel):
    _name = "advance.payments.wizard"

    origin = fields.Char(string="Origin")
    paid_amount = fields.Float(string="Amount")
    total_amount = fields.Float(string="Total Amount")
    remaining_amount = fields.Float(string="Remaining Amount")
    amount_difference = fields.Float(string="Amount Difference")
    currency_id = fields.Many2one(comodel_name="res.currency", string="currency")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
    date = fields.Datetime(string="Payment Date")
    journal_id = fields.Many2one(comodel_name="account.journal", string="Account Journal")
    payment_method_id = fields.Many2one(comodel_name="account.payment.method", string="Payment Method")

    @api.model
    def default_get(self, fields_list):
        res = super(AdvancePaymentsWizard, self).default_get(fields_list)
        purchase_id = self.env["purchase.order"].browse(self._context.get("active_id"))
        total_payment = sum(purchase_id.payment_line.mapped("amount")) if purchase_id.payment_line else 0
        if purchase_id.order_line.filtered(lambda l: l.product_qty > l.qty_invoiced):
            res["origin"] = purchase_id.name
            res["total_amount"] = purchase_id.amount_total
            res["paid_amount"] = purchase_id.amount_total - total_payment
            res["remaining_amount"] = purchase_id.amount_total - total_payment
            res["partner_id"] = purchase_id.partner_id.id
            res["currency_id"] = purchase_id.currency_id.id
            res["date"] = datetime.now()
        else:
            res["origin"] = purchase_id.name
            res["total_amount"] = purchase_id.amount_total
            res["remaining_amount"] = purchase_id.amount_total - total_payment
            res["paid_amount"] = purchase_id.amount_total - total_payment
            res["partner_id"] = purchase_id.partner_id.id
            res["currency_id"] = purchase_id.currency_id.id
        return res

    @api.onchange("paid_amount", "total_amount", "remaining_amount")
    def onchange_paid_amount(self):
        # self.amount_difference = self.total_amount - self.paid_amount
        self.amount_difference = self.remaining_amount - self.paid_amount

    def submit_payment(self):
        purchase_id = self.env["purchase.order"].browse(self._context.get("active_id"))
        if not self.partner_id.advance_account_payable_id:
            raise UserError(_("Please set the Advance Account Receivable for the Vendor: {}").format(purchase_id.partner_id.name))

        payment = self.env["account.payment"].create(
            {
                "partner_id": purchase_id.partner_id.id,
                # 'company_id': self.env.user.company_id.id,
                "date": self.date,
                "currency_id": self.currency_id.id,
                "amount": self.paid_amount,
                "payment_type": "outbound",
                "partner_type": "supplier",
                "journal_id": self.journal_id.id,
                "payment_method_id": self.payment_method_id.id,
                "memo": purchase_id.name,
                "purchase_id": purchase_id.id,
                "advance_sale_purchase": "purchase",
            }
        )
        payment.move_id.line_ids.filtered(lambda x: x.debit > 0).update({"account_id": purchase_id.partner_id.advance_account_payable_id.id})
        payment.action_post()
