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
from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"

    account_asset_counterpart_id = fields.Many2one(comodel_name='account.account', string='Asset Counterpart Account', check_company=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_asset_counterpart_id = fields.Many2one(
        comodel_name='account.account',
        string='Asset Counterpart Account',
        help='Account for the asset counterpart',
        readonly=False,
        check_company=True,
        related='company_id.account_asset_counterpart_id',)