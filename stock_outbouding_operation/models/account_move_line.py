from odoo import _, api, fields, models



class AccountMove(models.Model):
    _inherit = 'account.move'
    

    po_number = fields.Char(string="PO Number")
    branch = fields.Char(string='Branch')
    remark_invoice = fields.Char(string="Remark")
    division = fields.Selection([('food','Food'),('non_food','Non-Food'),('mars','Mars')],string="Division")
    receipt_date = fields.Date(string="Invoice Receipt Date",default=fields.Date.context_today,)
    is_invoice_journal = fields.Boolean(related="journal_id.is_invoice_journal",string="IS Invoice Journal",store=True)
    is_debit_note_journal = fields.Boolean(string="Is Debit Note Journal",related="journal_id.is_debit_note_journal",store=True)

    def _get_invoiced_lot_values(self):
        """ Display expire date """
        res = super()._get_invoiced_lot_values()
        for lot in res:
            lot_id = self.env['stock.lot'].browse(lot.get('lot_id'))
            lot['expire_date']= lot_id.expiration_date
        return res

    def action_print_pdf(self):
        result = super().action_print_pdf()
        self.ensure_one()
        return self.env.ref('stock_outbouding_operation.tax_account_invoices').report_action(self.id)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    excise_tax = fields.Char(string="Excise Tax")
    remark_invoice = fields.Char(string="Remark",related="move_id.remark_invoice",store=True)