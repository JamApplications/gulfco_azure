from odoo import api, fields, models, _


class CrmTeam(models.Model):
    _inherit = 'crm.team'


    partner_member_ids = fields.Many2many(
        'res.partner',
        string='Contacts',
        domain="[('fsm_person', '=', True)]",
        help="Only contacts who are FS Workers can be assigned."
    )

    team_type = fields.Selection([('van_sale','VAN Sale'),
                                  ('pre_sale','Pre-Sale'),
                                  ('merchandise','Merchandise'),
                                  ('delivery','Delivery'),
                                  ], string='Team')
