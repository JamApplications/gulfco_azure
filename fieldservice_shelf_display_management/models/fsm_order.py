from odoo import models, fields, api
from datetime import datetime, date

class FieldServiceOrder(models.Model):
    _inherit = 'fsm.order'

    def action_open_shelf_display(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shelf Display',
            'res_model': 'shelf.display',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_customer_id': self.customer_id.id if self.customer_id else False,
                'default_visit_id': self.id,
                'default_worker_id': self.person_id_partner.id if self.person_id_partner else False,
                'default_date': date.today().strftime("%Y-%m-%d"),
            },
        }
