from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    visit_id = fields.Many2one('fsm.order', string="Visit")
    collector_id = fields.Many2one('res.partner',related="visit_id.person_id_partner",string="Collector Partner")

    def get_settlement_invoice(self):
        return  self.invoice_ids | self.reconciled_invoice_ids

    def get_payment_paid_amount(self):
        for pay in self:
            applied_amounts = 0.0
            for line in pay.move_id.line_ids:
                for matched in line.matched_debit_ids + line.matched_credit_ids:
                    other_line = matched.debit_move_id if matched.debit_move_id != line else matched.credit_move_id
                    invoice = other_line.move_id
                    if invoice.move_type in ['out_invoice', 'in_invoice']:
                        applied_amounts += matched.amount
            return applied_amounts


