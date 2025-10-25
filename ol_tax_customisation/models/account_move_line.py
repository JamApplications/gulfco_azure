from odoo import fields, models, api, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    tax_vat_code_ids = fields.Many2many(
        comodel_name='account.tax',
        relation="rel_account_move_line_tax_vat_code",
        string="Taxes (Vat Code)",
        compute='_compute_tax_vat_code_ids', 
        inverse='_inverse_tax_vat_code_ids',
        store=True
    )
    
    @api.depends('tax_ids')
    def _compute_tax_vat_code_ids(self):
        for rec in self:
            rec.tax_vat_code_ids = rec.tax_ids
            
    def _inverse_tax_vat_code_ids(self):
        # Write directly to inverse field to force recompute of tax_ids
        for rec in self:
            # Optionally: store the value somewhere or force recompute
            # Dummy write to trigger dependency
            rec.tax_ids = rec.tax_vat_code_ids
            
    @api.depends('product_id', 'product_uom_id', 'tax_vat_code_ids')
    def _compute_tax_ids(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note', 'payment_term') or line.is_imported:
                continue
            
                        # Check if tax_vat_code_ids was changed (prioritize it over computed taxes)
            if line.tax_vat_code_ids and line.tax_vat_code_ids != line.tax_ids:
                # Sync from tax_vat_code_ids to tax_ids
                line.tax_ids = line.tax_vat_code_ids
            else:
                # Original logic - compute taxes from product/account
                # /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
                if line.product_id or (line.display_type != 'discount' and (line.account_id.tax_ids or not line.tax_ids)):
                    computed_taxes = line._get_computed_taxes()
                    line.tax_ids = computed_taxes
                    # Also sync to tax_vat_code_ids
                    line.tax_vat_code_ids = computed_taxes                