from odoo import _, api, fields, models


class AsnStage(models.Model):
  _name = 'asn.stage'
  _description = 'ASN Stage'

  name = fields.Char(string='Name', required=True)
  sequence = fields.Integer(string='Sequence', required=True)
  description = fields.Text(string='Description')
