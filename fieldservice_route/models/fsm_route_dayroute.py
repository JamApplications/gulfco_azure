# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta,date


class FSMRouteDayRoute(models.Model):
    _name = "fsm.route.dayroute"
    _description = "Field Service Route Dayroute"

    name = fields.Char(required=True, copy=False, default=lambda self: _("New"))
    # person_id = fields.Many2one(
    #     comodel_name="fsm.person",
    #     string="Person",
    #     compute="_compute_person_id",
    #     store=True,
    #     readonly=False,
    # )

    partner_team_member_ids = fields.Many2many('res.partner', 'sale_team_members_rel', string='Team Members',
                                               compute="_get_team_member", store=True)


    @api.depends('team_id')
    def _get_team_member(self):
        for rec in self:
            rec.partner_team_member_ids = None
            if self.team_id.sales_team_id.partner_member_ids:
                rec.partner_team_member_ids = [(6,0, self.team_id.sales_team_id.partner_member_ids.ids)]

    person_id_partner = fields.Many2one("res.partner",string="Worker", domain="[('id', 'in', partner_team_member_ids)]")

    @api.constrains('person_id_partner')
    def _check_assigned_to_belongs_to_team(self):
        for record in self:
            # Ensure the "assigned_to" is in the selected "team_id"
            if record.sales_team_id and record.person_id_partner:
                # Check if the assigned partner belongs to the team
                if record.person_id_partner not in record.sales_team_id.partner_member_ids:
                    raise ValidationError(
                        f"The selected Assigned person {record.person_id_partner.name} does not belong to the selected team."
                    )

    route_id = fields.Many2one(comodel_name="fsm.route", string="Route")
    route_setup_id = fields.Many2one(comodel_name="fsm.router.setup", string="Route")
    date = fields.Date()
    team_id = fields.Many2one(
        comodel_name="fsm.team",
        string="Team",
        default=lambda self: self._default_team_id(),
    )
    sales_team_id = fields.Many2one(
        "crm.team",
        string="Sales Team",
        related="team_id.sales_team_id", store=True,
    )
    stage_id = fields.Many2one(
        comodel_name="fsm.stage",
        string="Stage",
        domain="[('stage_type', '=', 'route')]",
        index=True,
        copy=False,
        default=lambda self: self._default_stage_id(),
    )
    longitude = fields.Float()
    latitude = fields.Float()
    last_location_id = fields.Many2one(
        comodel_name="fsm.location", string="Last Location"
    )
    date_start_planned = fields.Datetime(
        string="Planned Start Time",
        compute="_compute_date_start_planned",
        store=True,
        readonly=False,
    )
    start_location_id = fields.Many2one(
        comodel_name="fsm.location", string="Start Location"
    )
    end_location_id = fields.Many2one(
        comodel_name="fsm.location", string="End Location"
    )
    work_time = fields.Float(string="Time before overtime (in hours)", default=8.0)
    max_allow_time = fields.Float(
        string="Maximal Allowable Time (in hours)", default=10.0
    )
    order_ids = fields.One2many(
        comodel_name="fsm.order", inverse_name="dayroute_id", string="Orders"
    )
    order_count = fields.Integer(
        compute="_compute_order_count", string="Number of Orders", store=True
    )
    order_remaining = fields.Integer(
        compute="_compute_order_count", string="Available Capacity", store=True
    )
    max_order = fields.Integer(
        related="route_id.max_order",
        string="Maximum Capacity",
        store=True,
        help="Maximum numbers of orders that can be added to this day route.",
    )
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To',)

    @api.constrains('date_from', 'date_to')
    def _check_date_period(self):
        for record in self:
            if record.date_to and record.date_from:
                if record.date_to < record.date_from:
                    raise ValidationError("The 'To' date cannot be before the 'From' date.")

    @api.onchange('route_setup_id')
    def _onchange_route_setup_id(self):
        if self.route_setup_id:
            if self.route_setup_id.worker_id:
                crm_team = self.env['crm.team'].sudo().search([('partner_member_ids', 'in', self.route_setup_id.worker_id.id)], limit=1)
                if crm_team:
                    fsm_team = self.env['fsm.team'].sudo().search([('sales_team_id', '=', crm_team.id)], limit=1)
                    self.team_id = fsm_team.id or False

                self.person_id_partner = self.route_setup_id.worker_id.id

    # def create_records_between_dates(self, start_date, end_date, allowed_days):
    #     current_date = start_date
    #     records = []
    #
    #     while current_date <= end_date:
    #         # if current_date.strftime('%A').lower() in allowed_days:
    #         if current_date.strftime('%A') in allowed_days:
    #             # Create your record here
    #             records.append(current_date)  # Replace with actual record creation logic
    #         current_date += timedelta(days=1)
    #
    #     return records

    def create_records_between_dates(self, start_date, end_date, allowed_days, allowed_weeks):
        current_date = start_date
        records = []
        month = current_date.month
        week_number = 1
        week_start = current_date
        week_end = week_start + timedelta(days=6)
        while current_date <= end_date:
            if current_date.month != month:
                month = current_date.month
                week_number = 1
                week_start = current_date
                week_end = week_start + timedelta(days=6)
            week_key = f"w{week_number}"
            if (current_date.strftime('%A') in allowed_days) and (week_key in allowed_weeks):
                records.append(current_date)
            if current_date >= week_end:
                week_number += 1
                week_start = week_end + timedelta(days=1)
                week_end = week_start + timedelta(days=6)
            current_date += timedelta(days=1)

        return records

    def schedule_visits_button(self):
        # allowed_days = [day.name for day in self.route_id.day_ids]
        if self.order_ids:
            self.order_ids.unlink()
        order_vals_list = []
        for line in self.route_setup_id.line_ids:
            # allowed_days = [day.name for day in line.route_day_ids]
            # allowed_weeks = [day.week for day in line.route_day_ids]
            allowed_days, allowed_weeks = zip(
                *[(day.name, day.week) for day in line.route_day_ids]) if line.route_day_ids else ([], [])

            records_to_create = self.create_records_between_dates(start_date=self.date_from, end_date=self.date_to, allowed_days=allowed_days,allowed_weeks=allowed_weeks)
            route_location = line.location_ids
            print("route_location:", route_location)
            # self.order_ids.unlink()
            for rec in records_to_create:
                for loc in route_location:
                    vals = {
                        'location_id': loc.id,
                        'dayroute_id': self.id,
                        'team_id': self.team_id.id,
                        'person_id_partner': self.person_id_partner.id,
                        'scheduled_date_start': rec,
                        'customer_id':line.customer_id.id
                        # 'scheduled_duration': None,
                        # 'scheduled_date_end': None,
                    }

                    print("valsL", vals)
                    order_vals_list.append((0,0,vals))
                    # self.write({'order_ids':[(0,0,vals)]})
        self.write({'order_ids': order_vals_list})
        for order in self.order_ids:
            order.onchange_team_id()
            order._onchange_template_id()
            order._onchange_template_team_id()
            order._onchange_vehicle_person_id_partner()

            order.scheduled_duration = order.template_id.duration
            order.scheduled_date_end = order.scheduled_date_start + timedelta(hours=order.template_id.duration)

    # def schedule_visits_button(self):
    #     # allowed_days = [day.name for day in self.route_id.day_ids]
    #     allowed_days = [day.name for day in self.route_id.day_ids]
    #     records_to_create = self.create_records_between_dates(start_date=self.date_from, end_date=self.date_to, allowed_days=allowed_days)
    #
    #     fsm_order_ref = self.env['fsm.order'].sudo()
    #
    #
    #     route_location = self.env['fsm.location'].search([('fsm_route_ids', 'in', self.route_id.id)])
    #     print("route_location:", route_location)
    #     self.order_ids.unlink()
    #     for rec in records_to_create:
    #         for loc in route_location:
    #             vals = {
    #                 'location_id': loc.id,
    #                 'dayroute_id': self.id,
    #                 'team_id': self.team_id.id,
    #                 'person_id_partner': self.person_id_partner.id,
    #                 'scheduled_date_start': rec,
    #                 # 'scheduled_duration': None,
    #                 # 'scheduled_date_end': None,
    #             }
    #
    #             print("valsL", vals)
    #             self.write({'order_ids':[(0,0,vals)]})
    #
    #     for order in self.order_ids:
    #         order.onchange_team_id()
    #         order._onchange_template_id()
    #         order._onchange_template_team_id()
    #         order._onchange_vehicle_person_id_partner()
    #
    #         order.scheduled_duration = order.template_id.duration
    #         order.scheduled_date_end = order.scheduled_date_start + timedelta(hours=order.template_id.duration)

    def _default_team_id(self):
        teams = self.env["fsm.team"].search(
            [("company_id", "in", (self.env.user.company_id.id, False))],
            order="sequence asc",
            limit=1,
        )
        if teams:
            return teams
        else:
            raise ValidationError(_("You must create a FSM team first."))

    def _default_stage_id(self):
        return self.env["fsm.stage"].search(
            [("stage_type", "=", "route"), ("is_default", "=", True)], limit=1
        )

    @api.depends("route_id", "order_ids")
    def _compute_order_count(self):
        for rec in self:
            rec.order_count = len(rec.order_ids)
            rec.order_remaining = rec.max_order - rec.order_count

    # @api.depends("route_id", "route_id.fsm_person_id")
    # def _compute_person_id(self):
    #     for rec in self:
    #         if not rec.route_id.fsm_person_id:
    #             rec.person_id = None
    #             continue
    #
    #         rec.person_id = rec.route_id.fsm_person_id

    @api.depends("date")
    def _compute_date_start_planned(self):
        for rec in self:
            if not rec.date:
                rec.date_start_planned = None
                continue

            # TODO: Use the worker timezone and working schedule
            rec.date_start_planned = datetime.combine(
                rec.date, datetime.strptime("8:00:00", "%H:%M:%S").time()
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "fsm.route.dayroute"
                ) or _("New")
            if not vals.get("date_start_planned", False) and vals.get("date", False):
                # TODO: Use the worker timezone and working schedule
                date = vals.get("date")
                if isinstance(vals.get("date"), str):
                    date = datetime.strptime(
                        vals.get("date"), DEFAULT_SERVER_DATE_FORMAT
                    ).date()
                vals.update(
                    {
                        "date_start_planned": datetime.combine(
                            date, datetime.strptime("8:00:00", "%H:%M:%S").time()
                        )
                    }
                )
        return super().create(vals_list)

    # @api.constrains("date", "route_id")
    # def check_day(self):
    #     for rec in self:
    #         if rec.date and rec.route_id:
    #             # Get the day of the week: Monday -> 0, Sunday -> 6
    #             day_index = rec.date.weekday()
    #             day = self.env.ref("fieldservice_route.fsm_route_day_" + str(day_index))
    #             if day.id not in rec.route_id.day_ids.ids:
    #                 raise ValidationError(
    #                     _("The route %(route_name)s does not run on %(name)s!")
    #                     % {"route_name": rec.route_id.name, "name": day.name}
    #                 )

    # @api.constrains("route_id", "max_order", "order_count")
    # def check_capacity(self):
    #     for rec in self:
    #         if rec.route_id and rec.order_count > rec.max_order:
    #             raise ValidationError(
    #                 _(
    #                     "The day route is exceeding the maximum number of "
    #                     "orders of the route."
    #                 )
    #             )
