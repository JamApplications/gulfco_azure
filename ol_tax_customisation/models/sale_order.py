# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    allowed_tax_ids = fields.Many2many(
        'account.tax',
        compute='_compute_allowed_tax_ids',
        string="Allowed Taxes",
        store=True
    )

    @api.depends('fiscal_position_id' ,'fiscal_position_id.tax_ids', 'company_id', 'tax_country_id')
    def _compute_allowed_tax_ids(self):
        for order in self:
            if order.fiscal_position_id:
                fp_allowed_tax_ids = order.fiscal_position_id.tax_ids.mapped('tax_dest_id')
                order.allowed_tax_ids = self.env["account.tax"].search(
                    [
                        ('id', 'in', fp_allowed_tax_ids.ids),
                        ("type_tax_use", "=", "sale"),
                        ("company_id", "parent_of", order.company_id.id),
                        ("country_id", "=", order.tax_country_id.id),
                    ]
                )
            else:
                order.allowed_tax_ids = self.env["account.tax"].search(
                    [
                        ("type_tax_use", "=", "sale"),
                        ("company_id", "parent_of", order.company_id.id),
                        ("country_id", "=", order.tax_country_id.id),
                    ]
                )
