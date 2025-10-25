from odoo import models, fields, api
from datetime import date

class VanDailyCollectionWizard(models.TransientModel):
    _name = 'van.daily.collection.wizard'
    _description = 'Van Daily Collection Wizard'

    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)

    def print_report(self):
        data = {
            'user_id': self.user_id.id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
        }
        return self.env.ref('plennix_mobile_app.action_report_van_daily_collection').report_action(self, data=data)