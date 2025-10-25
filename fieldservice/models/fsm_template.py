# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _


class FSMTemplate(models.Model):
    _name = "fsm.template"
    _description = "Field Service Order Template"

    name = fields.Char(required=True)
    instructions = fields.Text()
    category_ids = fields.Many2many("fsm.category", string="Categories")
    duration = fields.Float(help="Default duration in hours")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        index=True,
        help="Company related to this template",
        default=lambda self: self.env.user.company_id,
    )
    type_id = fields.Many2one("fsm.order.type", string="Type")
    team_id = fields.Many2one(
        "fsm.team",
        string="Team",
        help="Choose a team to be set on orders of this template",
    )

    @api.onchange('team_id')
    def onchange_team_id(self):
        if self.team_id:
            self.name = self.team_id.name

    _sql_constraints = [
        (
            "company_team_id_unique",
            "UNIQUE(company_id,team_id)",
            "You cannot have the same Team twice.",
        )
    ]

