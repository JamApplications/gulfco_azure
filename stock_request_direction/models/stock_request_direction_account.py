from odoo import api, fields, models


class StockRequestDirectionAccount(models.Model):
    _name = "stock.request.direction.account"
    _rec_name = "direction"
    _description = "Default Accounts for Stock Request Order Request Type"

    direction = fields.Selection(
        [
            ('internal_transfer', 'Internal Transfer'),
            ('branch_transfer', 'Branch Transfer'),
            ('sample_issue_out', 'Sample Issue Out'),
            ('damage_expiry_issue_out', 'Damage & Expiry Issue Out'),
            ('miscellaneous_issue_out', 'Miscellaneous Issue Out'),
            ('foc_receiving', 'FOC Receiving'),
            ('miscellaneous_receiving', 'Miscellaneous Receiving'),
            ('consumable_issuance', 'Consumable Issuance'),
            ('scrap_issuance', 'Scrap Issuance'),
            ('van_load', 'Van Load'),
            ('van_off_load', 'Van Off Load'),
            ('stock_takeover', 'Stock Takeover')
        ],
        string="Request Type",
        required=True,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Default Account",
        required=True,
    )

    _sql_constraints = [
        (
            'unique_direction',
            'unique(direction)',
            'You cannot create duplicate records for the same Request Type.'
        )
    ]
