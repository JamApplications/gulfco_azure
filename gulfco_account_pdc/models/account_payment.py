# -*- coding: utf-8 -*-
#############################################################################
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models, api, _
import ast
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _create_payment_vals_from_wizard(self, batch_result):
        """ inherit to add other fields """
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.payment_type != 'outbound':
            payment_vals['destination_account_id'] = self.journal_id.pdc_check_under_collection_account_id.id if self.journal_id.is_pdc == True else self.partner_id.property_account_receivable_id.id
        return payment_vals


class AccountDepositPdc(models.Model):
    _inherit = 'account.deposit.pdc'

    def action_deposit(self):
        """ create journal entry for deposit """
        print("PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP")
        for record in self:
            if not record.payment_ids:
                raise ValidationError(_('Please choose cheque to deposit'))
            record.payment_deposit_ids = record.mapped('payment_ids')
            company_currency = record.bank_journal_id.company_id.currency_id
            for payment in record.payment_ids.filtered(lambda line: line.state == 'in_process'):
                payment.mark_as_sent()
                amount_currency = payment._get_payment_amount()
                currency = company_currency
                if payment.currency_id != company_currency:
                    amount_currency = payment._get_payment_amount(company_currency=False)
                    currency = payment.currency_id
                payment_company_amount = payment._get_payment_amount()
                liquidity_analytic_tag_ids = False
                if hasattr(payment, 'liquidity_analytic_tag_ids'):
                    liquidity_analytic_tag_ids = payment.liquidity_analytic_tag_ids.ids

                move = payment._create_pdc_journal_entry(
                    journal=payment.journal_id,
                    partner=payment.partner_id,
                    label='Cheque Deposit %s - %s' % (payment.memo, payment.name),
                    amount=payment_company_amount,
                    debit_account=payment.payment_method_line_id.payment_account_id,
                    credit_account=payment.journal_id.pdc_notes_receivable_account_id,
                    amount_currency=amount_currency,
                    currency=currency,
                    ref=payment.name + ' ' + record.name,
                    debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    cheque_payment_type='deposit',
                )
                payment.deposit_move_id = move.id
            record.state = 'deposit'
            record.payment_ids.pdc_state = 'deposit'


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # common functions pdc receivable and payable
    def _create_pdc_bounce_journal_entry(self, journal, partner, label, amount, debit_account, credit_account, bounce_debit, bounce_credit,
                                  amount_currency=False,
                                  currency=False, ref='',
                                  date=fields.Date.today(),
                                  debit_analytic_tag_ids=False,
                                  credit_analytic_tag_ids=False,
                                  cheque_payment_type=False):
        """ generic function to create journal entry """
        self.ensure_one()
        move = self.env['account.move'].create({
            'date': date,
            'journal_id': journal.id,
            'cheque_payment_id': self.id,
            'ref': ref,
            'partner_id': partner.id,
            'cheque_payment_type': cheque_payment_type,
            'line_ids': [
                (0, 0, {
                    'name': label,
                    'partner_id': partner.id,
                    'account_id': debit_account.id,
                    'debit': amount,
                    'currency_id': currency.id if currency else False,
                    'amount_currency': amount_currency if amount_currency else 0,
                    # 'analytic_tag_ids': [(6, 0, debit_analytic_tag_ids)] if debit_analytic_tag_ids else False,
                }),
                (0, 0, {
                    'name': label,
                    'partner_id': partner.id,
                    'account_id': credit_account.id,
                    'credit': amount,
                    'currency_id': currency.id if currency else False,
                    'amount_currency': -amount_currency if amount_currency else 0,
                    'is_pdc_receivable_entry': True,
                    # 'analytic_tag_ids': [(6, 0, credit_analytic_tag_ids)] if credit_analytic_tag_ids else False,
                }),

                (0, 0, {
                    'name': label,
                    'partner_id': partner.id,
                    'account_id': bounce_debit.id,
                    'debit': amount,
                    'currency_id': currency.id if currency else False,
                    'amount_currency': amount_currency if amount_currency else 0,
                    # 'analytic_tag_ids': [(6, 0, debit_analytic_tag_ids)] if debit_analytic_tag_ids else False,
                }),
                (0, 0, {
                    'name': label,
                    'partner_id': partner.id,
                    'account_id': bounce_credit.id,
                    'credit': amount,
                    'currency_id': currency.id if currency else False,
                    'amount_currency': -amount_currency if amount_currency else 0,
                    'is_pdc_receivable_entry': True,
                    # 'analytic_tag_ids': [(6, 0, credit_analytic_tag_ids)] if credit_analytic_tag_ids else False,
                }),
            ],
        })
        move.action_post()
        return move

    def action_pdc_receivable_bounced(self, bounce_date=fields.Date.today(),
                                      partner=False, original_payment=False,
                                      related_payments=False):
        """ mark bounced and unsent cheque"""
        for record in self:
            record.unmark_as_sent()
            company_currency = record.journal_id.company_id.currency_id
            amount_currency = abs(record._get_payment_amount())
            currency = company_currency
            if record.currency_id != company_currency:
                amount_currency = record._get_payment_amount(company_currency=False)
                currency = record.currency_id
            liquidity_analytic_tag_ids = False
            if hasattr(record, 'liquidity_analytic_tag_ids'):
                liquidity_analytic_tag_ids = record.liquidity_analytic_tag_ids.ids
  
            payment_method = original_payment.payment_method_line_id
            if not payment_method.payment_account_id:
                raise ValidationError(_("You need to configure the outstanding account in the journal!"))
            if not original_payment.journal_id.pdc_bounce_receivable_account_id or not original_payment.journal_id.pdc_bounce_beneficiaries_account_id:
                raise ValidationError(_("You need to configure the bounce account in the journal!"))

            move = record._create_pdc_bounce_journal_entry(
                journal=record.journal_id,
                partner=record.partner_id,
                label='Cheque Bounced %s - %s' % (record.memo, record.name),
                amount=record._get_payment_amount(),
                debit_account=original_payment.partner_id.property_account_receivable_id,
                credit_account=payment_method.payment_account_id,
                bounce_debit=original_payment.journal_id.pdc_bounce_receivable_account_id,
                bounce_credit=original_payment.journal_id.pdc_bounce_beneficiaries_account_id,
                amount_currency=amount_currency,
                currency=currency,
                ref=record.name,
                debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                cheque_payment_type='bounced',
                date=bounce_date,
            )
            record.sudo().bounced_move_id = move.id

            invoice = self.env['account.move'].search([('origin_payment_id', '=', original_payment.id)])
            if invoice:
                invoice.line_ids.remove_move_reconcile()


            """
            - keep history of reconciled move.
            - hasattr is used as we do not need to add dependency 
            between modules.
            """
            if hasattr(record, '_save_reconciled_invoice_matching'):
                record._save_reconciled_invoice_matching()
            # unreconcile invoice from payment to set invoice status to unpaid
            payment_receivable_move_lines = record.move_id.line_ids.filtered(
                lambda line: line.account_id == record.destination_account_id)
            if record.reconciled_invoice_ids:
                payment_receivable_move_lines.remove_move_reconcile()
            bounce_receivable_move_line = move.line_ids.filtered(
                lambda line: line.account_id == record.destination_account_id)
            (payment_receivable_move_lines +
             bounce_receivable_move_line).reconcile()
            if hasattr(record, 'invoice_matching_ids') \
                    and any(not rec.matched_partial_reconcile_ids
                            and not rec.invoice_matching_ids for rec in
                            self):
                record.invoice_matching_ids._compute_invoice_amount()

        # generate 2 payments inbound and outbound
        if record.pdc_state == 'deposit':
            payment_in = self._create_inbound_payment(
                partner, original_payment, related_payments, bounce_date)
        else:
            # take collection payments and remove reconcile with deposit
            payment_in = original_payment.collect_payment_id
            if related_payments:
                payment_in |= related_payments.mapped('collect_payment_id')
            if payment_in:
                payment_in.mapped('move_id.line_ids').remove_move_reconcile()
        payment_out = self._create_outbound_payment(
            partner, original_payment, related_payments, bounce_date)
        if related_payments:
            related_payments.write({
                'related_move_ids': [(6, 0, (payment_in.mapped('move_id') |
                                             payment_out.move_id).ids)]
            })
        if original_payment.journal_id.pdc_check_under_collection_account_id and \
                original_payment.journal_id.pdc_check_under_collection_account_id.reconcile:
            if payment_in and payment_out:
                # @formatter:off
                payment_in_line = payment_in.move_id.line_ids.filtered(
                    lambda line: line.account_id == original_payment.journal_id.pdc_check_under_collection_account_id
                                 and not line.full_reconcile_id and line.balance
                                 and line.account_id.reconcile)
                payment_out_line = payment_out.move_id.line_ids.filtered(
                    lambda line: line.account_id == original_payment.journal_id.pdc_check_under_collection_account_id
                                 and not line.full_reconcile_id and line.balance
                                 and line.account_id.reconcile)
                # @formatter:on
                if payment_in_line and payment_out_line:
                    (payment_in_line + payment_out_line).reconcile()
        self.sudo().write({'pdc_state': 'bounced','state': 'in_process'})
        template = self.env.ref('gulfco_account_pdc.email_template_pdc_bounce')
        template.send_mail(self.id, force_send=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Success"),
                'message': _("Email notification sent to %s") % self.partner_id.name,
                'type': 'success',
                'sticky': False,
            }
        }




    def action_collect_payment_pdc_receivable(self,
                                              collect_date=fields.Date.today(),
                                              partner=False,
                                              original_payment=False,
                                              related_payments=False):
        """ register payment in bank and mark cheque status is collected"""
        from_bounce_state = False
        if original_payment.pdc_state in ['deposit', 'bounced','collected','registered']:

            liquidity_analytic_tag_ids = False
            if hasattr(original_payment, 'liquidity_analytic_tag_ids'):
                liquidity_analytic_tag_ids = original_payment.liquidity_analytic_tag_ids.ids
            move = original_payment._create_pdc_journal_entry(
                journal=original_payment.journal_id,
                partner=partner,
                label='Collect PDC ' + original_payment.name if original_payment.name else '' + ' - ' + original_payment.memo if original_payment.memo else '',
                amount_currency = original_payment._get_payment_amount(company_currency=False),
                debit_account=original_payment.journal_id.pdc_check_under_collection_account_id,
                credit_account=original_payment.partner_id.property_account_receivable_id,
                amount=original_payment._get_payment_amount(),
                currency=original_payment.journal_id.company_id.currency_id,
                ref=original_payment.name,
                debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                cheque_payment_type='collected',
            )
            if original_payment.payment_type != 'inbound':
                original_payment.pdc_state = 'collected'
            if original_payment.payment_type == 'inbound':
                original_payment.is_pdc_collected = True
            """
            if move:
                # Reconcile payment with invoice
                for inv in original_payment.invoice_ids:
                    account = inv.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')).account_id
                    lines_to_reconcile = (inv.line_ids + move.line_ids).filtered(
                        lambda line: line.account_id == account and not line.reconciled
                    )
                    if lines_to_reconcile:
                        lines_to_reconcile.reconcile()
            """

    def action_recollect_payment_pdc_receivable(self,
                                              collect_date=fields.Date.today(),
                                              partner=False,
                                              original_payment=False,
                                              related_payments=False):
        """ register payment in bank and mark cheque status is collected"""
        from_bounce_state = False
        if original_payment.pdc_state in ['deposit', 'bounced']:

            liquidity_analytic_tag_ids = False
            if hasattr(original_payment, 'liquidity_analytic_tag_ids'):
                liquidity_analytic_tag_ids = original_payment.liquidity_analytic_tag_ids.ids

            payment_method = self.env['account.payment.method.line'].search(
                [('journal_id', '=', original_payment.deposit_move_id.journal_id.id),
                 ('payment_method_id', '=', self.env['account.payment.method'].search([('code', '=', 'manual'),
                                                                                       ('payment_type', '=',
                                                                                        'inbound')]).id)])
            if not original_payment.payment_method_line_id.payment_account_id:
                raise ValidationError(_("You need to configure the outstanding account in the journal!"))

            move = original_payment._create_pdc_journal_entry(
                journal=original_payment.journal_id,
                partner=partner,
                label='ReCollect PDC ' + original_payment.name if original_payment.name else '' + ' - ' + original_payment.memo if original_payment.memo else '',
                amount_currency=original_payment._get_payment_amount(company_currency=False),
                debit_account=payment_method[0].payment_account_id,
                credit_account=original_payment.partner_id.property_account_receivable_id,
                amount=original_payment._get_payment_amount(),
                currency=original_payment.journal_id.company_id.currency_id,
                ref=original_payment.name,
                debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                cheque_payment_type='collected',
            )
            original_payment.pdc_state = 'collected'
            """
            if move:
                # Reconcile payment with invoice
                for inv in original_payment.invoice_ids:
                    account = inv.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')).account_id
                    lines_to_reconcile = (inv.line_ids + move.line_ids).filtered(
                        lambda line: line.account_id == account and not line.reconciled
                    )
                    if lines_to_reconcile:
                        lines_to_reconcile.reconcile()
            """

    def action_collect_payment_cdc_receivable(self,
                                              collect_date=fields.Date.today(),
                                              partner=False,
                                              original_payment=False,
                                              related_payments=False):
        """ register payment in bank and mark cheque status is collected"""
        from_bounce_state = False
        if original_payment.cdc_state in ['deposit', 'bounced']:
            payment_method = self.env['account.payment.method.line'].search([('journal_id','=',original_payment.deposit_move_id.journal_id.id),
                                                                             ('payment_method_id', '=', self.env['account.payment.method'].search([('code','=', 'manual'),
                                                                                                                                                ('payment_type','=', 'inbound')]).id)])
            if not original_payment.payment_method_line_id.payment_account_id:
                raise ValidationError(_("You need to configure the outstanding account in the journal!"))
            liquidity_analytic_tag_ids = False
            if hasattr(original_payment, 'liquidity_analytic_tag_ids'):
                liquidity_analytic_tag_ids = original_payment.liquidity_analytic_tag_ids.ids
            move = original_payment._create_cdc_journal_entry(
                journal=original_payment.journal_id,
                partner=partner,
                label='Collect CDC ' + original_payment.name if original_payment.name else '' + ' - ' + original_payment.memo if original_payment.memo else '',
                amount_currency = original_payment._get_payment_amount(company_currency=False),
                debit_account=payment_method[0].payment_account_id,
                credit_account=original_payment.journal_id.cdc_check_under_collection_account_id,
                amount=original_payment._get_payment_amount(),
                currency=original_payment.journal_id.company_id.currency_id,
                ref=original_payment.name,
                debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                cheque_payment_type='collected',
            )
            original_payment.cdc_state = 'collected'
            """
            if move:
                # Reconcile payment with invoice
                for inv in original_payment.invoice_ids:
                    account = inv.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')).account_id
                    lines_to_reconcile = (inv.line_ids + move.line_ids).filtered(
                        lambda line: line.account_id == account and not line.reconciled
                    )
                    if lines_to_reconcile:
                        lines_to_reconcile.reconcile()
            """

    def auto_collect_pdc_pdc_receivable(self):
        today = date.today()
        payments = self.search([
            ('payment_mode', '=', 'pdc'),
            ('state', '=', 'in_process'),
            ('pdc_state', '=', 'deposit'),
            ('payment_type', '=', 'inbound'),
            ('due_date', '=', today),
            ('is_pdc_payable', '=', False),
        ])
        for payment in payments:
            try:
                ctx = {
                    'active_id': payment.id,
                    'active_ids': [payment.id],
                    'active_model':'account.payment',
                    'default_collect_date': today,
                }
                default_vals = self.env['account.payment.pdc.collect'].with_context(ctx).default_get(
                    ['collect_date', 'payment_id'])
                default_vals['collect_date'] = today  # Force today's date
                wizard = self.env['account.payment.pdc.collect'].with_context(ctx).create(default_vals)
                wizard.action_collect_pdc()
                _logger.info(f"Auto-collected PDC for Payment ID {payment.id}")

            except Exception as e:
                _logger.exception(f"Failed to auto-collect PDC for Payment ID {payment.id}: {e}")



