from odoo import models, fields,tools

class StockLandedCostSummeryLine(models.Model):
    _name = 'stock.landed.cost.summery.line'
    _description = 'Stock Landed Cost Summary Line'

    landed_cost_id = fields.Many2one('stock.landed.cost', string="Landed Cost", ondelete='cascade')
    product_id = fields.Many2one('product.product',string="Item")
    item_code = fields.Char(string='Item Code',related="product_id.default_code",store=True)
    trx_qty = fields.Float(string='Transaction Qty')
    unit_price = fields.Float(string='Unit Price')
    currency_code = fields.Char(string='Currency')
    po_cost = fields.Float(string='PO Cost')
    po_cost_local = fields.Float(string='PO Cost Local Currency')
    unit_excise_cost =  fields.Float(string="Unit Excise Cost")
    excise_duty = fields.Float(string='Excise Duty AED')
    hdr_charges = fields.Float(string='Hdr Comp Charges')
    landed_cost_per_unit = fields.Float(string='Landed Cost Per Unit')
    total_cost_aed = fields.Float(string="Total Cost AED")
    
    
    def action_view_total_cost_breakdown(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Total Cost (AED) Breakdown',
            'view_mode': 'form',
            'res_model': 'total.cost.breakdown.wizard',
            'target': 'new',
            'context': {
                'default_excise_duty': self.excise_duty,
                'default_landed_cost_total': self.landed_cost_id.amount_total,
                'default_total_cost_aed': self.total_cost_aed,
                'default_po_cost_local': self.po_cost_local,
                'default_hdr_charges': self.hdr_charges,
            }
        }