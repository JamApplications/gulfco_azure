# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_account_receivable_id = fields.Many2one(
        "account.account",
        string="Account Receivable",
        domain=[("account_type", "=", "asset_receivable"), ("deprecated", "=", False)],
        required=False,
    )
    property_account_payable_id = fields.Many2one(
        "account.account",
        string="Account Payable",
        domain=[("account_type", "=", "liability_payable"), ("deprecated", "=", False)],
        required=False,
    )

    advance_account_payable_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Advance Account Payable",
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
    )
    advance_account_receivable_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Advance Account Receivable",
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
    )
