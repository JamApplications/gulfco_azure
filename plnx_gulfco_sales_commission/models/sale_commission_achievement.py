
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, api


class CommissionAchievement(models.Model):
    _inherit = 'sale.commission.achievement'


    partner_id = fields.Many2one('res.partner', "Salesperson", required=True,
                                 domain="[('contact_type', '=', 'worker')]")

    # kpi_type = fields.Selection(related='plan_id.kpi_type', store=True)
