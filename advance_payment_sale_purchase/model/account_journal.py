from odoo import models, fields, api, _
from odoo.exceptions import UserError



class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_advance_sale = fields.Boolean('Advance Sale')
    is_advance_purchase = fields.Boolean('Advance Purchase')

    default_rma_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Default RMA Account',)
        # domain=_get_default_account_domain)