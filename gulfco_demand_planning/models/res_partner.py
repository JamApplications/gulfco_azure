# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class Partner(models.Model):
    _inherit = "res.partner"

    supplier_mos = fields.Integer(string="MOS")
