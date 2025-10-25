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
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from collections import defaultdict


class AccountAsset(models.Model):
    _inherit = "account.asset"

    code = fields.Char(string="Asset Code", required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    model_code = fields.Char(string="Asset Model Code")
    from_analytic_distribution = fields.Json(string="From Analytic Distribution")
    to_analytic_distribution = fields.Json(string="To Analytic Distribution")
    transfer_date = fields.Date(string="Transfer Date")
    transfer_memo = fields.Text(string="Note")
    transfer = fields.Boolean(string="Transfer")
    old_ref = fields.Char(string="Old Ref")
    reclassification_move_ids = fields.Many2many('account.move','account_move_reclassification_rel' ,'asset_id', 'reclassification_move_id',
                                                 string='Reclassification Move ids')

    def action_open_reclassification_entries(self):
        return {
            'name': _('Reclassification Journal Entries'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'search_view_id': [self.env.ref('account.view_account_move_filter').id, 'search'],
            'views': [(self.env.ref('account.view_move_tree').id, 'list'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.reclassification_move_ids.ids)],
            'context': dict(self._context, create=False),
        }

    @api.model
    def create(self, vals):
        if vals.get('model_id'):
            category = self.env['account.asset'].browse(vals['model_id'])
            category_code = category.model_code if category.model_code else '00'  # Default if no code

            # Define a unique sequence code for each category
            seq_code = f"account.asset.{category_code}"

            # Search for an existing sequence for the category
            seq = self.env['ir.sequence'].search([('code', '=', seq_code)], limit=1)

            # If the sequence does not exist, create a new one
            if not seq:
                seq = self.env['ir.sequence'].create({
                    'name': f'Sequence for {category.name}',
                    'code': seq_code,
                    'prefix': f'{category_code}-',
                    'padding': 6,
                    'number_next': 1,  # Ensures it starts at 1
                    'number_increment': 1,
                })

            # Generate the next number using the category-specific sequence
            vals['code'] = seq.next_by_id()

        return super(AccountAsset, self).create(vals)

    def validate(self):
        res = super(AccountAsset, self).validate()
        for asset in self:
            new_account_id = asset.model_id.account_asset_id
            new_journal_id = asset.model_id.journal_id
            bill_lines = asset.original_move_line_ids.filtered(
                lambda l: l.move_id.move_type == 'in_invoice')
            if not bill_lines:
                continue
            reclass_credit_lines = []
            total_debit = 0.0
            # combined_analytic = defaultdict(float)
            for line in bill_lines:
                if new_account_id and line.account_id.id != new_account_id.id:
                    reclass_credit_lines.append((0, 0, {
                        'name': 'Reclassification of the Asset Model',
                        'account_id': line.account_id.id,
                        'credit': line.debit,
                        'debit': 0.0,
                        'partner_id': line.partner_id.id,
                        'analytic_distribution': line.analytic_distribution
                    }))
                    total_debit += line.debit
                    # if line.analytic_distribution:
                    #     for acc_id, value in line.analytic_distribution.items():
                    #         combined_analytic[acc_id] += value  # combine same accounts
            if new_journal_id and reclass_credit_lines and total_debit > 0.0:
                reclass_debit_line = (0, 0, {
                    'name': 'Reclassification of the Asset Model',
                    'account_id': new_account_id.id,
                    'credit': 0.0,
                    'debit': total_debit,
                    'partner_id': False,
                    'analytic_distribution': asset.analytic_distribution,
                    # 'analytic_distribution': dict(combined_analytic),
                })
                move_vals = {
                    'journal_id': new_journal_id.id,
                    'date': fields.Date.context_today(self),
                    'ref': f'Reclassification of Asset Model - {asset.name}',
                    'line_ids': reclass_credit_lines + [reclass_debit_line],
                }
                new_move_id = self.env['account.move'].create(move_vals)
                if new_move_id:
                    new_move_id.action_post()
                    asset.write({'reclassification_move_ids': [(4, new_move_id.id)]})
        return res

    def set_to_dispose(self, invoice_line_ids, date=None, message=None):
        disposal_date = date or fields.Date.today()
        if disposal_date <= self.company_id._get_user_fiscal_lock_date(self.journal_id):
            raise UserError(_("You cannot dispose of an asset before the lock date."))
        if invoice_line_ids and self.children_ids.filtered(
                lambda a: a.state in ('draft', 'open') or a.value_residual > 0):
            raise UserError(
                _("You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."))
        full_asset = self + self.children_ids
        move_ids = full_asset._get_disposal_moves([invoice_line_ids] * len(full_asset), disposal_date)
        for asset in full_asset:
            asset.message_post(body=
                               _('Asset sold. %s', message if message else "")
                               if invoice_line_ids else
                               _('Asset disposed. %s', message if message else "")
                               )
        selling_price = abs(sum(invoice_line.balance for invoice_line in invoice_line_ids))
        self.net_gain_on_sale = self.currency_id.round(selling_price - self.book_value)

        full_asset.write({'state': 'close'})

    def action_open_transferred_asset_ids(self):
        return self.env['account.asset.transfer'].search([('asset_id', '=', self.id)]).open_transferred_asset(
            ['list', 'form'])

    def dispose_asset(self):
        """ Returns an action opening the asset modification wizard.
        """
        # self.ensure_one()
        new_wizard = self.env['asset.modify'].create({
            'asset_id': self[0].id,
            'asset_ids': self.ids,
            'modify_action': 'resume' if self.env.context.get('resume_after_pause') else 'dispose',
        })
        return {
            'name': _('Modify Asset'),
            'view_mode': 'form',
            'res_model': 'asset.modify',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }

    def pause_asset(self):
        """ Returns an action opening the asset modification wizard.
                """
        self.ensure_one()
        new_wizard = self.env['asset.modify'].create({
            'asset_id': self.id,
            'asset_ids': self.ids,
            'modify_action': 'resume' if self.env.context.get('resume_after_pause') else 'dispose',
        })
        return {
            'name': _('Modify Asset'),
            'view_mode': 'form',
            'res_model': 'asset.modify',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }
