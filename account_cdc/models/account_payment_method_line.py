from odoo import api, fields, models


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    is_cdc_payable = fields.Boolean(
        string='Is CDC Payable',
    )
