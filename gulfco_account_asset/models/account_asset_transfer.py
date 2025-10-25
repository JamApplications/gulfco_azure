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
from odoo import models, fields, _


class AccountAssetTransfer(models.Model):
    _name = 'account.asset.transfer'
    _description = 'Model show transferred asset details'

    asset_id = fields.Many2one(comodel_name="account.asset", string="Asset")
    original_location = fields.Json(string="Original Location")
    new_location = fields.Json(string="New Location")
    transfer_date = fields.Date(string="Transfer Date")
    transfer_memo = fields.Text(string="Note")
    transfer_by = fields.Many2one(comodel_name="res.users", string="Transferred By")
    analytic_precision = fields.Integer(string="Analytic Precision", default=2)

    def open_transferred_asset(self, view_mode):

        view_mode = ['list']
        views = [v for v in [(False, 'list'), (False, 'form')] if v[1] in view_mode]
        ctx = dict(self._context)
        ctx.pop('default_move_type', None)
        action = {
            'name': _('Asset Transfer'),
            'view_mode': ','.join(view_mode),
            'type': 'ir.actions.act_window',
            'res_id': self.id if 'list' not in view_mode else False,
            'res_model': 'account.asset.transfer',
            'views': views,
            'domain': [('id', 'in', self.ids)],
            'context': ctx
        }
        return action