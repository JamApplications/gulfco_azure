from odoo import fields, models, api, _
from collections import defaultdict


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    tax_vat_code_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='rel_sale_order_line_tax_vat_code',
        string="Taxes (Vat Code)",
        compute='_compute_tax_vat_code_ids', store=True, readonly=False,
    )

    @api.depends('tax_id')
    def _compute_tax_vat_code_ids(self):
        for rec in self:
            rec.tax_vat_code_ids = rec.tax_id
            
    @api.depends('product_id', 'company_id', 'tax_vat_code_ids')                
    def _compute_tax_id(self):
        lines_by_company = defaultdict(lambda: self.env['sale.order.line'])
        cached_taxes = {}
        for line in self:
            if line.product_type == 'combo':
                line.tax_id = False
                continue
            lines_by_company[line.company_id] += line
        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                if line.tax_vat_code_ids and line.tax_vat_code_ids != line.tax_id:
                    # Sync from tax_vat_code_ids to tax_id
                    line.tax_id = line.tax_vat_code_ids
                else:
                    taxes = None
                    if line.product_id:
                        taxes = line.product_id.taxes_id._filter_taxes_by_company(company)
                    if not line.product_id or not taxes:
                        # Nothing to map
                        line.tax_id = False
                        continue
                    fiscal_position = line.order_id.fiscal_position_id
                    cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                    cache_key += line._get_custom_compute_tax_cache_key()
                    if cache_key in cached_taxes:
                        result = cached_taxes[cache_key]
                    else:
                        result = fiscal_position.map_tax(taxes)
                        cached_taxes[cache_key] = result
                    # If company_id is set, always filter taxes by the company
                    line.tax_id = result
                    line.tax_vat_code_ids = result
        