class AccountMove(models.Model):
    _inherit = "account.move"


    def _reconcile_move_with_payment_due_date(self):
        moves = self.search([
            ('state', '=', 'posted'),
            ('date', '<=', fields.Date.context_today(self)),
            ('move_type', '=', 'out_invoice')], limit=100)
        payment_list = []
        for record in moves:
            if record.matched_payment_ids:
                for payment in record.matched_payment_ids:
                    payment_list.append(payment.id)

            if payment_list:
                for jv in self.search([('cheque_payment_id', 'in', payment_list),('cheque_payment_type', '=', 'collected')]):
                    if jv.state == 'posted':
                        account = record.line_ids.filtered(
                            lambda line: line.account_id.account_type in ('asset_receivable',
                                                                          'liability_payable')).account_id
                        lines_to_reconcile = (record.line_ids + jv.line_ids).filtered(
                            lambda line: line.account_id == account and not line.reconciled
                        )
                        if lines_to_reconcile:
                            if jv.cheque_payment_id.due_date <= fields.date.today():
                                lines_to_reconcile.reconcile()


    # def action_post(self):
    #     '''Code removed as credit limit used in cash transaction limit app'''
    #     result = super(AccountMove, self).action_post()
    #     for record in self:
    #         if record.partner_id.use_partner_credit_limit and record.partner_id.credit_limit < record.partner_id.credit:
    #             raise ValidationError(_("You cannot exceed credit limit for this customer!"))
    #     return result