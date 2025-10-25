from odoo import fields, models, api, _


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    tax_vat_code_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='rel_purchase_order_line_tax_vat_code',
        string="Taxes (Vat Code)",
        compute='_compute_tax_vat_code_ids', store=True, readonly=False,
        inverse='_inverse_tax_vat_code_ids',
    )

    @api.depends('taxes_id')
    def _compute_tax_vat_code_ids(self):
        for rec in self:
            rec.tax_vat_code_ids = rec.taxes_id
            
    def _inverse_tax_vat_code_ids(self):
        for rec in self:
            rec.taxes_id = rec.tax_vat_code_ids
            
    @api.onchange('tax_vat_code_ids')
    def _onchange_tax_vat_code_ids(self):
        for rec in self:
            if rec.tax_vat_code_ids and rec.tax_vat_code_ids != rec.taxes_id:
                # Sync from tax_vat_code_ids to taxes_id
                rec.taxes_id = rec.tax_vat_code_ids
                
        