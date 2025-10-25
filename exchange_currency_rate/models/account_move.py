
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_exchange = fields.Boolean(string="Apply Manual Exchange",
                                help='Check this box if you want to manually '
                                                  'apply an exchange rate for this '
                                                  'transaction.')

    rate = fields.Float(string="Exchange Rate", compute="_compute_rate", inverse="_inverse_rate", store=True,
                        help='Specify the rate (e.g. 1 EUR = 4.30 AED)')

    invoice_company_currency_rate = fields.Float(
        string='Currency Rate',
        compute='_compute_invoice_currency_rate', store=True, precompute=True,
        copy=False,
        digits=0,
        help="Currency rate from company currency to document currency.",
    )

    # sale_order_id = fields.Many2one('sale.order', string="Sale Order", compute="_compute_sale_order",
    #                                 store=True,help="Linking corresponding Sale Order")
    # purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order",
    #                                     compute="_compute_purchase_order", store=True,help="Linking Purchase Order")

    @api.constrains('company_currency_id', 'currency_id')
    def _onchange_different_currency(self):
        """Disable manual exchange if base and invoice currency are the same"""
        for rec in self:
            if rec.company_currency_id == rec.currency_id and rec.is_exchange:
                rec.is_exchange = False

    # @api.depends('line_ids.sale_line_ids.order_id')
    # def _compute_sale_order(self):
    #     """ Compute Function to Update the Corresponding Sale Order """
    #     for move in self:
    #         sale_orders = move.line_ids.mapped('sale_line_ids.order_id')
    #         move.sale_order_id = sale_orders and sale_orders[0] or False

    # @api.depends('line_ids.purchase_line_id.order_id')
    # def _compute_purchase_order(self):
    #     """ Compute Function to Updmanualate the Corresponding Purchase Order """
    #     for move in self:
    #         purchase_orders = move.line_ids.mapped('purchase_line_id.order_id')
    #         move.purchase_order_id = purchase_orders and purchase_orders[0] or False

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date', 'rate', 'is_exchange')
    def _compute_invoice_currency_rate(self):
        """Override to support forward manual rate (e.g., 1 EUR = 4.30 AED)"""
        for move in self:
            if not move.is_exchange:
                return super(AccountMove, move)._compute_invoice_currency_rate()
                
            if move.is_invoice(include_receipts=True):
                if move.currency_id:
                    if move.is_exchange:
                        rate = move.rate if move.rate else 1
                        move.invoice_company_currency_rate = rate  # No inversion now
                        move.invoice_currency_rate = 1 / rate if rate else 1  # Optional reverse rate
                        continue
                    move.invoice_company_currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=move.company_currency_id,
                        to_currency=move.currency_id,
                        company=move.company_id,
                        date=move._get_invoice_currency_rate_date(),
                    )
                    move.invoice_currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=move.currency_id,
                        to_currency=move.company_currency_id,
                        company=move.company_id,
                        date=move._get_invoice_currency_rate_date(),
                    )
                else:
                    move.invoice_company_currency_rate = 1
                    move.invoice_currency_rate = 1

    @api.depends('rate')
    def _compute_rate(self):
        """Default rate from company ➝ invoice currency (forward rate)"""
        for move in self:
            move.rate = self.env['res.currency']._get_conversion_rate(
                from_currency=move.company_currency_id,
                to_currency=move.currency_id,
                company=move.company_id,
                date=move.date,
            )

    def _inverse_rate(self):
        """Allow manual editing of rate (already stored as forward rate, so nothing else needed)"""
        # This method can stay empty if there's no specific behavior required.
        pass
