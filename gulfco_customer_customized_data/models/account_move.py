from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    customer_code = fields.Char(related='partner_id.customer_code', string='Customer Code', store=True, readonly=True)
    
    show_goods_warning_no_so = fields.Boolean(compute="_compute_goods_invoice_warnings")
    show_goods_warning_debit_journal = fields.Boolean(compute="_compute_goods_invoice_warnings")
    voucher_number = fields.Char(string="Voucher Number", copy=False)

    @api.depends('invoice_line_ids.product_id', 'invoice_line_ids', 'journal_id', 'move_type')
    def _compute_goods_invoice_warnings(self):
        for move in self:
            goods_lines = [
                line for line in move.invoice_line_ids
                if line.product_id
                and line.product_id.type == 'consu'
                and line.product_id.is_storable
            ]
            has_sale_order = any(line.sale_line_ids for line in move.invoice_line_ids)

            move.show_goods_warning_no_so = (
                bool(goods_lines)
                and move.move_type == 'out_invoice'
                and not has_sale_order
            )

            move.show_goods_warning_debit_journal = (
                bool(goods_lines)
                and move.move_type == 'out_invoice'
                and move.journal_id
                and move.journal_id.type == 'sale'
                and move.journal_id.code.lower() in ['dn', 'debit']
            )

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_block_goods(self):
        for line in self:
            move = line.move_id
            product = line.product_id
            has_sale_order = any(line.sale_line_ids for line in move.invoice_line_ids)
            if not product or not move:
                continue
            is_goods = product.type == 'consu'
            is_tracked = product.is_storable
            if is_goods and is_tracked:
                if move.move_type in ['out_invoice', 'out_refund'] and not has_sale_order:
                    raise UserError(
                        _('Please note that the sale or return of goods items must follow a Sales Order (SO).'))

                elif move.move_type in ['in_invoice', 'in_refund'] and not line.purchase_line_id:
                    raise UserError(
                        _('Please note that the purchases or refunds of goods items must follow a Purchase Order (PO).'))