# Copyright 2018 Creu Blanca
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"


    foc_account_id = fields.Many2one(
        'account.account',
        string="FOC Account",
        config_parameter='loyalty_extension.foc_account_id'  # optional, stores automatically
    )