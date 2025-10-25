from odoo import api, fields, models


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    is_pdc_payable = fields.Boolean(
        string='Is PDC Payable',
    )
