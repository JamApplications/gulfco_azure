from odoo import models, fields, api

class CustomerStock(models.Model):
    _name = 'customer.stock'
    _description = 'Customer Stock'
    _rec_name= 'visit_id'

    location_id = fields.Many2one('fsm.location', string='Location')
    customer_id = fields.Many2one('res.partner', string='Customer')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    worker_id = fields.Many2one('res.partner', string='Worker', domain=[('contact_type', '=', 'worker')])
    visit_id = fields.Many2one('fsm.order', string='Visit', required=1)
    line_ids = fields.One2many('customer.stock.line', 'stock_id', string='Stock Lines')

    @api.onchange('visit_id')
    def _onchange_visit_id(self):
        for record in self:
            if record.visit_id:
                record.location_id = record.visit_id.location_id.id if record.visit_id.location_id else False
                record.customer_id = record.visit_id.customer_id.id if record.visit_id.customer_id else False
                record.worker_id = record.visit_id.person_id_partner.id if record.visit_id.person_id_partner else False
