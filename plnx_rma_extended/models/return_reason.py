# Copyright 2020 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ReturnReason(models.Model):
    _name = "rma.return.reason"
    _description = "RMA Return Reason"
    _order = "name"

    name = fields.Char(
        string='Name',
        required=True,
        translate=True
    )

    type = fields.Many2one("rma.return.reason.type",string="Type")

    active = fields.Boolean(
        string='Active',
        default=True
    )

    is_salable = fields.Boolean(default=True)

