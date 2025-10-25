from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError


class AdvancePaymentWizard(models.TransientModel):
    _name = "advance.payment.wizard"

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
        res = super(AdvancePaymentWizard, self).default_get(fields_list)
        sale_id = self.env["sale.order"].browse(self._context.get("active_id"))
        total_payment = sum(sale_id.payment_line.mapped("amount")) if sale_id.payment_line else 0
        if sale_id.order_line.filtered(lambda l: l.invoice_status != "invoiced"):
            res["origin"] = sale_id.name
            res["total_amount"] = sale_id.amount_total
            res["paid_amount"] = sale_id.amount_total - total_payment
            res["remaining_amount"] = sale_id.amount_total - total_payment
            res["partner_id"] = sale_id.partner_id.id
            res["currency_id"] = sale_id.currency_id.id
            res["date"] = datetime.now()
        else:
            res["origin"] = sale_id.name
            res["total_amount"] = sale_id.amount_total
            res["remaining_amount"] = sale_id.amount_total - total_payment
            res["paid_amount"] = sale_id.amount_total - total_payment
            res["partner_id"] = sale_id.partner_id.id
        return res

    @api.onchange("paid_amount", "total_amount", "remaining_amount")
    def onchange_paid_amount(self):
        # self.amount_difference = self.total_amount - self.remaining_amount
        self.amount_difference = self.remaining_amount - self.paid_amount

    def submit_payment(self):
        if not self.partner_id.advance_account_receivable_id:
            raise UserError(_("Please set the Advance Account Receivable for the customer: {}").format(self.partner_id.name))
        sale_id = self.env["sale.order"].browse(self._context.get("active_id"))
        payment = self.env["account.payment"].create(
            {
                "partner_id": sale_id.partner_id.id,
                # 'company_id': self.env.user.company_id.id,
                "date": self.date,
                "currency_id": self.currency_id.id,
                "amount": self.paid_amount,
                "payment_type": "inbound",
                "partner_type": "customer",
                "journal_id": self.journal_id.id,
                "payment_method_id": self.payment_method_id.id,
                "memo": sale_id.name,
                'sale_id': sale_id.id,
                "advance_sale_purchase": "sale",
            }
        )
        payment.move_id.line_ids.filtered(lambda x: x.credit > 0).update({"account_id": self.partner_id.advance_account_receivable_id.id})
        payment.action_post()
