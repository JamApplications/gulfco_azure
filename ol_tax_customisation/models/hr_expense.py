from odoo import fields, models, api, _


class HrExpense(models.Model):
    _inherit = "hr.expense"
    
    tax_vat_code_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='rel_expense_tax_vat_code',
        string="Taxes (Vat Code)",
        compute='_compute_tax_vat_code_ids', store=True, readonly=False,
        domain="[('type_tax_use', '=', 'purchase')]",
    )
    
    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit', precompute=True, store=True, required=False, readonly=True,
        copy=True,
        digits='Product Price',
    )

    @api.depends('tax_ids')
    def _compute_tax_vat_code_ids(self):
        for rec in self:
            rec.tax_vat_code_ids = rec.tax_ids
            
    @api.depends('product_id', 'company_id', 'tax_vat_code_ids')
    def _compute_tax_ids(self):
        for _expense in self:
            expense = _expense.with_company(_expense.company_id)
            if expense.tax_vat_code_ids and expense.tax_vat_code_ids != expense.tax_ids:
                # Sync from tax_vat_code_ids to tax_ids
                expense.tax_ids = expense.tax_vat_code_ids
            else:
                # Original logic
                # taxes only from the same company
                taxes = expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id))
                expense.tax_ids = taxes
                expense.tax_vat_code_ids = taxes
        