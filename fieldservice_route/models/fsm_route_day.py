# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class FSMRouteDay(models.Model):
    _name = "fsm.route.day"
    _description = "Route Day"
    _rec_name = 'route_day_name'

    route_day_name = fields.Char(string="Name")

    _sql_constraints = [("route_day_name_uniq", "unique (route_day_name)", "Route name already exists!")]

    @api.constrains("route_day_name")
    def _check_unique_route_day_name(self):
        for rec in self:
            if not rec.route_day_name:
                continue
            # 🔹 Case-insensitive uniqueness check
            domain = [
                ("id", "!=", rec.id),
                ("route_day_name", "=ilike", rec.route_day_name),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    f"Route Day '{rec.route_day_name}' already exists!"
                )

    name = fields.Selection(
        selection=[
            ("Monday", "Monday"),
            ("Tuesday", "Tuesday"),
            ("Wednesday", "Wednesday"),
            ("Thursday", "Thursday"),
            ("Friday", "Friday"),
            ("Saturday", "Saturday"),
            ("Sunday", "Sunday"),
        ],
        string="Day"
    )
    week = fields.Selection(
        selection=[
            ("w1", "W1"),
            ("w2", "W2"),
            ("w3", "W3"),
            ("w4", "W4"),
            ("w5", "W5"),
        ],
        string="Week"
    )


