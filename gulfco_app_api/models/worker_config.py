from odoo import fields, models, api


class WorkerConfig(models.Model):
    _name = 'worker.config'
    _description = 'Description'

    app_id = fields.Many2one("gulfco.mobile.app")
    worker_id = fields.Many2one('res.partner')
    update_customer_geo_location = fields.Boolean(default=False)
    allow_to_pay_in_multiple_ways = fields.Boolean(default=False)
    allow_to_cancel_sale_order = fields.Boolean(default=False)
    _sql_constraints = [
        ('unique_worker_per_app',
         'unique(app_id, worker_id)',
         'This worker is already configured for this app.')
    ]