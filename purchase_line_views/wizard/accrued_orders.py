from odoo import models, fields, api, _, Command
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

class AccruedExpenseRevenue(models.TransientModel):
    _inherit = 'account.accrued.orders.wizard'

    reversal_date = fields.Date(
        compute="_compute_reversal_date",
        required=False,
        readonly=False,
        store=True,
        precompute=True,
    )
    amount = fields.Monetary(string='Amount', help="Specify an arbitrary value that will be accrued on a \
        default account for the entire order, regardless of the products on the different lines.",currency_field='currency_id')
    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_id,related=False, string='Currency',
        readonly=False, store=True,
        help='Utility field to express amount currency')


    @api.depends('date')
    def _compute_reversal_date(self):
        for wizard in self:
            if not wizard.reversal_date or wizard.reversal_date <= wizard.date:
                wizard.reversal_date = wizard.date + relativedelta(days=1)
            else:
                wizard.reversal_date = wizard.reversal_date

    @api.depends('company_id')
    def _compute_journal_id(self):
        for record in self:
            record.journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(record.company_id),
                ('type', '=', 'general'),
                ('is_accrued_journal','=',True)
            ], limit=1)

    def create_entries(self):
        self.ensure_one()
        if self.reversal_date <= self.date:
            raise UserError(_('Reversal date must be posterior to date.'))
        orders = self.env[self._context['active_model']].with_company(self.company_id).browse(self._context['active_ids'])
        if len({order.currency_id or order.company_id.currency_id for order in orders}) != 1:
            raise UserError(_('Cannot create an accrual entry with orders in different currencies.'))

        move_vals, orders_with_entries = self._compute_move_vals()
        move = self.env['account.move'].create(move_vals)
        move._post()
        # comment code becuase in customization no need to reverse entries
        # reverse_move = move._reverse_moves(default_values_list=[{
        #     'ref': _('Reversal of: %s', move.ref),
        #     'name': '/',
        #     'date': self.reversal_date,
        # }])
        # reverse_move._post()
        # for order in orders_with_entries:
        #     body = _(
        #         'Accrual entry created on %(date)s: %(accrual_entry)s.\
        #             And its reverse entry: %(reverse_entry)s.',
        #         date=self.date,
        #         accrual_entry=move._get_html_link(),
        #         reverse_entry=reverse_move._get_html_link(),
        #     )
        #     order.message_post(body=body)
        return {
            'name': _('Accrual Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', '=', move.id)],
        }