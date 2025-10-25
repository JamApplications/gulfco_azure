from odoo import api, fields, models,_
from odoo.exceptions import UserError


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _change_standart_price_accounting_entries(self, new_price):
        # Handle account moves.
        if self.env.context.get('skip_price_change_journal'):
            return
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self.product_id}
        company_id = self.env.company
        am_vals_list = []
        for layer in self:
            product = layer.product_id
            value = layer.value

            if not product.is_storable or product.valuation != 'real_time':
                continue

            # Sanity check.
            if not product_accounts[product.id].get('expense'):
                raise UserError(_('You must set a counterpart account on your product category.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

            if value < 0:
                debit_account_id = product_accounts[product.id]['expense'].id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
            else:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['expense'].id

            name = _(
                '%(user)s changed cost from %(previous)s to %(new_price)s - %(record)s',
                user=self.env.user.name,
                previous=layer.lot_id.standard_price if layer.lot_id else product.standard_price,
                new_price=new_price,
                record=layer.lot_id.display_name or product.display_name
            )
            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': company_id.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [layer.id])],
                'move_type': 'entry',
                'line_ids': [(0, 0, {
                    'name': name,
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                    'quantity': 0,
                }), (0, 0, {
                    'name': name,
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                    'quantity': 0,
                })],
            }
            am_vals_list.append(move_vals)

        account_moves = self.env['account.move'].sudo().create(am_vals_list)
        if account_moves:
            account_moves._post()
