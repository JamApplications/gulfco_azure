from odoo import models, fields, api
from datetime import datetime, date

class FieldServiceOrderSrockStore(models.Model):
    _inherit = 'fsm.order'

    def action_open_stock_store(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Merchandise Stock Store',
            'res_model': 'merchandise.stock.store',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_customer_id': self.customer_id.id if self.customer_id else False,
                'default_location_id': self.location_id.id if self.location_id else False,
                'default_visit_id': self.id,
                'default_worker_id': self.person_id_partner.id if self.person_id_partner else False,
                'default_activity_date': date.today().strftime("%Y-%m-%d"),
            },
        }
