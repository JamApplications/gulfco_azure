from odoo import models, fields
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    bill_amount_currency = fields.Monetary(string='Total in AED',readonly=True,currency_field='currency_id',)

    vendor_code = fields.Char(string='Vendor Code')
    _depends = {'account.move': ['bill_amount_currency', 'vendor_code'],}

    def _select(self) -> SQL:
        return SQL("%s, move.bill_amount_currency,move.vendor_code",
                   super()._select())

