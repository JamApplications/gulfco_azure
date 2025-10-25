from odoo import models, fields, api

class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _prepare_base_line_for_taxes_computation(self, line, **kwargs):
        base_line = super()._prepare_base_line_for_taxes_computation(line, **kwargs)

        if line and line._name == 'account.move.line' and line.move_id and line.move_id.is_purchase_document() and line.ass_value:
            base_line['ass_value'] = line.ass_value
            # base_line['price_unit'] = line.ass_value
            # base_line['quantity'] = 1  # Since ass_value is full amount, no need to multiply
            # base_line['discount'] = 0  # Since ass_value is full amount, no need to apply discount
            base_line['ass_value_applied'] = True  # Optional flag for debugging

        return base_line

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        # Check if custom logic should apply
        if (
            "ass_value_applied" not in base_line
            or not base_line.get("ass_value", 0)
            or not base_line.get("record", False)
            or base_line.get("record", False).move_id.move_type != "in_invoice"
        ):
            return super()._add_tax_details_in_base_line(base_line=base_line, company=company, rounding_method=rounding_method)

        rounding_method = rounding_method or company.tax_calculation_rounding_method
        rate = base_line['rate']
        currency = base_line['currency_id']
        ass_value = base_line['ass_value']  # The taxable base amount
        # price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))

        # taxes_computation_original = base_line['tax_ids']._get_tax_details(
        #     price_unit=price_unit_after_discount,
        #     quantity=base_line['quantity'],
        #     precision_rounding=base_line['currency_id'].rounding,
        #     rounding_method=rounding_method,
        #     product=base_line['product_id'],
        #     special_mode=base_line['special_mode'],
        #     manual_tax_amounts=base_line['manual_tax_amounts'],
        #     filter_tax_function=base_line['filter_tax_function'],
        # )  

        # Compute taxes using ass_value as base price
        taxes_computation = base_line['tax_ids']._get_tax_details(
            price_unit=ass_value,  # <-- use ass_value as base
            quantity=1.0,          # since ass_value is total base
            precision_rounding=currency.rounding,
            rounding_method=rounding_method,
            product=base_line['product_id'],
            special_mode=base_line['special_mode'],
            manual_tax_amounts=base_line['manual_tax_amounts'],
            filter_tax_function=base_line['filter_tax_function'],
        )
        total_excluded = taxes_computation['total_excluded']
        total_included = taxes_computation['total_included']
        total_tax = total_included - total_excluded
        original_base = base_line['price_unit'] * base_line['quantity'] * (1 - (base_line['discount'] / 100.0))

        tax_details = base_line['tax_details'] = {
            'raw_total_excluded_currency': original_base,  # Actual price
            'raw_total_excluded': original_base / rate if rate else 0.0,
            'raw_total_included_currency': total_tax + (original_base),
            'raw_total_included': (total_tax / rate if rate else 0.0) + (original_base) / rate if rate else 0.0,
            'taxes_data': [],
        }

        if rounding_method == 'round_per_line':
            tax_details['raw_total_excluded'] = currency.round(tax_details['raw_total_excluded'])
            tax_details['raw_total_included'] = currency.round(tax_details['raw_total_included'])

        for tax_data in taxes_computation['taxes_data']:
            # tax_amount = tax_data['tax_amount'] / rate if rate else 0.0
            # base_amount = tax_data['base_amount'] / rate if rate else 0.0
            tax_amount = tax_data['tax_amount']
            base_amount = tax_data['base_amount']
            if rounding_method == 'round_per_line':
                tax_amount = currency.round(tax_amount)
                base_amount = currency.round(base_amount)
            tax_details['taxes_data'].append({
                **tax_data,
                'raw_tax_amount_currency': tax_data['tax_amount'],
                'raw_tax_amount': tax_amount,
                'raw_base_amount_currency': tax_data['base_amount'],
                'raw_base_amount': base_amount,
            })

        return tax_details


    # @api.model
    # def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
    #     # Only update price_unit in base_line if ass_value_applied is True
    #     if (
    #         "ass_value_applied" not in base_line
    #         or not base_line.get("ass_value", 0)
    #         or not base_line.get("record", False)
    #         or base_line.get("record", False).move_id.move_type != "in_invoice"
    #     ):
    #         return super(AccountTax, self)._add_tax_details_in_base_line(
    #             base_line=base_line, company=company, rounding_method=rounding_method
    #         )

    #     # OVERRIDE FOR ass_value based TAX Calculations in Vendor Bill
    #     rounding_method = rounding_method or company.tax_calculation_rounding_method
    #     price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
    #     taxes_computation_original = base_line['tax_ids']._get_tax_details(
    #         price_unit=price_unit_after_discount,
    #         quantity=base_line['quantity'],
    #         precision_rounding=base_line['currency_id'].rounding,
    #         rounding_method=rounding_method,
    #         product=base_line['product_id'],
    #         special_mode=base_line['special_mode'],
    #         manual_tax_amounts=base_line['manual_tax_amounts'],
    #         filter_tax_function=base_line['filter_tax_function'],
    #     )        
    #     taxes_computation = base_line['tax_ids']._get_tax_details(
    #         price_unit=base_line['ass_value'],
    #         quantity=1,
    #         precision_rounding=base_line['currency_id'].rounding,
    #         rounding_method=rounding_method,
    #         product=base_line['product_id'],
    #         special_mode=base_line['special_mode'],
    #         manual_tax_amounts=base_line['manual_tax_amounts'],
    #         filter_tax_function=base_line['filter_tax_function'],
    #     )
    #     rate = base_line['rate']
    #     tax_details = base_line['tax_details'] = {
    #         'raw_total_excluded_currency': taxes_computation['total_excluded'],
    #         'raw_total_excluded': taxes_computation['total_excluded'] / rate if rate else 0.0,
    #         'raw_total_included_currency': taxes_computation['total_included'],
    #         'raw_total_included': taxes_computation['total_included'] / rate if rate else 0.0,
    #         'taxes_data': [],
    #     }
    #     raw_total_excluded = price_unit_after_discount * base_line['quantity']
    #     total_tax_amt = sum(map(lambda x: x.get('tax_amount'), taxes_computation['taxes_data']))
    #     raw_total_included = raw_total_excluded + total_tax_amt
    #     if rounding_method == 'round_per_line':
    #         # tax_details['raw_total_excluded'] = company.currency_id.round(tax_details['raw_total_excluded'])
    #         # tax_details['raw_total_included'] = company.currency_id.round(tax_details['raw_total_included'])
    #         tax_details['raw_total_excluded'] = company.currency_id.round(raw_total_excluded)
    #         tax_details['raw_total_included'] = company.currency_id.round(raw_total_included)
    #     for tax_data in taxes_computation['taxes_data']:
    #         tax_amount = tax_data['tax_amount'] / rate if rate else 0.0
    #         # base_amount = tax_data['base_amount'] / rate if rate else 0.0
    #         base_amount = raw_total_excluded / rate if rate else 0.0
    #         if rounding_method == 'round_per_line':
    #             tax_amount = company.currency_id.round(tax_amount)
    #             # base_amount = company.currency_id.round(base_amount)
    #             base_amount = company.currency_id.round(raw_total_excluded)
    #         tax_details['taxes_data'].append({
    #             **tax_data,
    #             'raw_tax_amount_currency': tax_data['tax_amount'],
    #             'raw_tax_amount': tax_amount,
    #             # 'raw_base_amount_currency': tax_data['base_amount'],
    #             'raw_base_amount_currency': tax_data['base_amount'],
    #             # 'raw_base_amount': base_amount,
    #             'raw_base_amount': raw_total_excluded,
    #         })
