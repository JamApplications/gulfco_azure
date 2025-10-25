from odoo import _, fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_cdc_receivable_entry = fields.Boolean(string='Is CDC Receivable Entry', readonly=True, store=True)

    @api.model
    def _search_default_journal(self):
        """ handle case default from cdc receivable """
        journal = super()._search_default_journal()
        if self.env.context.get('default_is_cdc_payment'):
            company_id = self._context.get('default_company_id', self.env.company.id)
            domain = [('company_id', '=', company_id), ('is_cdc', '=', True), ('type', '=', 'bank')]
            journal = self.env['account.journal'].search(domain, limit=1)
        if self.env.context.get('default_is_cdc_payable'):
            company_id = self._context.get('default_company_id', self.env.company.id)
            domain = [('company_id', '=', company_id),
                      ('cdc_notes_payable_account_id', '!=', False),
                      ('type', '=', 'bank')]
            journal = self.env['account.journal'].search(domain, limit=1)
        return journal

    def action_open_related_cdc(self):
        """
        open cdc receivable cashed payments
        """
        self.ensure_one()
        cheque_payment = self.cheque_payment_id
        action = {
            'name': _("CDC"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False, 'edit': False},
            'res_id': cheque_payment.id,
            'view_mode': 'form',
        }
        return action


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_cdc_receivable_entry = fields.Boolean(string='Is CDC Receivable Entry', readonly=True, store=True)

