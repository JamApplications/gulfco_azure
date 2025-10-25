#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models,fields


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    is_department_plan = fields.Boolean(string="Is Department Plan")