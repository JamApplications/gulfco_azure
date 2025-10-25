from odoo import models, fields

class TotalCostBreakdownWizard(models.TransientModel):
    _name = 'total.cost.breakdown.wizard'
    _description = 'Total Cost (AED) Breakdown'

    excise_duty = fields.Monetary(string='Excise Duty')
    landed_cost_total = fields.Monetary(string='Landed Cost Total')
    total_cost_aed = fields.Monetary(string="Total Cost AED")
    po_cost_local = fields.Monetary(string='PO Cost (Local)')
    hdr_charges = fields.Monetary(string='HDR Comp Charges')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
