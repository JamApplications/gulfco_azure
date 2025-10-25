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
from docutils.parsers.rst.directives import percentage
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from itertools import product
import re



class AccountAnalyticCommonDistribution(models.Model):
    _name = 'account.analytic.common.distribution'
    _description = 'Distribute Common Analytic'

    code = fields.Char(string="Code")
    name = fields.Char(string="Name")
    analytic_id = fields.Many2one(comodel_name='account.analytic.account', string='Analytic')
    line_ids = fields.One2many(comodel_name='account.analytic.common.distribution.line', inverse_name='distribution_id', string='Line IDs')
    active = fields.Boolean(string='Active', default='True')



class AccountAnalyticCommonDistributionLine(models.Model):
    _name = 'account.analytic.common.distribution.line'
    _description = 'Distribute Common Analytic Lines'

    distribution_id = fields.Many2one(comodel_name='account.analytic.common.distribution', string='Distribution')
    analytic_id = fields.Many2one(comodel_name='account.analytic.account', string='Analytic')
    percentage = fields.Float(string='Percentage')



class AccountMove(models.Model):
    _inherit = 'account.move'

    def _action_distribute(self):
        lines = []
        loc = False
        dep = False
        ch = False
        for line in self.env['account.move.line'].search([('is_distribute', '=', False),
                                                          ('account_id.account_type', 'in', ('income','income_other','expense','expense_depreciation','expense_direct_cost')),
                                                          ('parent_state', '=', 'posted')
                                                          ]):
            loc = False
            dep = False
            ch = False
            line.distribute_match = line.id
            line.is_distribute = True
            for analytic in line.distribution_analytic_account_ids:
                if analytic.is_common == False and analytic.plan_id.is_location == True:
                    loc = analytic
                if analytic.is_common == False and analytic.plan_id.is_department == True:
                    dep = analytic
                if analytic.is_common == False and analytic.plan_id.is_channel == True:
                    ch = analytic
            print(loc, dep, ch, "111111111111111111111111111111111111111111111111111111111111")
            if not (loc and dep and ch):
                print("33333333333333333333333333333333333333333333333333333333333333333333333")
                lines.append({'name': line.name,
                              'partner_id': line.partner_id.id,
                              'account_id': line.account_id.id,
                              'debit': -1*(line.amount_currency) if line.amount_currency < 0 else 0,
                              'credit': line.amount_currency if line.amount_currency > 0 else 0,
                              'currency_id': line.currency_id.id,
                              'is_distribute': True,
                              'distribute_match': line.id,
                              'analytic_distribution': line.analytic_distribution,
                              })
                for dis in line.move_id.generate_distribution_dict(line.amount_currency,loc, dep, ch):
                    distribution = {str(account_id): 100 for account_id in dis['analytic_ids']}
                    lines.append({'name': line.name,
                                  'partner_id': line.partner_id.id,
                                  'account_id': line.account_id.id,
                                  'debit': dis['amount'] if dis['amount'] > 0 else 0,
                                  'credit': -1*(dis['amount']) if dis['amount'] < 0 else 0,
                                  'currency_id': line.currency_id.id,
                                  'is_distribute': True,
                                  'distribute_match':line.id,
                                  'analytic_distribution': distribution,
                                  }),
        print(lines, "222222222222222222222222222222222222222222222222222222222222222222222222222222")
        if lines:
            move=self.env['account.move'].create({'date': fields.date.today(),
                                                  'journal_id': line.move_id.journal_id.id,
                                                  'ref': line.move_id.ref,
                                                  'partner_id': line.move_id.partner_id.id,
                                                  'line_ids': [(0, 0, line) for line in lines]})
            move.action_post()

        return True

    def get_all_combinations(self,loc, dep, ch):
        """Return all 27 possible combinations as tuples (loc, dept, channel)"""

        locations = []
        departments = []
        channels = []
        for line in self.env['account.analytic.common.distribution.line'].search([]):
            if line.distribution_id.analytic_id.plan_id.is_location == True and not loc:
                locations.append(line.analytic_id.id)
            elif line.distribution_id.analytic_id.plan_id.is_department == True and not dep:
                departments.append(line.analytic_id.id)
            elif line.distribution_id.analytic_id.plan_id.is_channel == True and not ch:
                channels.append(line.analytic_id.id)
        if loc:
            locations.append(loc.id)
        if dep:
            departments.append(dep.id)
        if ch:
            channels.append(ch.id)

        return list(product(locations, departments, channels))

    def calculate_combinations(self, amount, distribution_rates,loc, dep, ch):
        self._validate_distribution_rates(distribution_rates)

        combinations = self.get_all_combinations(loc, dep, ch)
        result = []

        for loc, dept, channel in combinations:
            # Calculate the distributed amount through all levels
            loc_amount = (amount * distribution_rates['location'][loc]) / 100
            dept_amount = (loc_amount * distribution_rates['department'][dept]) / 100
            final_amount = (dept_amount * distribution_rates['channel'][channel]) / 100

            # Create a unique key for each combination
            combo_key = f"{loc}-{dept}-{channel}"
            result.append({
                'location': loc,
                'department': dept,
                'channel': channel,
                'amount': final_amount,
                'analytic_ids': [loc,dept,channel]
            })
        return result

    def _validate_distribution_rates(self, distribution_rates):
        """Ensure percentages sum to 100% for each level"""
        for level, rates in distribution_rates.items():
            total = sum(rates.values())
            if not (99.9 <= total <= 100.1):  # Allow for floating point rounding
                raise ValueError(
                    f"Percentages for {level} level must sum to 100% (currently {total}%)"
                )


    def generate_distribution_dict(self, amount, loc, dep, ch):
        """
        Sample implementation with your specific distribution rates
        Returns the full 27-combination distribution dictionary
        """
        distribution_rates = {}
        location_dic = {}
        department_dic = {}
        channel_dic = {}
        for line in self.env['account.analytic.common.distribution.line'].search([]):
            if line.distribution_id.analytic_id.plan_id.is_location == True and not loc:
                location_dic.update({line.analytic_id.id: line.percentage})
            if line.distribution_id.analytic_id.plan_id.is_department == True and not dep:
                department_dic.update({line.analytic_id.id: line.percentage})
            if line.distribution_id.analytic_id.plan_id.is_channel == True and not ch:
                channel_dic.update({line.analytic_id.id: line.percentage})
        if loc:
            location_dic.update({loc.id: 100})
        if dep:
            department_dic.update({dep.id: 100})
        if ch:
            channel_dic.update({ch.id: 100})
        distribution_rates.update({'location': location_dic})
        distribution_rates.update({'department': department_dic})
        distribution_rates.update({'channel': channel_dic})
        return self.calculate_combinations(amount, distribution_rates,loc, dep, ch)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_distribute = fields.Boolean(string="Distributed")
    distribute_match = fields.Char(string="Distributed Match")


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    is_common = fields.Boolean(string="Common Analytic")


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    is_location = fields.Boolean(string="Location")
    is_department = fields.Boolean(string="Department")
    is_channel = fields.Boolean(string="Channel")
    active = fields.Boolean(
        'Active',
        help="Deactivate the Plan.",
        default=True,
        tracking=True,
    )

    def action_archive(self):
        for record in self:
            if record.account_ids:
                record.account_ids.action_archive()
        return super(AccountAnalyticPlan, self).action_archive()

    def action_unarchive(self):
        res = super().action_unarchive()
        for record in self:
            if record.with_context(active_test=False).account_ids:
                record.with_context(active_test=False).account_ids.action_unarchive()
        return res

