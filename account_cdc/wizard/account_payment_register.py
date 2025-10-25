from odoo import fields, models, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    cdc_bank_id = fields.Many2one(
        comodel_name='res.bank',
        string='Bank Name',
    )
    due_date = fields.Date()
    cheque_owner_id = fields.Many2one(
        comodel_name='res.users',
        default=lambda self: self.env.user,
    )
    cheque_scanning = fields.Binary()
    is_cdc_payment = fields.Boolean(
        related='journal_id.is_cdc'
    )

    can_be_cdc_payable = fields.Boolean(
        compute='_compute_can_be_cdc_payable',
    )
    is_cdc_payable = fields.Boolean(
        string='Is CDC Payable', related='payment_method_line_id.is_cdc_payable'
    )
    cdc_payable_note = fields.Char(
        string='CDC Payable Note',
    )

    beneficiary_id = fields.Many2one(comodel_name="res.company", string='Beneficiary Name', required=False,
                                     default=lambda self: self.env.company,
                                     )
    beneficiary_name = fields.Char(string="Beneficiary Name",default="Gulf Trading and Refrigerating Co LLC")

    cheque_number = fields.Integer()

    @api.onchange('is_cdc_payable')
    def _onchange_is_cdc_payable(self):
        """ reset cdc payable info """
        self.due_date = False
        self.cdc_payable_note = False

    @api.depends('journal_id', 'payment_type')
    def _compute_can_be_cdc_payable(self):
        """ set true / false based on payment_type, partner_type, notes_payable account """
        for record in self:
            can_be_cdc_payable = False
            if record.journal_id and record.journal_id.cdc_notes_payable_account_id and record.payment_type == 'outbound':
                can_be_cdc_payable = True
            record.can_be_cdc_payable = can_be_cdc_payable
            # record.is_cdc_payable = can_be_cdc_payable

    @api.onchange('journal_id')
    def _onchange_journal(self):
        payment_date = self.payment_date
        if self.journal_id and self.journal_id.is_cdc:
            self.communication = False
            self.payment_date = fields.Date.context_today(self)
            self.cheque_owner_id = self.env.user
        else:
            self._compute_communication()
            self.payment_date = payment_date
            self.cdc_bank_id = False
            self.due_date = False
            self.cheque_owner_id = False
            self.cheque_scanning = False

    def _create_payment_vals_from_wizard(self, batch_result):
        """ inherit to add other fields """
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['cdc_bank_id'] = self.cdc_bank_id.id if self.cdc_bank_id else False
        payment_vals['due_date'] = self.due_date
        payment_vals['cheque_owner_id'] = self.cheque_owner_id.id if self.cheque_owner_id else False
        payment_vals['cheque_scanning'] = self.cheque_scanning
        payment_vals['is_cdc_payable'] = self.is_cdc_payable
        payment_vals['due_date'] = self.due_date
        payment_vals['cdc_ref'] = self.cheque_number
        payment_vals['cdc_payable_note'] = self.cdc_payable_note
        if self.payment_type != 'outbound':
            payment_vals['destination_account_id'] = self.journal_id.cdc_check_under_collection_account_id.id if self.journal_id.is_pdc == True else self.partner_id.property_account_receivable_id.id
        # if self.is_cdc_payable:
        #     payment_vals['cdc_payable_state'] = 'registered'
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        """ inherit to add other fields """
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        if 'cdc_bank_id' in batch_result['payment_values']:
            payment_vals['cdc_bank_id'] = batch_result['payment_values']['cdc_bank_id']
        if 'due_date' in batch_result['payment_values']:
            payment_vals['due_date'] = batch_result['payment_values']['due_date']
        if 'cheque_owner_id' in batch_result['payment_values']:
            payment_vals['cheque_owner_id'] = batch_result['payment_values']['cheque_owner_id']
        if 'cheque_scanning' in batch_result['payment_values']:
            payment_vals['cheque_scanning'] = batch_result['payment_values']['cheque_scanning']
        if 'is_cdc_payable' in batch_result['payment_values']:
            payment_vals['is_cdc_payable'] = batch_result['payment_values']['is_cdc_payable']
            # payment_vals['cdc_payable_state'] = 'registered'
        if 'cdc_payable_note' in batch_result['payment_values']:
            payment_vals['cdc_payable_note'] = batch_result['payment_values']['cdc_payable_note']
        return payment_vals
