# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, tools

class InventoryAtDateWizard(models.TransientModel):
    _name = 'inventory.at.date.wizard'
    _description = 'Inventory at Date Wizard'

    date = fields.Date(string="Inventory Date", required=True, default=fields.Date.today)

    def action_open_inventory(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Inventory at Date',
            'res_model': 'inventory.query',   # your SQL view model
            'view_mode': 'list',
            'domain': [('date', '<=', self.date)],
            'context': {'inventory_date': self.date},
        }