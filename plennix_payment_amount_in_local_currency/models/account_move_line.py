from odoo import models, _ ,api
from odoo.fields import Command
from collections import defaultdict
from datetime import date


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def action_reconcile(self):
        invoice_ids = self.filtered(lambda s:s.move_type != 'entry').mapped('move_id')
        custom_payment_ids = self.filtered(lambda s: s.payment_id).mapped('payment_id')
        return super(AccountMoveLine, self.with_context(invoice_bill_move_ids=invoice_ids,custom_payment_ids=custom_payment_ids)).action_reconcile()

    def reconcile(self):
        invoice_ids = self.filtered(lambda s:s.move_type != 'entry').mapped('move_id')
        custom_payment_ids = self.filtered(lambda s: s.payment_id).mapped('payment_id')
        res = super(AccountMoveLine, self.with_context(invoice_bill_move_ids=invoice_ids,custom_payment_ids=custom_payment_ids)).reconcile()
        return res

    def _prepare_exchange_difference_move_vals(self, amounts_list, company=None, exchange_date=None, **kwargs):
        """ Prepare values to create later the exchange difference journal entry.
        The exchange difference journal entry is there to fix the debit/credit of lines when the journal items are
        fully reconciled in foreign currency.
        :param amounts_list:    A list of dict, one for each aml.
        :param company:         The company in case there is no aml in self.
        :param exchange_date:   Optional date object providing the date to consider for the exchange difference.
        :return:                A python dictionary containing:
            * move_vals:    A dictionary to be passed to the account.move.create method.
            * to_reconcile: A list of tuple <move_line, sequence> in order to perform the reconciliation after the move
                            creation.
        """
        company = (
            (self.move_id.filtered(lambda m: m.is_invoice(True)) or self.move_id).company_id
            or company
        )[:1]
        if not company:
            return
        journal = company.currency_exchange_journal_id
        expense_exchange_account = company.expense_currency_exchange_account_id
        income_exchange_account = company.income_currency_exchange_account_id
        accounting_exchange_date = journal.with_context(move_date=exchange_date).accounting_date if journal else date.min
        payment_name = ""
        payments = self.env['account.payment']
        for line in self:
            pymt = self.env['account.payment'].search([('memo', '=', line.move_id.name)], limit=1)
            if pymt:
                payments |= pymt
        if payments:
            payment_name = ','.join(payments.mapped('name')) if len(payments) > 1 else payments.name
        if not payments:
            for line in self:
                pymt = self.env['account.payment'].search([('move_id', '=', line.move_id.id)], limit=1)
                if pymt:
                    payments |= pymt
            if payments:
                payment_name = ','.join(payments.mapped('name')) if len(payments) > 1 else payments.name
        if self.env.context.get('custom_payment_ids'):
            payment_name = self.env.context.get('custom_payment_ids')[0].name
        move_vals = {
            'move_type': 'entry',
            'name': '/', # do not trigger the compute name before posting as it will most likely be posted immediately after
            'date': accounting_exchange_date,
            'journal_id': journal.id,
            'line_ids': [],
            'always_tax_exigible': True,
            'ref': payment_name,
        }
        to_reconcile = []

        for line, amounts in zip(self, amounts_list):
            move_vals['date'] = max(move_vals['date'], line.date)

            if 'amount_residual' in amounts:
                amount_residual = amounts['amount_residual']
                amount_residual_currency = 0.0
                if line.currency_id == line.company_id.currency_id:
                    amount_residual_currency = amount_residual
                amount_residual_to_fix = amount_residual
                if line.company_currency_id.is_zero(amount_residual):
                    continue
            elif 'amount_residual_currency' in amounts:
                amount_residual = 0.0
                amount_residual_currency = amounts['amount_residual_currency']
                amount_residual_to_fix = amount_residual_currency
                if line.currency_id.is_zero(amount_residual_currency):
                    continue
            else:
                continue

            if amount_residual_to_fix > 0.0:
                exchange_line_account = expense_exchange_account
            else:
                exchange_line_account = income_exchange_account

            sequence = len(move_vals['line_ids'])

            # aggregated_distribution = defaultdict(float)

            # Find the invoice line that shares the same account and name (or other logic)
            # related_invoice_line = line.move_id.invoice_line_ids.filtered(
            #     lambda l: l.account_id.id == line.account_id.id and l.name == line.name
            # )

            related_lines = line._get_related_invoice_lines(line)

            analytic_distribution = None
            for line_id, dist in related_lines:
                if line_id == line.credit or line.debit:
                    analytic_distribution = dist
                    break
            if self.env.context.get('invoice_bill_move_ids'):
                analytic_distribution = {}
                for inv in self.env.context.get('invoice_bill_move_ids').filtered(lambda m: m.move_type in ('out_invoice', 'in_invoice')):
                    for inv_line in inv.invoice_line_ids:
                        for acc_id, percent in (inv_line.analytic_distribution or {}).items():
                            analytic_distribution[acc_id] = analytic_distribution.get(acc_id, 0.0) + percent
            line_vals = [
                {
                    'name': _('Currency exchange rate difference'),
                    'debit': -amount_residual if amount_residual < 0.0 else 0.0,
                    'credit': amount_residual if amount_residual > 0.0 else 0.0,
                    'amount_currency': -amount_residual_currency,
                    'full_reconcile_id': line.full_reconcile_id.id,
                    'account_id': line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.partner_id.id,
                    'sequence': sequence,
                },
                {
                    'name': _('Currency exchange rate difference'),
                    'debit': amount_residual if amount_residual > 0.0 else 0.0,
                    'credit': -amount_residual if amount_residual < 0.0 else 0.0,
                    'amount_currency': amount_residual_currency,
                    'account_id': exchange_line_account.id,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.partner_id.id,
                    'sequence': sequence + 1,
                    'analytic_distribution': analytic_distribution,
                },
            ]

            if kwargs.get('exchange_analytic_distribution'):
                line_vals[1].update({'analytic_distribution': kwargs['exchange_analytic_distribution']})

            move_vals['line_ids'] += [Command.create(vals) for vals in line_vals]
            to_reconcile.append((line, sequence))

        return {'move_values': move_vals, 'to_reconcile': to_reconcile}






    def _get_related_invoice_lines(self, line):
        move = line.move_id
        line_ids = move.line_ids
        invoice_line_ids = move.invoice_line_ids
        related_lines = []

        for acc_line in line_ids:
            acc_amount = abs(acc_line.amount_currency)

            for invoice_line in invoice_line_ids:
                inv_amount = invoice_line.price_subtotal
                if acc_amount == inv_amount:
                    related_lines.append((inv_amount, invoice_line.analytic_distribution))
                    # related_lines.append(acc_line)
        return related_lines

    # def _prepare_exchange_difference_move_vals(self, amounts_list, company=None, exchange_date=None, **kwargs):
    #     result = super(AccountMoveLine, self)._prepare_exchange_difference_move_vals(
    #         amounts_list,
    #         company=company,
    #         exchange_date=exchange_date,
    #         **kwargs
    #     )
    #
    #     if not result:
    #         return result
    #
    #     move_vals = result.get('move_values')
    #     to_reconcile = result.get('to_reconcile', [])
    #
    #     # --- Get related payment name from reconciled payment
    #     payment_name = None
    #
    #     payment = self.env['account.payment'].search([('memo', '=', self.move_id.name)], limit=1)
    #     if payment:
    #             payment_name = payment.name
    #
    #     if payment:
    #         move_vals['ref'] = payment_name
    #
    #
    #     # --- Add analytic_distribution from source line (line_vals[1])
    #     for (line, sequence) in to_reconcile:
    #         for line_command in move_vals.get('line_ids', []):
    #             print(line_command, "Line Command")
    #             if isinstance(line_command, Command) and line_command[0] == 0:
    #                 line_vals = line_command[2]
    #                 # We only want to update the second line (the one using exchange account)
    #                 if line_vals.get('account_id') in (
    #                     line.company_id.income_currency_exchange_account_id.id,
    #                     line.company_id.expense_currency_exchange_account_id.id
    #                 ):
    #                     if line.analytic_distribution:
    #                         line_vals['analytic_distribution'] = line.analytic_distribution
    #
    #
    #
    #     print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    #     print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    #     print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    #
    #
    #
    #     return {
    #         'move_values': move_vals,
    #         'to_reconcile': to_reconcile,
    #     }
