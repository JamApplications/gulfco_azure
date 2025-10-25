from odoo import models, fields, api


class MerchandiseStockStore(models.Model):
    _name = 'merchandise.stock.store'
    _description = 'Merchandise Stock Store'
    _rec_name = 'visit_id'

    location_id = fields.Many2one(
        'fsm.location',
        string='Location'
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )

    count_type = fields.Char(
        string='Count Type'
    )

    activity_date = fields.Date(
        string='Date'
    )

    worker_id = fields.Many2one(
        'res.partner',
        string='Worker Name',
        domain=[('contact_type', '=', 'worker')]
    )

    visit_id = fields.Many2one(
        'fsm.order',
        string='Visit',
        required=True
    )

    stock_lines_ids = fields.One2many(
        'merchandise.stock.store.lines',
        'store_id',
        string='Stock Lines'
    )

    @api.onchange('visit_id')
    def _onchange_visit_id(self):
        for record in self:
            if record.visit_id:
                record.location_id = record.visit_id.location_id.id if record.visit_id.location_id else False
                record.customer_id = record.visit_id.customer_id.id if record.visit_id.customer_id else False
                # record.customer_id = record.visit_id.product_id.partner_id if record.visit_id.product_id else False
                # record.activity_date = record.visit_id.date_order
                record.worker_id = record.visit_id.person_id_partner.id if record.visit_id.person_id_partner else False

