# models/fsm_router_setup.py
from odoo import models, fields

class FSMRouterSetup(models.Model):
    _name = "fsm.router.setup"
    _description = "FSM Router Setup"
    _rec_name = "worker_id"

    worker_id = fields.Many2one(
        comodel_name="res.partner",
        string="Worker",
        domain=[('contact_type', '=', 'worker')]
    )
    line_ids = fields.One2many(
        comodel_name="fsm.router.setup.line",
        inverse_name="setup_id",
        string="Router Lines"
    )

class FSMRouterSetupLine(models.Model):
    _name = "fsm.router.setup.line"
    _description = "FSM Router Setup Line"

    setup_id = fields.Many2one(
        comodel_name="fsm.router.setup",
        string="Setup",
        ondelete="cascade"
    )

    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        domain=[('contact_type', '=', 'customer')]
    )

    location_ids = fields.Many2many(
        comodel_name="fsm.location",
        relation="fsm_router_setup_line_location_rel",
        column1="line_id",
        column2="partner_id",
        string="Locations",
        domain="[('partner_id', '=', customer_id)]"
    )

    route_day_ids = fields.Many2many(
        comodel_name="fsm.route.day",
        relation="fsm_router_setup_line_rel",
        column1="line_id",
        column2="setup_id",
        string="Route Days"
    )