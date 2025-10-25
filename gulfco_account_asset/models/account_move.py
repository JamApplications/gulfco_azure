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
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.tools import (
    create_index,
    date_utils,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    index_exists,
    OrderedSet,
    SQL,
)
from odoo.tools.mail import email_re, email_split, is_html_empty



class AccountMove(models.Model):
    _inherit = "account.move"

    revaluate = fields.Boolean(string="Revaluate Asset", help="Define whether the "
                                              "bill is for asset revaluate")
    revaluate_asset_id = fields.Many2one('account.asset', string="Asset")

    def action_open_gross_increase_asset_ids(self):
        return self.revaluate_asset_id.open_asset(['list', 'form'])


    def _post(self, soft=True):
        # OVERRIDE
        posted = super()._post(soft)
        for move in posted:
            if not move.revaluate:
                print(move, "0000000000000000000000000000000000000000000000000000000000000000000000")
                # log the post of a depreciation
                posted._log_depreciation_asset()

                # look for any asset to create, in case we just posted a bill on an account
                # configured to automatically create assets
                posted.sudo()._auto_create_asset()
            else:
                print(move,"11111111111111111111111111111111111111111111111111111111111111111111111")
                revaluation_amount = 0
                for move_line in move.line_ids:
                    print(move_line.account_id,
                          move_line.account_id.can_create_asset,
                          move_line.account_id.create_asset,
                          (move_line.currency_id or move.currency_id).is_zero(move_line.price_total),
                          move_line.asset_ids,
                          move_line.tax_line_id,
                          move_line.price_total,
                          move.move_type,
                          move_line.account_id.internal_group, "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC")
                    if (
                            move_line.account_id
                            and (move_line.account_id.can_create_asset)
                            and move_line.account_id.create_asset != "no"
                            and not (move_line.currency_id or move.currency_id).is_zero(move_line.price_total)
                            #and not move_line.asset_ids
                            and not move_line.tax_line_id
                            and move_line.price_total > 0
                            and not (move.move_type in (
                            'out_invoice', 'out_refund') and move_line.account_id.internal_group == 'asset')
                    ):

                        revaluation_amount = move_line.price_unit
                        last_dep_date = self.env['account.move'].search([('asset_id', '=', move_line.revaluate_asset_id.id),
                                                                         ('state', '=', 'posted')],
                                                                        order='date desc',
                                                                        limit=1).date
                        if not self.env.company.account_asset_counterpart_id.id:
                            raise UserError('Please configure the account counterpart in default account settings!')
                        print(move_line.revaluate_asset_id.id,"2222222222222222222222222222222222222222222222222222222222222222222222222")
                        wiz = self.env['asset.modify'].create({'modify_action': 'modify',
                                                               'date': last_dep_date  if last_dep_date else move.date,
                                                               'value_residual': move_line.revaluate_asset_id.book_value + revaluation_amount,
                                                               'account_asset_counterpart_id': self.env.company.account_asset_counterpart_id.id,
                                                               'name': 'Revaluate',
                                                               'asset_id': move_line.revaluate_asset_id.id,
                                                               'method_number': move_line.revaluate_asset_id.method_number,
                                                               'method_period': move_line.revaluate_asset_id.method_period,
                                                               'salvage_value': move_line.revaluate_asset_id.salvage_value,
                                                               'account_asset_id': move_line.revaluate_asset_id.account_asset_id.id,
                                                               'account_depreciation_id': move_line.revaluate_asset_id.account_depreciation_id.id,
                                                               'account_depreciation_expense_id': move_line.revaluate_asset_id.account_depreciation_expense_id.id, })
                        wiz.with_context(revaluation_move=move).modify()
                        move.revaluate_asset_id = self.env['account.asset'].search([('parent_id', '=', move_line.revaluate_asset_id.id)])[-1]



    def _log_depreciation_asset(self):
        for move in self.filtered(lambda m: m.asset_id):
            if not move.revaluate:
                asset = move.asset_id
                msg = _('Depreciation entry %(name)s posted (%(value)s)', name=move.name, value=formatLang(self.env, move.depreciation_value, currency_obj=move.company_id.currency_id))
                asset.message_post(body=msg)
    
    def _auto_create_asset(self):
        create_list = []
        invoice_list = []
        auto_validate = []
        for move in self:
            if not move.revaluate:
                print("1111111111111111111111111111111111111111111111111111111111111111111111111111f")
                if not move.is_invoice():
                    continue

                for move_line in move.line_ids:
                    if (
                        move_line.account_id
                        and (move_line.account_id.can_create_asset)
                        and move_line.account_id.create_asset != "no"
                        and not (move_line.currency_id or move.currency_id).is_zero(move_line.price_total)
                        and not move_line.asset_ids
                        and not move_line.tax_line_id
                        and move_line.price_total > 0
                        and not (move.move_type in ('out_invoice', 'out_refund') and move_line.account_id.internal_group == 'asset')
                    ):
                        if not move_line.name:
                            if move_line.product_id:
                                move_line.name = move_line.product_id.display_name
                            else:
                                raise UserError(_('Journal Items of %(account)s should have a label in order to generate an asset', account=move_line.account_id.display_name))
                        if move_line.account_id.multiple_assets_per_line:
                            # decimal quantities are not supported, quantities are rounded to the lower int
                            units_quantity = max(1, int(move_line.quantity))
                        else:
                            units_quantity = 1

                        model_ids = move_line.account_id.asset_model_ids
                        vals = {
                            'name': move_line.name,
                            'company_id': move_line.company_id.id,
                            'currency_id': move_line.company_currency_id.id,
                            'analytic_distribution': move_line.analytic_distribution,
                            'original_move_line_ids': [(6, False, move_line.ids)],
                            'state': 'draft',
                            'acquisition_date': move.invoice_date if not move.reversed_entry_id else move.reversed_entry_id.invoice_date,
                        }
                        for model_id in model_ids or [None]:
                            if model_id:
                                vals['model_id'] = model_id.id

                            auto_validate.extend([move_line.account_id.create_asset == 'validate'] * units_quantity)
                            invoice_list.extend([move] * units_quantity)
                            for i in range(1, units_quantity + 1):
                                if units_quantity > 1:
                                    vals['name'] = _("%(move_line)s (%(current)s of %(total)s)", move_line=move_line.name, current=i, total=units_quantity)
                                create_list.extend([vals.copy()])

                assets = self.env['account.asset'].with_context({}).create(create_list)
                for asset, vals, invoice, validate in zip(assets, create_list, invoice_list, auto_validate):
                    if 'model_id' in vals:
                        asset._onchange_model_id()
                        if validate:
                            asset.validate()
                    if invoice:
                        asset.message_post(body=_('Asset created from invoice: %s', invoice._get_html_link()))
                        asset._post_non_deductible_tax_value()
                return assets


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    revaluate = fields.Boolean(related="move_id.revaluate")
    revaluate_asset_id = fields.Many2one('account.asset', string="Asset",
                              help="Reference to the revaluate asset.",
                               domain="[('state', '=', 'open')]")
