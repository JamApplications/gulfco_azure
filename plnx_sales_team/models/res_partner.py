from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    worker_password_data = fields.Char( string="Worker Password", readonly=True, default=None, copy=False)
    division = fields.Selection([('food', 'Food'),
                                            ('non_food', 'Non-Food'),
                                            ('mars', 'MARS')
                                        ], string='Division')
    division_ids = fields.Many2many('division.management',string="Division")
    location_analytic_account_id = fields.Many2one('account.analytic.account', string="Location")


    def auto_generate_password(self):
        pass_config = self.env['team.password.config'].search([('state', '=', 'active')], limit=1)
        if not pass_config:
            raise ValidationError("Active Password Configuration Not Found.")

        if not pass_config.sequence:
            worker_seq = self.env['ir.sequence'].sudo().create({
                'name': _("Worker Password"),
                'implementation': 'no_gap',
                'padding': pass_config.no_of_sequence,
                'use_date_range': True,
                'company_id': self.env.company.id,
                'prefix': pass_config.prefix or None,
                'suffix': pass_config.suffix or None,
                'code': ('%s_%s'%(pass_config.id, pass_config.name))
            })
            pass_config.sequence = worker_seq.id

        self.worker_password_data = self.env['ir.sequence'].next_by_code(pass_config.sequence.code) or _('New')


    partner_channel_id = fields.Many2one('channel.channel', string='Channel')

    outlet_id = fields.Many2one(
        'outlet.channel',
        string='Outlet Classification',
        domain="[('channel_name_id', '=', partner_channel_id)]",
    )

    sub_outlet_id = fields.Many2one(
        'sub.outlet.channel',
        string='SubOutlet Classification',
        domain="[('outlet_id', '=', outlet_id)]",
    )

    @api.onchange('partner_channel_id')
    def _onchange_partner_channel_id(self):
        self.outlet_id = False
        self.sub_outlet_id = False

    @api.onchange('outlet_id')
    def _onchange_outlet_id(self):
        self.sub_outlet_id = False