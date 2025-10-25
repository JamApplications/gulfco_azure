from odoo import models, fields, api

class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _prepare_base_line_for_taxes_computation(self, line, **kwargs):
        base_line = super()._prepare_base_line_for_taxes_computation(line, **kwargs)
        
        if line and line._name in ['sale.order.line', 'account.move.line'] and line.exercise_price:
            base_line['excise_amount'] = line.exercise_price
            
        return base_line

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        # Check if custom logic should apply
        if (
            not base_line.get("excise_amount", 0)
            or not base_line.get("record", False)
        ):
            return super()._add_tax_details_in_base_line(base_line=base_line, company=company, rounding_method=rounding_method)
        
        rounding_method = rounding_method or company.tax_calculation_rounding_method
        # price_unit_after_discount = (base_line['price_unit'] + base_line['excise_amount']) * (1 - (base_line['discount'] / 100.0))
        price_unit_after_discount = (base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))) + base_line['excise_amount']
        taxes_computation = base_line['tax_ids']._get_tax_details(
            price_unit=price_unit_after_discount,
            quantity=base_line['quantity'],
            precision_rounding=base_line['currency_id'].rounding,
            rounding_method=rounding_method,
            product=base_line['product_id'],
            special_mode=base_line['special_mode'],
            manual_tax_amounts=base_line['manual_tax_amounts'],
            filter_tax_function=base_line['filter_tax_function'],
        )
        rate = base_line['rate']
        tax_details = base_line['tax_details'] = {
            'raw_total_excluded_currency': taxes_computation['total_excluded'],
            'raw_total_excluded': taxes_computation['total_excluded'] / rate if rate else 0.0,
            'raw_total_included_currency': taxes_computation['total_included'],
            'raw_total_included': taxes_computation['total_included'] / rate if rate else 0.0,
            'taxes_data': [],
        }
        if rounding_method == 'round_per_line':
            tax_details['raw_total_excluded'] = company.currency_id.round(tax_details['raw_total_excluded'])
            tax_details['raw_total_included'] = company.currency_id.round(tax_details['raw_total_included'])
        for tax_data in taxes_computation['taxes_data']:
            tax_amount = tax_data['tax_amount'] / rate if rate else 0.0
            base_amount = tax_data['base_amount'] / rate if rate else 0.0
            if rounding_method == 'round_per_line':
                tax_amount = company.currency_id.round(tax_amount)
                base_amount = company.currency_id.round(base_amount)
            tax_details['taxes_data'].append({
                **tax_data,
                'raw_tax_amount_currency': tax_data['tax_amount'],
                'raw_tax_amount': tax_amount,
                'raw_base_amount_currency': tax_data['base_amount'],
                'raw_base_amount': base_amount,
            })
