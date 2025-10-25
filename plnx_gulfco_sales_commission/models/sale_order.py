# Copyright (C) 2019 Brian McMaster
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # worker_id = fields.Many2one('res.partner', "Salesperson", domain="[('contact_type', '=', 'worker')]",
    #                             default=lambda self: self.env.user.partner_id.id,)

    assign_to = fields.Many2one('res.partner', domain="[('contact_type', '=', 'worker')]",
                                string="Assign To", default=False)

    @api.depends('partner_id')
    def _compute_user_id(self):
        for order in self:
            if order.partner_id and not (order._origin.id and order.user_id):
                # Recompute the salesman on partner change
                #   * if partner is set (is required anyway, so it will be set sooner or later)
                #   * if the order is not saved or has no salesman already
                order.user_id = (
                        order.partner_id.user_id
                        or order.partner_id.commercial_partner_id.user_id
                        or (self.env.user.has_group('sales_team.group_sale_salesman') and self.env.user)
                )
                # order.assign_to = order.user_id.partner_id.id

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.assign_to:
            res['assign_to'] = self.assign_to.id
        return res
