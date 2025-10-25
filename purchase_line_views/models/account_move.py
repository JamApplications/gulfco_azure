from odoo import fields, models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    excise_stock_picking_id = fields.Many2one(
        'stock.picking',
        string='Excise Stock Picking',
    )

    def _add_custom_purchase_order_lines(self, purchase_order_lines):
        self.ensure_one()
        new_line_ids = self.env['account.move.line']

        for po_line in purchase_order_lines:
            new_line_values = po_line._prepare_account_move_line(self)
            new_line_ids += self.env['account.move.line'].new(new_line_values)

        self.invoice_line_ids += new_line_ids

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    bill_matching_picking_ids = fields.Many2many(comodel_name='stock.picking',relation='stock_picking_bill_matching_rel',string="GRN")
