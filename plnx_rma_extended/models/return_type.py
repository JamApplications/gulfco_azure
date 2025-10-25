# Copyright 2020 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ReturnReasonType(models.Model):
    _name = "rma.return.reason.type"
    _description = "RMA Return Reason Type"
    _order = "name"

    name = fields.Char(
        string='Name',
        required=True,
        translate=True
    )

