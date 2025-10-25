from odoo import models, fields, api, _

class PDCCDCLine(models.TransientModel):
    _name = 'pdc.cdc.line'
    _description = 'PDC/CDC Line Details'

    wizard_id = fields.Many2one('pdc.cdc.wizard', required=True, ondelete='cascade')
    cust_no = fields.Many2one('res.partner', string='Cust No')
    customer_name = fields.Char(string='Customer Name')
    move_date = fields.Date(string='M. Date')
    check_no = fields.Char(string='Check No')
    due_date = fields.Date(string='D. Date')
    pos_rec_no = fields.Char(string='POS Rec. No')
    amount = fields.Float(string='Amount')
    custodian_code = fields.Char(string="Custodian Code")
    cheque_number = fields.Char(string="Cheque Number")
    cheque_status = fields.Char(string="Cheque Status")


class PDCCDCWizard(models.TransientModel):
    _name = 'pdc.cdc.wizard'
    _description = 'PDC/CDC Report Wizard'

    payment_ids = fields.Many2many('account.payment',string="Payments")
    line_ids = fields.One2many('pdc.cdc.line', 'wizard_id', string='PDC/CDC Lines')

    def default_get(self, fields):
        res = super().default_get(fields)
        payments = res.get('payment_ids')
        if payments and payments[0] and len(payments[0]) == 3 and len(payments[0][2]) > 0:
            payment_records = self.env['account.payment'].sudo().browse(payments[0][2])
            lines = []
            for p in payment_records:
                cheque_number = ''
                cheque_status = ''
                if p.payment_mode == 'pdc':
                    cheque_number = p.pdc_ref
                    cheque_status = p.pdc_state
                elif p.payment_mode == 'cdc':
                    cheque_number = p.cdc_ref
                    cheque_status = p.cdc_state
                lines.append((0, 0, {
                    'cust_no': p.partner_id.customer_code,
                    'customer_name': p.partner_id.name,
                    'move_date': p.create_date.date(),
                    'check_no': p.pdc_ref,
                    'due_date': p.due_date,
                    'pos_rec_no': p.name,
                    'amount': p.amount_signed,
                    'custodian_code' : p.custodian_id.custodian_code,
                    'cheque_number':cheque_number,
                    'cheque_status':cheque_status
                }))
            res['line_ids'] = lines
        return res