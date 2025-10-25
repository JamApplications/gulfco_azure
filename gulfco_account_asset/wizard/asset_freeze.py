# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning



class AssetFreeze(models.TransientModel):
    _name = 'asset.freeze'

    date = fields.Date(string="Date")
    name = fields.Text(string="Memo")

    def freeze(self):
        for asset in self.env['account.asset'].search([('id', 'in', self.env.context['active_ids'])]):
            asset.pause(pause_date=self.date, message=self.name)

