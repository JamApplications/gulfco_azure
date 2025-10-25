from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True,
        help='Shows the company base currency'
    )

    is_exchange = fields.Boolean(
        string='Apply Manual Currency',
        help='Enable to apply a manual exchange rate (e.g. 1 EUR = 4.30 AED)'
    )

    rate = fields.Float(
        string='Rate',
        help='Enter manual rate from sale currency to company currency (e.g. 1 EUR = 4.30 AED)',
        default=1
    )

    @api.constrains('company_currency_id', 'currency_id')
    def _onchange_different_currency(self):
        """ Auto-disable manual exchange if base currency = SO currency """
        for rec in self:
            if rec.company_currency_id == rec.currency_id and rec.is_exchange:
                rec.is_exchange = False

    @api.onchange('is_exchange', 'currency_id', 'company_currency_id', 'date_order')
    def _onchange_is_exchange(self):
        """ Autofill rate if exchange is enabled """
        for rec in self:
            if rec.is_exchange and rec.currency_id and rec.company_currency_id:
                rec.rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=rec.company_currency_id,
                    to_currency=rec.currency_id,
                    company=rec.company_id,
                    date=rec.date_order or fields.Date.today()
                )
