from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_cdc = fields.Boolean(
        string='Enable CDC',
    )
    cdc_notes_receivable_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Notes Receivable Account',
        check_company=True,
        domain=lambda self: "[('deprecated', '=', False), ('reconcile', '=', True),('account_type', 'not in', ('asset_receivable', 'liability_payable'))]"
        #('company_id', '=', company_id), removed from domain
    )
    cdc_check_under_collection_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Check Under Collection Account',
        check_company=True,
        domain=lambda self: "[('deprecated', '=', False), ('reconcile', '=', True), ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]"
        # ('company_id', '=', company_id), removed from domain
    )
    write_off_cdc_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Write Off Account',
        check_company=True,
        domain=lambda self: "[('deprecated', '=', False), \
                                     ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]"
        # ('company_id', '=', company_id), removed from domain
    )

    cdc_bounce_receivable_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Bounce Receivable Account',
        check_company=True,
        domain=lambda self: "[('deprecated', '=', False), \
                                         ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]"
    )

    cdc_bounce_beneficiaries_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Bounce Beneficiaries Account',
        check_company=True,
        domain=lambda self: "[('deprecated', '=', False), \
                                         ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]"
    )

    cdc_notes_payable_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Notes Payable Account',
        check_company=True,
        domain=lambda self: "[('deprecated', '=', False), ('reconcile', '=', True), \
                                     ('account_type', '=', 'asset_current')]",
        # ('company_id', '=', company_id), removed from domain
    )
    cdc_payable_under_collection_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Under Collection Payable Account',
        check_company=True,
        domain=lambda self: "[('deprecated', '=', False), ('reconcile', '=', True), \
                                             ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        # ('company_id', '=', company_id), removed from domain
    )


    @api.onchange('type')
    def _compute_refund_sequence(self):
        """ reset is cdc if type is not bank """
        super(AccountJournal, self)._compute_refund_sequence()
        for journal in self:
            if journal.type != 'bank':
                journal.is_cdc = False
                journal.cdc_notes_payable_account_id = False
