# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT



class ResUsers(models.Model):
    _inherit = "res.users"

    allow_multi_employee = fields.Boolean(string='Allow Multiple Employee to login with Barcode PIN')