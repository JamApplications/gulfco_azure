from odoo import _, fields, models, api
from lxml import etree

class AccountMove(models.Model):
    _inherit = 'account.move'

    cheque_payment_id = fields.Many2one(
        comodel_name='account.payment',
        copy=False,
    )

    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=False, index=True, copy=False,
                               default=fields.Date.context_today)

    is_pdc_receivable_entry = fields.Boolean(string='Is PDC Receivable Entry', readonly=True, store=True)

    cheque_payment_type = fields.Selection(
        selection=[('bounced', 'Bounced'),
                   ('deposit', 'Deposit'),
                   ('collected', 'Collected'),
                   ('delivered', 'Delivered'),
                   ('returned', 'Returned'),
                   ('cleared', 'Cleared'),
                   ('writeoff', 'Write-off'),
                   ('recheque', 'Recheque'),
                   ('bounced_in', 'Bounced In Bank'),
                   ('bounced_out', 'Bounced Out Bank'),
                   ('cashed', 'Cashed'),
                   ('recycled', 'Recycled'),
                   ('collection_fees', 'Collection Fees'),
                   ],
    )

    @api.model
    def _search_default_journal(self):
        """ handle case default from pdc receivable """
        journal = super()._search_default_journal()
        if self.env.context.get('default_is_pdc_payment'):
            company_id = self._context.get('default_company_id', self.env.company.id)
            domain = [('company_id', '=', company_id), ('is_pdc', '=', True), ('type', '=', 'bank')]
            journal = self.env['account.journal'].search(domain, limit=1)
        if self.env.context.get('default_is_pdc_payable'):
            company_id = self._context.get('default_company_id', self.env.company.id)
            domain = [('company_id', '=', company_id),
                      ('pdc_notes_payable_account_id', '!=', False),
                      ('type', '=', 'bank')]
            journal = self.env['account.journal'].search(domain, limit=1)
        return journal

    def action_open_related_pdc(self):
        """
        open pdc receivable cashed payments
        """
        self.ensure_one()
        cheque_payment = self.cheque_payment_id
        action = {
            'name': _("PDC"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False, 'edit': False},
            'res_id': cheque_payment.id,
            'view_mode': 'form',
        }
        return action


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_pdc_receivable_entry = fields.Boolean(string='Is PDC Receivable Entry', readonly=True, store=True)


    def reconcile(self):
        """
        inherit to unmark is_pdc_receivable_entry
        """
        res = super(AccountMoveLine, self).reconcile()
        # if res.get('partials'):
            # reconciled = res.get('partials')
            # for move in res:
            #     for line in move.debit_move_id.filtered(lambda m:m.move_id.cheque_payment_id):
            #         pdc = line.move_id.cheque_payment_id
            #         if pdc:
            #             pdc.move_id.line_ids.is_pdc_receivable_entry = False

        return res

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)

        if (
            view_type == "search"
            and view.model == "account.move.line"
            and view.xml_id == "account_accountant.view_account_move_line_reconcile_search"
        ):
            # Get all check_under_collection_account_ids from PDC journals
            pdc_journals = self.env["account.journal"].search(
                [("type", "=", "bank"), ("is_pdc", "=", True)]
            )
            pdc_account_ids = pdc_journals.pdc_check_under_collection_account_id.ids

            if pdc_account_ids:
                # Create a new filter node dynamically
                filter_node = etree.Element(
                    "filter",
                    {
                        "string": "PDC Accounts",
                        "name": "pdc_accounts",
                        "domain": str([("account_id", "in", pdc_account_ids)]),
                        "help": "Journal items from PDC check under collection accounts",
                    },
                )

                # Insert after "Receivable" filter
                for receivable_node in arch.xpath("//filter[@name='trade_receivable']"):
                    receivable_node.addnext(filter_node)

        return arch, view
