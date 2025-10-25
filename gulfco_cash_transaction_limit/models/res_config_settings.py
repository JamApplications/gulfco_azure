from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_cash_transaction_limit = fields.Boolean(
        string='Cash Limit Feature',
        config_parameter='account.enable_cash_transaction_limit',
        help="This field will enable Cash limit feature for Cash Customer"
    )
