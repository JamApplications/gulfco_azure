# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    def _prepare_embedded_views_data(self):
        self.ensure_one()
        res = super(BankRecWidget, self)._prepare_embedded_views_data()

        if self.env.user.has_group('gulfco_account_payment_extended.group_restrict_entries_accounts_journal_filter'):
            amls = res.get('amls', {})
            context = amls.get('context', {})
            dynamic_filters = amls.get('dynamic_filters', [])
            st_line = self.st_line_id

            # == Dynamic Customer/Vendor filter ==
            journal = st_line.journal_id
            context['search_default_journal_id'] = journal.id
            account_ids = set()

            inbound_accounts = journal._get_journal_inbound_outstanding_payment_accounts() - journal.default_account_id
            outbound_accounts = journal._get_journal_outbound_outstanding_payment_accounts() - journal.default_account_id

            # Matching on debit account.
            for account in inbound_accounts:
                account_ids.add(account.id)

            # Matching on credit account.
            for account in outbound_accounts:
                account_ids.add(account.id)

            accounts_matching_filter = {
                'name': 'matching_accounts',
                'description': _("Matching Payments Accounts"),
                'domain': [
                    ('account_id', 'in', tuple(account_ids)),
                ],
                'no_separator': True,
                'is_default': True,
            }
            dynamic_filters.append(accounts_matching_filter)

            # Stringify the domain.
            dynamic_filters[-1]['domain'] = str(dynamic_filters[-1]['domain'])

            res.get('amls', {}).update({
                'dynamic_filters': dynamic_filters,
                'context': context,
            })

        return res

    def _lines_get_exchange_diff_values(self, line):
        if (
            line.source_aml_move_id
            and line.source_aml_move_id.origin_payment_id
            and line.source_aml_move_id.origin_payment_id.is_exchange
            and line.currency_id == line.source_aml_move_id.origin_payment_id.currency_id
        ):
            if line.flag != "new_aml":
                return []
            account, exchange_diff_balance = self._lines_get_account_balance_exchange_diff(line.currency_id, line.balance, line.amount_currency)

            origin_payment_id = line.source_aml_move_id.origin_payment_id
            origin_balance = line.amount_currency * origin_payment_id.rate
            exchange_diff_balance = origin_balance - line.balance

            if line.currency_id.is_zero(exchange_diff_balance):
                return []
            return [{
                'flag': 'exchange_diff',
                'source_aml_id': line.source_aml_id.id,
                'account_id': account.id,
                'date': line.date,
                'name': _("Exchange Difference: %s", line.name),
                'partner_id': line.partner_id.id,
                'currency_id': line.currency_id.id,
                'amount_currency': exchange_diff_balance if line.currency_id == self.company_currency_id else 0.0,
                'balance': exchange_diff_balance,
                'source_amount_currency': line.amount_currency,
                'source_balance': exchange_diff_balance,
            }]
            
        return super(BankRecWidget, self)._lines_get_exchange_diff_values(line=line)
