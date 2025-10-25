from odoo import models, api

class VanDailyCollectionReport(models.AbstractModel):
    _name = 'report.plennix_mobile_app.report_van_daily_collection'

    @api.model
    def _get_report_values(self, docids, data=None):
        user = self.env['res.users'].browse(data['user_id'])
        start_date = data['start_date']
        end_date = data['end_date']

        # Perform same logic as the mobile version (search for payments & RMAs, etc.)
        # Replace below with the actual logic you already wrote in the controller.
        payments = self.env['account.payment'].search([
            ('responsible_id', '=', user.partner_id.id),
            ('state', '=', 'paid'),
            ('date', '>=', start_date),
            ('date', '<=', end_date)
        ])

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        return {
            'doc_ids': docids,
            'doc_model': self.env['van.daily.collection.wizard'],
            'data': data,
            'docs': payments,
            'user': user,
            'start_date': start_date,
            'end_date': end_date,
            'base_url': base_url,
        }