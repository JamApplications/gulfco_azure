# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning



class AssetDispose(models.TransientModel):
    _name = 'asset.dispose'

    date = fields.Date(string="Dispose Date")
    loss_account_id = fields.Many2one(comodel_name="account.account", string="Loss Account")
    name = fields.Text(string="Memo")
    asset_ids = fields.Many2many('account.asset', string="Selected Assets")

    def dispose(self):
        for asset in self.env['account.asset'].search([('id', 'in', self.env.context['active_ids'])]):
            if self.loss_account_id == asset.account_depreciation_id:
                raise UserError(_("You cannot select the same account as the Depreciation Account"))
            invoice_lines = self.env['account.move.line']
            asset.set_to_dispose(invoice_line_ids=invoice_lines, date=self.date, message=self.name)

