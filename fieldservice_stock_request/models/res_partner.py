from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_van_load(self):
        location_id = self.env['stock.location']
        user_id = self.env['res.users'].search([('partner_id', '=', self.id)],limit=1)
        if user_id:
            location_id = self.env['stock.location'].search([('responsible_id','in',user_id.ids)],limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Request Orders',
            'view_mode': 'form',
            'view_id': self.env.ref('stock_request.stock_request_order_form').id,
            'res_model': 'stock.request.order',
            'target': 'current',
            'context': {'default_destination_id': location_id.id or False,'default_direction':'van_load' ,'default_warehouse_id': location_id.warehouse_id.id or False},
        }
    def action_van_off_load(self):
        location_id = self.env['stock.location']
        user_id = self.env['res.users'].search([('partner_id', '=', self.id)],limit=1)
        if user_id:
            location_id = self.env['stock.location'].search([('responsible_id','in',user_id.ids)],limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Request Orders',
            'view_mode': 'form',
            'view_id': self.env.ref('stock_request.stock_request_order_form').id,
            'res_model': 'stock.request.order',
            'target': 'current',
            'context': {'default_destination_id': location_id.id or False, 'default_direction': 'van_off_load',
                        'default_warehouse_id': location_id.warehouse_id.id or False},
        }