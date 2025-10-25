# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

from odoo import models


class ExternalDatasetTables(models.Model):
    _inherit = 'external.dataset.table'

    def action_pb_view_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.model_id.name,
            'res_model': self.model_id.model,
            'domain': self.domain,
            'view_mode': 'list,form',
        }

