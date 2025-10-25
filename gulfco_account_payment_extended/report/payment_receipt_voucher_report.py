from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PaymentReceiptVoucherReport(models.AbstractModel):
    _name = 'report.gulfco_account_payment_extended.receipt_voucher_doc'
    _template = 'gulfco_account_payment_extended.receipt_voucher_doc'
    _description = 'Payment Receipt Voucher Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        payments = self.env['account.payment'].browse(docids)
        for payment in payments:
            if payment.state == 'draft':
                raise UserError("You cannot print the receipt voucher while the payment is in draft state.")
        return {
            'doc_ids': docids,
            'docs': payment,
        }
