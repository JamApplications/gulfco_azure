from odoo import fields, models, api, _
from odoo.osv import expression


class AccountTax(models.Model):
    _inherit = "account.tax"
    _rec_names_search = ['name', 'description', 'invoice_label','vat_code']
    
    vat_code = fields.Char(string='Vat Code')
    
    
    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        domain = domain or []
        
        for d in domain:
            if isinstance(d, (list, tuple)) and d[0] == 'name' and d[1] in ('ilike', 'like', '='):
                # Add OR condition for 'vat_code'
                domain = expression.OR([
                    domain or [],
                    [('vat_code', d[1], d[2])],
                ])
                break

        return super(AccountTax, self).search_fetch(domain=domain, field_names=field_names, offset=offset, limit=limit, order=order)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []

        domain += [('vat_code', operator, name)]

        return super(AccountTax, self)._name_search(name=name, domain=domain, operator=operator, limit=limit,order=order)
    
    @api.depends('type_tax_use', 'tax_scope')
    @api.depends_context('append_type_to_tax_name', 'show_vat_code')
    def _compute_display_name(self):
        type_tax_use = dict(self._fields['type_tax_use']._description_selection(self.env))
        for record in self:
            # if 'show_vat_code' not in record._context:
            #     return super(AccountTax, record)._compute_display_name()
            
            name = record.name or ''
            
            # Append (Sale/Purchase/None)
            if record.env.context.get('append_type_to_tax_name'):
                name += ' (%s)' % type_tax_use.get(record.type_tax_use)

            # Append Company Name (multi-company in product.template only)
            if len(record.env.companies) > 1 and record.env.context.get('params', {}).get('model') == 'product.template':
                name += ' (%s)' % record.company_id.display_name

            # Append country code if fiscal country mismatch
            if record.country_id and record.country_id != record.company_id._accessible_branches()[:1].account_fiscal_country_id:
                name += ' (%s)' % record.country_code

            # (Custom) Show only VAT Code if context is enabled
            if record.env.context.get('show_vat_code') and record.vat_code:
                name = f"{record.vat_code}"

            record.display_name = name
            

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Check if we're in the context of showing vat_code
        if self._context.get('show_vat_code'):
            if args is None:
                args = []
            
            # Search in both name and vat_code fields
            domain = args
            if name:
                domain = args + ['|', ('name', operator, name), ('vat_code', operator, name)]
            taxes = self.search(domain, limit=limit)
            
            # Return list with vat_code as display name
            return [(tax.id, tax.vat_code or tax.name) for tax in taxes]
        else:
            return super().name_search(name=name, args=args, operator=operator, limit=limit)