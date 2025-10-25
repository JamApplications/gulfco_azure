# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _



class TeamPasswordConfig(models.Model):
    _name = "team.password.config"
    _description = "Team Password Configuration"
    _inherit = ["mail.thread", "mail.activity.mixin"]


    name = fields.Char(required=True)
    prefix = fields.Char('Prefix', required=True)
    suffix = fields.Char('Suffix')
    no_of_sequence = fields.Integer('No of Sequence', required=True)
    state = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], default='inactive', copy=False)

    sequence = fields.Many2one('ir.sequence', readonly=True, copy=False)

    @api.model
    def create(self, vals):
        if vals.get('no_of_sequence', 0) < 0:
            raise ValidationError("The value of 'No of Sequence' cannot be negative.")
        return super(TeamPasswordConfig, self).create(vals)

    def write(self, vals):
        if 'no_of_sequence' in vals and vals['no_of_sequence'] < 0:
            raise ValidationError("The value of 'No of Sequence' cannot be negative.")
        return super(TeamPasswordConfig, self).write(vals)


    def action_active(self):
        active = self.search([('state', '=', 'active')])
        if active:
            raise ValidationError(_('There is already an active password configuration, the system will only allow one active state at a time'))
        else:
            if not self.sequence:
                worker_seq = self.env['ir.sequence'].sudo().create({
                    'name': _("Worker Password"),
                    'implementation': 'no_gap',
                    'padding': self.no_of_sequence,
                    'use_date_range': True,
                    'company_id': self.env.company.id,
                    'prefix': self.prefix or None,
                    'suffix': self.suffix or None,
                    'code': ('%s_%s' % (self.id, self.name))
                })
                self.sequence = worker_seq.id
            else:
                self.sequence.write({
                    'padding': self.no_of_sequence,
                    'company_id': self.env.company.id,
                    'prefix': self.prefix or None,
                    'suffix': self.suffix or None,
                    'code': ('%s_%s' % (self.id, self.name)),
                })

            self.state = 'active'

    def action_inactive(self):
        self.state = 'inactive'
