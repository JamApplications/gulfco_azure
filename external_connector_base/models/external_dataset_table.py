# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

from odoo import models, fields, api


class ExternalDatasetTables(models.Model):
    _name = 'external.dataset.table'
    _description = "External Dataset Table"

    name = fields.Char('Name', required=True)
    model_id = fields.Many2one('ir.model', string='Model',  ondelete='cascade', required=True)
    domain = fields.Char('Domain', default=[], required=True)
    res_model_name = fields.Char(related='model_id.model', string='Model Name')
    field_ids = fields.Many2many('ir.model.fields', domain='[("model_id", "=", model_id)]', string='Fields')

    @api.onchange('model_id')
    def _onchange_model_id(self):
        for rec in self:
            rec.field_ids = False
