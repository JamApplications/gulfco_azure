from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr, float_round, float_compare


class ProductProduct(models.Model):
    _inherit = 'product.product'


    def _change_standard_price(self, new_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        # Handle stock valuation layers.

        if self.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].has_access('read'):
            raise UserError(_("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        company_id = self.env.company
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        rounded_new_price = float_round(new_price, precision_digits=price_unit_prec)
        for product in self:
            if product.cost_method not in ('standard', 'average'):
                continue
            if product.lot_valuated:
                self.env['stock.lot'].search([('product_id', '=', product.id)]).standard_price = new_price
                continue
            quantity_svl = product.sudo().quantity_svl
            if float_compare(quantity_svl, 0.0, precision_rounding=product.uom_id.rounding) <= 0:
                continue
            value_svl = product.sudo().value_svl
            value = company_id.currency_id.round((rounded_new_price * quantity_svl) - value_svl)
            if company_id.currency_id.is_zero(value):
                continue

            svl_vals = {
                'company_id': company_id.id,
                'product_id': product.id,
                'description': _(
                    'Product value manually modified (from %(original_price)s to %(new_price)s)',
                    original_price=product.standard_price,
                    new_price=rounded_new_price,
                ),
                'value': value,
                'quantity': 0,
            }
            svl_vals_list.append(svl_vals)
        if self.env.context.get('skip_price_change_journal'):
            return
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
        stock_valuation_layers._change_standart_price_accounting_entries(new_price)

    def _prepare_out_svl_vals(self, quantity, company, lot=False):
        result = super(ProductProduct, self)._prepare_out_svl_vals(quantity, company, lot)
        if self.env.context.get('active_model') and self.env.context.get('active_model') == 'stock.return.picking':
            return_id = self.env['stock.return.picking'].browse(self.env.context.get('active_id'))
            if return_id.picking_id and return_id.picking_id.purchase_id:
                filter_product = return_id.picking_id.purchase_id.order_line.filtered(lambda prod:prod.product_id.id == self.id)
                if filter_product:
                    result.update({
                        'unit_cost': filter_product.price_unit,
                        'value': result['quantity'] * filter_product.price_unit
                    })
        return result
