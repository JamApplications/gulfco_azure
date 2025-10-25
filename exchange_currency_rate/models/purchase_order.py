
from odoo import api, fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True, help="To store the Company Currency")

    is_exchange = fields.Boolean(string='Apply Manual Currency', help='Allows users to manually apply an exchange rate')
    rate = fields.Float(string='Rate', help='Specify the manual rate, e.g. 1 EUR = 4.30 AED', default=1)

    @api.constrains('company_currency_id', 'currency_id')
    def _onchange_different_currency(self):
        """ Disable manual exchange if currency = company currency """
        for rec in self:
            if rec.company_currency_id == rec.currency_id and rec.is_exchange:
                rec.is_exchange = False

    @api.onchange('is_exchange', 'currency_id', 'company_currency_id', 'date_order')
    def _onchange_is_exchange(self):
        """ Set forward rate (Company ➝ PO currency) when enabled """
        for rec in self:
            if rec.is_exchange and rec.currency_id and rec.company_currency_id:
                rec.rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=rec.company_currency_id,
                    to_currency=rec.currency_id,
                    company=rec.company_id,
                    date=rec.date_order or fields.Date.today()
                )
