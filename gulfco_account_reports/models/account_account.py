from odoo import _, api, fields, models

class AccountAccount(models.Model):
  _inherit = "account.account"

  vat_detail_type = fields.Selection(
    [('input','Input'),('output','Output')]
  )