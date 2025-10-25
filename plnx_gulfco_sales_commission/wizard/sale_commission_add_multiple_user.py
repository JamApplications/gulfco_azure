# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, Command


class SaleCommissionPlanUserWizard(models.TransientModel):
    _inherit = 'sale.commission.plan.user.wizard'

    partner_ids = fields.Many2many('res.partner', "Salespersons_as_worker", string="Workers",  domain="[('contact_type', '=', 'worker')]")
    user_ids = fields.Many2many('res.users', "Salespersons", domain="[('share', '=', False)]")

    def submit(self):
        plan_id = self.env['sale.commission.plan'].browse(self.env.context.get('active_ids'))
        plan_id.user_ids = [Command.create({'partner_id': partner_id.id, 'plan_id': plan_id.id}) for partner_id in self.partner_ids]
        # plan_id.user_ids = [Command.create({'user_id': user_id.id, 'plan_id': plan_id.id}) for user_id in self.user_ids]
