# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT



class FSMOrder(models.Model):
    _inherit = "fsm.order"

    partner_team_member_ids = fields.Many2many('res.partner', 'fsm_order_sale_team_members_rel', string='Team Members',
                                               compute="_get_team_member", store=True)

    @api.depends('team_id')
    def _get_team_member(self):
        for rec in self:
            rec.partner_team_member_ids = None
            if self.team_id.sales_team_id.partner_member_ids:
                rec.partner_team_member_ids = [(6, 0, self.team_id.sales_team_id.partner_member_ids.ids)]

    person_id_partner = fields.Many2one("res.partner", string="Assigned To",
                                        domain="[('id', 'in', partner_team_member_ids)]")

    sale_ids = fields.Many2many("sale.order", 'rel_sale_fsm_order')
    sale_order_count = fields.Integer(
        "Number of SO Quot", compute='_compute_so_count',
        help="Number of SO Quotation Order")


    rma_ids = fields.One2many("rma", 'visit_id')
    rma_count = fields.Integer(
        "Number of RMA", compute='_compute_rma_count',
        help="Number of RMA")

    def _compute_rma_count(self):
        for rec in self:
            rec.rma_count = len(rec.rma_ids)

    def _compute_so_count(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_ids)


    def action_view_sales(self):
        self.ensure_one()

        if len(self.sale_ids) > 1:


            return {
                "type": "ir.actions.act_window",
                "res_model": "sale.order",
                "views": [[False, "list"], [False, "kanban"], [False, "form"]],
                "domain": [('id', 'in', self.sale_ids.ids)],
                "context": {"create": False, "show_sale": True},
                "name": _("Sales Orders"),
            }
        else:
            return {
                "name": _("Sales Orders"),
                "type": "ir.actions.act_window",
                "views": [ [False, "form"]],
                "view_type": "form",
                "view_mode": "form",
                "res_model": "sale.order",
                "domain": [('id', 'in', self.sale_ids.ids)],
                "res_id": self.sale_ids.id,
            }

    def create_sale_quotation(self):
        vals = {
            'partner_id': self.customer_id.id,
            'partner_invoice_id': self.location_id.customer_id.id,
            'partner_shipping_id': self.location_id.shipping_address_id.id,
            'date_order': self.scheduled_date_start,
            'origin': self.name,
            'assign_to': self.person_id_partner.id,
            'team_id': self.team_id.sales_team_id.id,
            'project_id': self.project_id.id,
            'fsm_order_id': self.id,
            'customer_partner_channel': self.customer_id.partner_channel_id.id,

        }
        if self.env.user.has_group('plnx_sales_team.group_sales_team_van_sale'):
            vals['order_creation_source'] = 'vansales'
        elif self.env.user.has_group('plnx_sales_team.group_sales_team_pre_sales'):
            vals['order_creation_source'] = 'presales'

        self.write({'sale_ids': [(0,0, vals)]})
        return {
            "name": _("Sales Orders"),
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "view_type": "form",
            "view_mode": "form",
            "res_model": "sale.order",
            "domain": [('id', '=', self.sale_ids.ids[-1:][0])],
            "res_id": self.sale_ids.ids[-1:][0],
        }



    def action_view_rma(self):
        if len(self.rma_ids) > 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "rma",
                "views": [[False, "list"], [False, "form"]],
                "domain": [('id', 'in', self.rma_ids.ids)],
                "context": {"create": False, "show_sale": True},
                "name": _("RMA"),
            }
        else:
            return {
                "name": _("RMA"),
                "type": "ir.actions.act_window",
                "views": [[False, "form"]],
                "view_type": "form",
                "view_mode": "form",
                "res_model": "rma",
                "domain": [('id', 'in', self.rma_ids.ids)],
                "res_id": self.rma_ids.id,
            }



    def create_rma_request(self):
        # vals = {
        #     'partner_id': self.customer_id.id,
        #     'partner_invoice_id': self.location_id.customer_id.id,
        #     'partner_shipping_id': self.location_id.shipping_address_id.id,
        #     'date': self.scheduled_date_start,
        #     'origin': self.team_id.name + ' - ' + self.name,
        #     'responsible_worker_id': self.person_id_partner.id,
        #     'user_id': self.env.user.id,
        #     'crm_team_id': self.team_id.sales_team_id.id,
        #     'project_id': self.project_id.id,
        #     'visit_id': self.id,
        #     'return_caused_by': self.env.user.id,
        # }
        # self.write({'rma_ids': [(0, 0, vals)]})
        vals = {
            'default_partner_id': self.customer_id.id,
            'default_partner_invoice_id': self.location_id.customer_id.id,
            'default_partner_shipping_id': self.location_id.shipping_address_id.id,
            'default_date': self.scheduled_date_start,
            'default_origin': self.team_id.name + ' - ' + self.name,
            'default_responsible_worker_id': self.person_id_partner.id,
            'default_user_id': self.env.user.id,
            'default_crm_team_id': self.team_id.sales_team_id.id,
            'default_project_id': self.project_id.id,
            'default_visit_id': self.id,
            'default_return_caused_by': self.env.user.id,
        }
        return {
            "name": _("RMA"),
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "view_type": "form",
            "view_mode": "form",
            "res_model": "rma",
            'context': vals,
            # "domain": [('id', '=', self.rma_ids.ids[-1:][0])],
            # "res_id": self.rma_ids.ids[-1:][0],
        }




