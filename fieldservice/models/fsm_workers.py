from datetime import datetime, timedelta, date

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from . import fsm_stage


class FSMOrder(models.Model):
    _name = "fsm.workers"

    name = fields.Char(required=True)
    location_id = fields.Many2one('stock.location', string="Van Location")


    def action_open_inventory_adjustment(self):
        view = self.env.ref('stock_inventory_adjustment.view_stock_inventory_adjustment_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Count/Adjustment',
            'view_mode': 'form',
            'view_id': view.id,
            'res_model': 'stock.inventory.adjustment',
            'target': 'current',
            'context': {'default_location_id': self.location_id.id},
        }

    def action_open_van_stock(self):
        self.ensure_one()
        action_ref = self.env.ref('stock.location_open_quants')
        action_data = action_ref.read()[0]
        action_data['domain'] = [('location_id.responsible_id', "in", self.env.user.ids)]
        return action_data
