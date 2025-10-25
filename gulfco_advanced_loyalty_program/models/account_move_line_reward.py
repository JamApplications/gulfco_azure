from odoo import models, fields, api, _

class AccountMoveLineReward(models.Model):
    _name = 'account.move.line.reward'
    _description = "Invoice Line Reward"

    name = fields.Char()
    account_move_line_id = fields.Many2one("account.move.line", required=True, ondelete="cascade")
    applied_reward_id = fields.Many2one(
        comodel_name='loyalty.reward', ondelete='restrict', readonly=True, required=True)
    applied_discount = fields.Float(string="Applied Discount (%)")
    applied_discount_value = fields.Float(string="Applied Discount")
    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('fixed', 'Fixed Amount')],
        string="Discount Type",
        default='percent'
    )
    
    def unlink(self):
        for rec in self:
            rec.account_move_line_id.test_discount = rec.account_move_line_id.test_discount - rec.applied_discount
            rec.account_move_line_id.test_discount_value = rec.account_move_line_id.test_discount_value - rec.applied_discount_value
        return super().unlink()