# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RMA(models.Model):
    _inherit = 'rma'


    responsible_worker_id = fields.Many2one('res.partner', 'Responsible Worker', domain="[('fsm_person', '=', True)]")
    visit_id = fields.Many2one('fsm.order', 'Visit')
    project_id = fields.Many2one('project.project', 'Project')

    crm_team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales team",
        index=True,
        compute="_compute_crm_team_id",
        store=True,
    )

    @api.depends("user_id", "responsible_worker_id")
    def _compute_crm_team_id(self):
        self.crm_team_id = False
        for record in self.filtered("responsible_worker_id"):
            record.crm_team_id = (
                self.env["crm.team"]
                .sudo()
                .search(
                    [
                        "|",
                        ("user_id", "=", record.user_id.id),
                        ("partner_member_ids", "=", record.responsible_worker_id.id),
                        # "|",
                        # ("company_id", "=", False),
                        # ("company_id", "child_of", record.company_id.ids),
                    ],
                    limit=1,
                )
            )
