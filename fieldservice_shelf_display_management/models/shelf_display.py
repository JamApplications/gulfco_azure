from odoo import models, fields, api
from datetime import datetime, date

class ShelfDisplay(models.Model):
    _name = 'shelf.display'
    _description = 'Shelf Display'
    _rec_name = 'customer_id'

    customer_id = fields.Many2one('res.partner', string='Customer')
    display_area_id = fields.Many2one('display.area', string='Display Area')
    date = fields.Date(string='Activity Date')
    worker_id = fields.Many2one(
        'res.partner',
        string='Worker Name',
        domain=[('contact_type', '=', 'worker'), ('fsm_person', '=', True)],
    )
    visit_id = fields.Many2one('fsm.order', string='Visit')
    line_ids = fields.One2many('display.area.lines', 'display_id', string='Display Area Lines')

    # @api.onchange('visit_id')
    # def _onchange_visit_id(self):
    #     # Logic to auto-fill the fields based on the visit
    #     if self.visit_id:
    #         self.customer_id = self.visit_id.customer_id.id if self.visit_id.customer_id else False
    #         self.worker_id = self.visit_id.assign_to.id if self.visit_id.assign_to else False