from odoo import api, fields, models, _

class FSMTeam(models.Model):
    _inherit = "fsm.team"

    team_type = fields.Selection(related="sales_team_id.team_type",store=True)