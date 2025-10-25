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



class AccountPaymentPdcCollect(models.TransientModel):
    _inherit = 'account.payment.pdc.collect'

    def action_collect_pdc(self):
        """ collect pdc receivable """
        if self.payment_ids and len(self.payment_ids) > 1:
            for payment in self.payment_ids:
                payment.action_collect_payment_pdc_receivable(
                collect_date=self.collect_date,
                partner=payment.partner_id,
                original_payment=payment,
            )
        else:
            payment = self.payment_id
            if self.related_payment_ids and self.allow_merge_pdc:
                related_pay_journals = self.related_payment_ids.mapped('journal_id')
                if len(related_pay_journals) > 1:
                    raise ValidationError(_('Related PDC must have same journal'))
                if related_pay_journals != self.payment_id.journal_id:
                    raise ValidationError(_('Related PDC must have journal %s')
                                        % self.payment_id.journal_id.display_name)
                related_pay_state = self.related_payment_ids.mapped('pdc_state')
                if related_pay_state[0] != self.payment_id.pdc_state:
                    raise ValidationError(_('Related PDC must has same '
                                            'status as payment %s')
                                        % self.payment_id.display_name)
                related_deposit_journals = self.related_payment_ids.mapped(
                    'deposit_pdc_id.bank_journal_id')
                if len(related_deposit_journals) > 1:
                    raise ValidationError(
                        _('Related PDC must has same deposit bank'))
                if related_deposit_journals[0] != \
                        self.payment_id.deposit_pdc_id.bank_journal_id:
                    raise ValidationError(
                        _('Related PDC must has same deposit bank %s')
                        % self.payment_id.deposit_pdc_id.bank_journal_id.display_name)
                (payment + self.related_payment_ids). \
                    action_collect_payment_pdc_receivable(
                    collect_date=self.collect_date,
                    partner=self.partner_id,
                    original_payment=self.payment_id,
                    related_payments=self.related_payment_ids,
                )
            else:
                payment.action_collect_payment_pdc_receivable(
                    collect_date=self.collect_date,
                    partner=self.partner_id,
                    original_payment=self.payment_id,
                )