from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_default_journal_id(self):
        property_stock_journal = self.env['ir.default'].with_company(self.env.company.id)._get_model_defaults('product.category').get('property_stock_journal')
        return property_stock_journal if property_stock_journal else False

    # default value form res.config.settings field:property_stock_journal
    gl_journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('type', '=', 'general')]",
        default=_get_default_journal_id
    )

    gl_move_ids = fields.One2many(
        'account.move',
        'gl_stock_picking_id',
        string='GL Entries',
    )

    def create_gl_entry(self):
        if not self.gl_journal_id and self.picking_type_code == 'internal' and self.location_id.warehouse_id != self.location_dest_id.warehouse_id:
            raise UserError(_('Please select a journal for this transaction'))

        if self.location_id.warehouse_id != self.location_dest_id.warehouse_id and self.picking_type_code == 'internal':
            amount = sum(
                [line.quantity * line.product_id.standard_price for line in self.move_line_ids],)
            self.env['account.move'].create({
                'journal_id': self.gl_journal_id.id,
                'date': self.scheduled_date,
                'ref': self.name,
                'line_ids': [
                    (0, 0, {
                        'name': self.name,
                        'account_id': self.location_dest_id.warehouse_id.gl_account_id.id,
                        'debit': amount,
                        'credit': 0,
                    }),
                    (0, 0, {
                        'name': self.name,
                        'account_id': self.location_id.warehouse_id.gl_account_id.id,
                        'debit': 0,
                        'credit': amount,
                    }),
                ],
                'gl_stock_picking_id': self.id,
            })

    def button_validate(self):
        res = super().button_validate()
        for rec in self:
            rec.create_gl_entry()
        return res

    def action_view_gl_entries(self):
        # open accounting entries related to this stock picking
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('gl_stock_picking_id', '=', self.id)]
        return action
