# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

from uuid import uuid4
from odoo import models, fields, api

ODOO_TO_PBI_FIELD_MAP = {
    'text': 'textType',
    'char': 'textType',
    'html': 'textType',
    'selection': 'textType',
    'boolean': 'booleanType',
    'binary': 'binaryType',
    'integer': 'integerType',
    'float': 'floatType',
    'monetary': 'currencyType',
    'many2one': 'integerType',
    'many2many': 'listType',
    'one2many': 'listType',
    'date': 'dateType',
    'datetime': 'dateTimeType',
}

class PbDatasetConfiguration(models.Model):
    _name = 'pb.dataset.configuration'
    _description = "PowerBI Dataset Configuration"

    api_key = fields.Char('API Key', required=True, default=lambda self: str(uuid4()))
    access_type = fields.Selection(selection=[('user_based', 'User Based Access'),
                                    ('full_access', 'Full Access Using Sudo')],
                                    string='Access Type', required=True)
    user_id = fields.Many2one('res.users', string='User')
    user_company_ids = fields.Many2many('res.company', related='user_id.company_ids')
    allowed_company_ids = fields.Many2many('res.company', string='Allowed Companies',
                                        domain="[('id', 'in', user_company_ids)]")
    ext_dataset_table_ids = fields.Many2many('external.dataset.table', string='Dataset Table', required=True)

    @api.onchange('user_id')
    def _onchange_user_id(self):
        for rec in self:
            rec.allowed_company_ids = False

    @api.constrains('api_key')
    def _check_api_key_field(self):
        for record in self:
            duplicate_records = self.search([('api_key', '=', record.api_key)])
            if len(duplicate_records) > 1:
                raise models.ValidationError('API Key  must be unique!')

    @api.constrains('ext_dataset_table_ids')
    def _check_ext_dataset_table_ids_field(self):
        for record in self:
            if not record.ext_dataset_table_ids:
                raise models.ValidationError('Must have atleast one table')

    def get_powerbi_table_data(self):
        """Return Dictionary that will be used in external system as data"""
        self.ensure_one()
        main_data = {}
        many2many_data = {}
        for dt_table in self.ext_dataset_table_ids:
            if self.access_type == 'full_access':
                Model = self.env[dt_table.model_id.model].sudo()
            elif self.access_type == 'user_based':
                Model = self.env[dt_table.model_id.model].with_user(self.user_id.id).with_context(
                                        allowed_company_ids=self.allowed_company_ids.ids)
            records = Model.search(eval(dt_table.domain))
            record_data = []
            for r in records:
                vals = {}
                for v in dt_table.field_ids:
                    if v.ttype in ['one2many']:
                        vals[v.name] = r[v.name].ids if r[v.name] else None
                    elif v.ttype in ['many2many']:
                        many2many_ids = r[v.name].ids if r[v.name] else None
                        vals[v.name] = many2many_ids
                        if many2many_ids and v.store:
                            for m in many2many_ids:
                                relation_table = v.relation_table
                                if not relation_table:
                                    tables = sorted([r._table, r[v.name]._table])
                                    relation_table = '%s_%s_rel' % tuple(tables)

                                column1 = v.column1
                                column2 = v.column2
                                if not column1:
                                    column1 = '%s_id' % r._table
                                if not column2:
                                    column2 = '%s_id' % r[v.name]._table
                                if many2many_data.get(relation_table):
                                    many2many_data[relation_table].append({column1: r.id, column2: m})
                                else:
                                    many2many_data[relation_table] = [{column1: r.id, column2: m}]
                    elif v.ttype == 'many2one':
                        vals[v.name] = r[v.name].id if r[v.name] else None
                    elif v.ttype == 'date':
                        vals[v.name] = r[v.name].strftime("%Y-%m-%d") if r[v.name] else None
                    elif v.ttype == 'datetime':
                        vals[v.name] = r[v.name].strftime("%Y-%m-%dT%H:%M:%S") if r[v.name] else None
                    elif v.ttype == 'binary':
                        vals[v.name] = str(r[v.name]) if r[v.name] else None
                    else:
                        vals[v.name] = r[v.name] if r[v.name] else None
                record_data.append(vals)
            main_data[self.env[dt_table.res_model_name]._table] = record_data
        final_data = {**main_data, **many2many_data}
        return final_data

    def get_powerbi_table_schema(self):
        main_data = {}
        for dt_table in self.ext_dataset_table_ids:
            main_data[self.env[dt_table.res_model_name]._table] = self.make_pb_table_schema(dt_table)
        return main_data

    def make_pb_table_schema(self, dt_table):
        schema_values = {}
        for f in dt_table.field_ids:
            schema_values[f.name] = ODOO_TO_PBI_FIELD_MAP.get(f.ttype, 'textType')
        return schema_values
