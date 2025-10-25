# Copyright (C) 2019 Brian McMaster
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    fsm_order_id = fields.Many2one(
        "fsm.order",
        string="FSM Order (Visit)",
        readonly=False,
    )
    assign_to = fields.Many2one('res.partner', string="Assign To")


    list_of_mapped_items = fields.Many2many('product.template', 'rel_templ_map', compute="_get_mapped_items")
    customer_worker_ids = fields.Many2many('res.partner', string="Customer Workers",
                                           compute="compute_customer_worker_ids", store=True)

    @api.depends('partner_id')
    def compute_customer_worker_ids(self):
        for record in self:
            customer_worker_ids = []
            if record.partner_id:
                worker_ids = self.env['customer.mapping'].sudo().search(
                    [('customer_id', '=', record.partner_id.id)]).mapped('customer_map_lines').mapped('worker_id')
                if worker_ids:
                    customer_worker_ids = worker_ids.ids
            record.customer_worker_ids = customer_worker_ids


    def _get_mapped_items(self):
        for rec in self:
            rec.list_of_mapped_items = None
            if rec.fsm_order_id:
                mapped_customer = self.env['customer.mapping'].search([('customer_id', '=', rec.partner_id.id)], limit=1)

                list_of_items = []
                workers = mapped_customer.customer_map_lines.filtered(lambda map: map.worker_id == rec.assign_to)
                division = workers.mapped('division')
                categ_id = workers.mapped('categ_id')
                for cat in categ_id:
                    filter_items = self.env['product.template'].search([('categ_id', 'child_of', cat.ids), ('division', 'in', division)])
                    list_of_items.append(filter_items.ids)
                flattened_list = [item for sublist in list_of_items for item in sublist]
                rec.list_of_mapped_items = [(6, 0, flattened_list)] or None




class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    list_of_mapped_items = fields.Many2many(related='order_id.list_of_mapped_items')




