from odoo import _, api, fields, models

class AccountAccount(models.Model):
  _inherit = "account.account"

  is_stock_control = fields.Boolean(copy=False)