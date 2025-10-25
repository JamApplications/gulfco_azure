
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError,UserError
from datetime import date

SALE_ORDER_STATE = [
    ('draft', "Quotation"),
    ('sent', "Quotation Sent"),
    ('pending', 'Waiting Approval'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('sale', "Sales Order"),
    ('cancel', "Cancelled"),
]

class SaleOrderExt(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(default=True)

    is_discount_panding = fields.Boolean(string='Is discount')
    is_po_amount_panding = fields.Boolean(string='Is Po Amount')
    is_po_exp_date_panding = fields.Boolean(string='Is Po Exp Date')

    order_creation_source = fields.Selection(
        [('vansales', 'Vansales'), ('presales', 'Presales'),('back_office','Back Office')],
        string="Order Creation Source",default="back_office"
    )
    po_date = fields.Date(string="PO Date/Order Received Date")
    po_number = fields.Char(string="PO Number", copy=False)
    po_expiry_date = fields.Date(string="PO Expiry Date")
    delivery_request_date = fields.Date(string="Delivery Request Date")
    po_amount_without_vat = fields.Float(string="PO Amount without VAT")
    po_amount_without_vat_char = fields.Char(string="PO Amount without VAT")
    # customer_channel = fields.Selection(
    #     string="Customer Channel",
    #     related="partner_id.channel",
    #     store=True
    # )
    customer_partner_channel = fields.Many2one('channel.channel',
                                               related="partner_id.partner_channel_id", store=True,
                                               string="Channel"
                                               )
    re_customer_group_id = fields.Many2one(
        related="partner_id.customer_group_id",
        string="Customer Group",
        store=True
    )
    delivery_required = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Delivery Required",
        default="yes"
    )
    order_type = fields.Selection(
        [('normal', 'Normal'), ('near_expiry', 'Near Expiry')],
        string="Order Type",
        default="normal"
    )
    remarks = fields.Text(string="Remarks")

    state = fields.Selection(
        selection=SALE_ORDER_STATE,
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=True,
        default='draft'
    )

    discount_approval_state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ],
        string="Discount Approval State",
        compute="_compute_discount_approval_state",
        store=True
    )
    is_applied_discount_approval = fields.Boolean(string="IS Applied Dis")
    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment Terms",
        compute='_compute_payment_term_id',
        store=True, readonly=False, precompute=True, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    
    quotation_number = fields.Char(
        string="Quotation Number",
        help="Stores the original quotation number before confirmation."
    )

    @api.depends('partner_id')
    def _compute_payment_term_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            if order.partner_id.property_payment_term_id:
                order.payment_term_id = order.partner_id.property_payment_term_id
            else:
                payment_term = self.env.ref('account.account_payment_term_immediate', raise_if_not_found=False)
                if payment_term:
                    order.payment_term_id = payment_term.id
                else:
                    order.payment_term_id = False

    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id')
    def _compute_amounts(self):
        res = super(SaleOrderExt, self)._compute_amounts()
        for order in self:
            order.amount_untaxed = sum(order.order_line.mapped('price_subtotal'))
            order.amount_total = sum(order.order_line.mapped('price_total'))
            # order.amount_total = order.amount_untaxed + sum(order.order_line.mapped('excise_total_amount' or [0]))
        return res

    sale_journal = fields.Many2one('account.journal')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("order_creation_source"):
                vals['order_creation_source'] = 'back_office'
        res =  super().create(vals_list)
        for record in res:
            if record.order_creation_source == 'back_office' and record.po_amount_without_vat <= 0.0:
                raise UserError('Please Put the value in PO Amount without VAT')
        return res

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.order_creation_source == 'back_office' and record.po_amount_without_vat <= 0.0:
                raise UserError('Please Put the value in PO Amount without VAT')
        return res
    # @api.onchange('po_expiry_date')
    # def _onchange_po_expiry_date(self):
    #     for record in self:
    #         if record.po_expiry_date and record.po_expiry_date < date.today():
    #             record.is_po_amount_panding = True
    #             if record.state not in ['sale', 'rejected', 'cancel']:
    #                 record.state = 'pending'
    #                 group = self.env.ref('gulfco_sale_extanded.discount_approvel_group')
    #                 if not group:
    #                     raise UserError("Approval group not found.")
    #                 group_users = group.users
    #                 for user in group_users:
    #                     record.activity_schedule(
    #                         'mail.mail_activity_data_todo',
    #                         summary='Po Expiry Date Approval Needed',
    #                         note=f'Po Expiry Date Approval Needed: {record.name}',
    #                         user_id=user.id,
    #                         date_deadline=fields.Date.today()
    #                     )

    # @api.model
    # def create(self, vals):
    #     res = super(SaleOrderExt, self).create(vals)
    #     for record in res:
            # if record.po_expiry_date and record.po_expiry_date < date.today():
            #     record.is_po_exp_date_panding = True
            #     record.state = 'pending'
            #     group = self.env.ref('gulfco_sale_extanded.discount_approvel_group')
            #     if not group:
            #         raise UserError("Approval group not found.")
            #     group_users = group.users
            #     for user in group_users:
            #         record.activity_schedule(
            #             'mail.mail_activity_data_todo',
            #             summary='Po Expiry Date Approval Needed',
            #             note=f'Po Expiry Date Approval Needed: {self.name}',
            #             user_id=user.id,
            #             date_deadline=fields.Date.today()
            #         )
            # if record.amount_untaxed != float(record.po_amount_without_vat_char) and record.state != 'amount_approved':
            #     group = self.env.ref('gulfco_sale_extanded.discount_approvel_group')
            #     group_users = group.users
            #     for user in group_users:
            #         record.activity_schedule(
            #             'mail.mail_activity_data_todo',
            #             summary='PO Amount without VAT Approval Needed',
            #             note=f': PO Amount without VAT{record.po_amount_without_vat_char } Approval',
            #             user_id=user.id,
            #             date_deadline=fields.Date.today()
            #         )
            #         record.is_po_amount_panding = True
            #         record.state = 'pending'
        # return res

    # def write(self, vals):
    #     sc = super(SaleOrderExt, self).write(vals)
    #     for record in self:
    #         if 'po_expiry_date' in vals:
    #             record.set_approval_po_expiry_date()
    #         # if 'po_amount_without_vat_char' in vals or 'order_line' in vals:
    #         if 'po_amount_without_vat_char' in vals or 'amount_untaxed' in vals:
    #             record.set_approval_po_amount()
    #     return sc

    # def set_approval_po_expiry_date(self):
    #     rec = self
    #     if not rec:
    #         rec = self.sudo().search([('state','not in', ['sale', 'cancel'])])
    #     for record in rec:
    #         if record.po_expiry_date and record.po_expiry_date < date.today():
    #             record.is_po_exp_date_panding = True
    #             if record.state not in ['sale', 'cancel']:
    #                 record.state = 'pending'
    #         group = self.env.ref('gulfco_sale_extanded.discount_approvel_group')
    #         if not group:
    #             raise UserError("Approval group not found.")
    #         group_users = group.users
    #         for user in group_users:
    #             record.activity_schedule(
    #                 'mail.mail_activity_data_todo',
    #                 summary='Po Expiry Date Approval Needed',
    #                 note=f'Po Expiry Date Approval Needed: {record.name}',
    #                 user_id=user.id,
    #                 date_deadline=fields.Date.today()
    #             )
    # def set_approval_po_amount(self):
    #     for record in self:
    #         if record.order_line and record.amount_untaxed != float(record.po_amount_without_vat_char):
    #             group = self.env.ref('gulfco_sale_extanded.discount_approvel_group')
    #             group_users = group.users
    #             for user in group_users:
    #                 record.activity_schedule(
    #                     'mail.mail_activity_data_todo',
    #                     summary='PO Amount without VAT Approval Needed',
    #                     note=f': PO Amount without VAT{record.po_amount_without_vat_char} Approval',
    #                     user_id=user.id,
    #                     date_deadline=fields.Date.today()
    #                 )
    #                 record.is_po_amount_panding = True
    #                 record.state = 'pending'

    @api.depends('order_line.discount_approval_state', 'order_line.discount')
    def _compute_discount_approval_state(self):
        for order in self:
            states = order.order_line.mapped('discount_approval_state')
            if not states:
                order.discount_approval_state = 'approved'  # default if no lines
            elif all(state == 'pending' for state in states):
                order.discount_approval_state = 'pending'
            elif all(state == 'approved' for state in states):
                order.discount_approval_state = 'approved'
            elif all(state == 'rejected' for state in states):
                order.discount_approval_state = 'rejected'
            else:
                order.discount_approval_state = 'pending'  # mixed case fallback

    def approve_discount(self):
        for rec in self:
            summary = ''
            discount_approval = rec.is_discount_panding
            # date_approval = rec.is_po_exp_date_panding
            # amount_approval = rec.is_po_amount_panding

            if discount_approval:
                rec.is_discount_panding = False
                summary = 'Discount Approval Needed'
                for line in rec.order_line:
                    line.old_discount = 0
                    line.discount_approval_state = 'approved'
            if discount_approval:
                # rec.state = 'approved'
                rec.write({'state': 'sale'})
                if not rec.picking_ids:
                    rec._action_confirm()
            # elif date_approval and amount_approval:
            #     summary = 'Po Expiry Date Approval Needed'
            #     rec.is_po_exp_date_panding = False
            #     rec.state = 'pending'
            # elif date_approval:
            #     summary = 'Po Expiry Date Approval Needed'
            #     rec.is_po_exp_date_panding = False
            #     rec.state = 'approved'
            # elif amount_approval:
            #     summary = 'PO Amount without VAT Approval Needed'
            #     rec.is_po_amount_panding = False
            #     rec.state = 'amount_approved'
        # activity_type = self.env.ref('mail.mail_activity_data_todo')
        # if activity_type:
        #     activities = self.env['mail.activity'].sudo().search([
        #         ('res_id', 'in', self.ids),
        #         ('res_model', '=', self._name),
        #         ('activity_type_id', '=', activity_type.id),
        #         ('summary', '=', summary),
        #         ('state', '!=', 'done')
        #     ])
        #     activities.action_done()

    def reject_discount(self):
        for rec in self:
            summary = ''
            discount_approval = rec.is_discount_panding
            # date_approval = rec.is_po_exp_date_panding
            # amount_approval = rec.is_po_amount_panding

            # Handle discount rejection
            if discount_approval:
                rec.is_discount_panding = False
                summary = 'Discount Approval Needed'
                for line in rec.order_line:
                    line.with_context(from_reject=1).discount = line.old_discount
                    line.discount_approval_state = 'rejected'

            # Determine state based on approval combinations
            # if discount_approval:
            #     if date_approval or amount_approval:
            #         rec.state = 'pending'
            #     else:
            #         rec.state = 'rejected'
            # elif date_approval and amount_approval:
            #     summary = 'Po Expiry Date Approval Needed'
            #     rec.is_po_exp_date_panding = False
            #     rec.state = 'pending'
            # elif date_approval:
            #     summary = 'Po Expiry Date Approval Needed'
            #     rec.is_po_exp_date_panding = False
            #     rec.state = 'draft'
            # elif amount_approval:
            #     summary = 'PO Amount without VAT Approval Needed'
            #     rec.is_po_amount_panding = False
            #     rec.state = 'draft'

        # Mark related activities as done
        # activity_type = self.env.ref('mail.mail_activity_data_todo')
        # if activity_type:
        #     activities = self.env['mail.activity'].sudo().search([
        #         ('res_id', 'in', self.ids),
        #         ('res_model', '=', self._name),
        #         ('activity_type_id', '=', activity_type.id),
        #         ('summary', '=', summary),
        #         ('state', '!=', 'done')
        #     ])
        #     activities.action_done()

    def _confirmation_error_message(self):
        """ Return whether order can be confirmed or not if not then returm error message. """
        self.ensure_one()
        # if self.state not in {'draft', 'sent', 'approved'}:
        #     return _("Some orders are not in a state requiring confirmation.")
        if any(
            not line.display_type
            and not line.is_downpayment
            and not line.product_id
            for line in self.order_line
        ):
            return _("A line on these orders missing a product, you cannot confirm it.")

        return False

    def action_confirm(self):
        for so in self:
            pending_lines = so.order_line.filtered(lambda l: l.discount_approval_state != 'approved')
            if pending_lines:
                raise UserError("You cannot confirm the order. Some discounts are not approved yet.")
            if not so.quotation_number:
                so.quotation_number = so.name
        # for order in self:
        #     if order.amount_untaxed != order.po_amount_without_vat and order.state != 'amount_approved':
        #         group = self.env.ref('gulfco_sale_extanded.discount_approvel_group')
        #         group_users = group.users
        #         for user in group_users:
        #             order.activity_schedule(
        #                 'mail.mail_activity_data_todo',
        #                 summary='PO Amount without VAT Approval Needed',
        #                 note=f': PO Amount without VAT{order.po_amount_without_vat } Approval',
        #                 user_id=user.id,
        #                 date_deadline=fields.Date.today()
        #             )
        #             order.is_po_amount_panding = True
        #             order.state = 'pending'
                    # if order.po_amount_without_vat != order.amount_untaxed and order.is_po_amount_panding:
                    #     raise ValidationError("Po Without amount Are Not Match")
        res = super(SaleOrderExt, self).action_confirm()
        # for order in self:
            # for picking in order.picking_ids:
            #     if picking.state == 'confirmed':
            #         vals = {'trx_type': 'direct_delivery_order'}
            #         if order.commitment_date:
            #             vals.update({'scheduled_date': order.commitment_date})
            #         picking.sudo().write(vals)
            #         if order.order_creation_source == 'vansales':
            #             picking.sudo().write(
            #                 {'picking_driver_id': order.assign_to.id,
            #                  'forklift_partner_id': order.assign_to.id,
            #                  'picking_type_id': order.assign_to.van_location.warehouse_id.out_type_id.id,
            #                  'location_id': order.assign_to.van_location.id
            #                  })
            #             picking.sudo().location_id = order.assign_to.van_location.id
            #
            #         picking.action_assign()
            # if order.order_creation_source != 'vansales':
            #     picking_ids = order._create_all_pickings_from_rule_chain(all_moves)
            #     vals = {'trx_type': 'direct_delivery_order'}
            #     if order.commitment_date:
            #         vals.update({'scheduled_date': order.commitment_date})
            #     picking_ids.sudo().write(vals)
            #     other_picking = picking_ids.filtered(lambda s:not s.is_out_type)
            #     other_picking.action_confirm()
        return res

    def _action_confirm(self):
        res = super()._action_confirm()
        for order in self:
            for picking in order.picking_ids:
                vals = {'trx_type': 'direct_delivery_order'}
                picking.sudo().write(vals)
                if picking.state == 'confirmed':

                    if order.commitment_date:
                        vals.update({'scheduled_date': order.commitment_date})
                    picking.sudo().write(vals)
                if order.order_creation_source == 'vansales':
                    picking.sudo().write(
                        {'picking_driver_id': order.assign_to.id,
                         'forklift_partner_id': order.assign_to.id,
                         'picking_type_id': order.assign_to.van_location.warehouse_id.out_type_id.id,
                         'location_id': order.assign_to.van_location.id
                         })
                    picking.sudo().location_id = order.assign_to.van_location.id
                    picking.action_assign()
            if order.order_creation_source != 'vansales':
                all_moves = order.mapped('order_line.move_ids')
                picking_ids = order._create_all_pickings_from_rule_chain(all_moves)
                vals = {'trx_type': 'direct_delivery_order'}
                if order.commitment_date:
                    vals.update({'scheduled_date': order.commitment_date})
                picking_ids.sudo().write(vals)
                other_picking = picking_ids.filtered(lambda s:not s.is_out_type)
                other_picking.action_confirm()
        return res

    def _create_all_pickings_from_rule_chain(self, initial_moves):
        StockRule = self.env['stock.rule']
        StockMove = self.env['stock.move']
        StockPicking = self.env['stock.picking']
        moves = initial_moves
        picking_ids = self.env['stock.picking']
        while moves:
            next_moves = self.env['stock.move']
            picking_map = {}
            for move in moves:
                rule = move.rule_id
                if not rule:
                    continue
                next_rule = StockRule.search([
                    ('location_src_id', '=', move.location_dest_id.id),
                    ('route_id', '=', rule.route_id.id),
                ], limit=1)
                if not next_rule:
                    continue
                picking_key = (
                    next_rule.picking_type_id.id,
                    next_rule.location_src_id.id,
                    next_rule.location_dest_id.id,
                    move.partner_id.id or False,
                )
                if picking_key not in picking_map:
                    picking = StockPicking.create({
                        'picking_type_id': next_rule.picking_type_id.id,
                        'location_id': next_rule.location_src_id.id,
                        'location_dest_id': next_rule.location_dest_id.id,
                        'origin': move.origin,
                        'move_type': 'direct',
                        'company_id': move.company_id.id,
                        'partner_id': move.partner_id.id or False,
                    })
                    picking_ids += picking
                    picking_map[picking_key] = picking
                else:
                    picking = picking_map[picking_key]
                downstream_move = StockMove.create({
                    'name': move.name,
                    'company_id': move.company_id.id,
                    'product_id': move.product_id.id,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.id,
                    'location_id': next_rule.location_src_id.id,
                    'location_dest_id': next_rule.location_dest_id.id,
                    'procure_method': 'make_to_stock',
                    'picking_type_id': next_rule.picking_type_id.id,
                    'picking_id': picking.id,
                    'state': 'draft',
                    'origin': move.origin,
                    'group_id': move.group_id.id,
                    'rule_id': next_rule.id,
                    'move_orig_ids': [(4, move.id)],
                    'product_packaging_id': move.product_packaging_id.id if move.product_packaging_id else False,
                    'sale_line_id':move.sale_line_id.id or False
                })
                move.move_dest_ids |= downstream_move
                next_moves |= downstream_move
            moves = next_moves.filtered(lambda m: m.state == 'draft')
        return picking_ids



    @api.constrains('po_number', 'partner_id')
    def _check_po_number_unique(self):
        for record in self:
            if not record.po_number or not record.partner_id:
                continue
            duplicate = self.env['sale.order'].search([
                ('partner_id', '=', record.partner_id.id),
                ('po_number', '=', record.po_number.strip()),
                ('id', '!=', record.id)
            ], limit=1)
            if duplicate:
                raise ValidationError("PO Number must be unique for this customer.")

    # @api.constrains('po_number')
    # def _check_po_number_duplication(self):
    #     for record in self:
    #         if record.order_creation_source != 'back_order':
    #             continue
    #         if self.search([('po_number', '=', record.po_number), ('id', '!=', record.id)]):
    #             raise ValidationError("PO Number must be unique!")

    # @api.onchange('po_amount_without_vat_char')
    # def _check_po_without_tax(self):
    #     for order in self:
    #         if order and order.po_amount_without_vat_char and not order.po_amount_without_vat_char.isdigit():
    #             raise ValidationError("Please Put Only Float Value")

    # @api.constrains('po_expiry_date')
    # def _check_po_expiry_date(self):
    #     for record in self:
    #         if record.po_expiry_date and record.po_expiry_date < date.today():
    #             raise ValidationError("PO Expiry Date cannot be before today!")

    # @api.depends_context('lang')
    # @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id')
    # def _compute_tax_totals(self):
    #     return super(SaleOrderExt, self.with_context(is_so_custome_code=True,custom_sale_id=self.ids))._compute_tax_totals()

    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id')
    def _compute_tax_totals(self):
        AccountTax = self.env['account.tax']
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            base_lines += order._add_base_lines_for_early_payment_discount()
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            order.tax_totals = AccountTax.with_context(is_so_custome_code=True,custom_sale_id=order.id)._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )

    @api.depends('assign_to')
    def _compute_fiscal_position_id(self):
        for order in self:
            assign_to_id = order.assign_to.state_id
            customer_fiscal_position_id = order.partner_id.property_account_position_id
            fiscal_position_id = self.env['account.fiscal.position'].search([('state_ids','in',assign_to_id.id)],limit=1)
            if fiscal_position_id and not customer_fiscal_position_id:
                order.fiscal_position_id = fiscal_position_id
            else:
                order.fiscal_position_id = customer_fiscal_position_id or False

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.assign_to:
            res['ref'] = self.po_number or ''
        return res
class AccountTaxInh(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        res = super(AccountTaxInh, self)._get_tax_totals_summary(base_lines, currency, company, cash_rounding)
        if self.env.context.get('is_so_custome_code'):
            sale_order = self.env['sale.order'].sudo().browse([self.env.context.get('custom_sale_id')])
            if sale_order and sale_order.order_line:
                amount = sum(sale_order.order_line.mapped('price_subtotal'))
                total_amount = sum(sale_order.order_line.mapped('price_total'))
                for so_line in res.get('subtotals'):
                    for tax_line in so_line.get('tax_groups'):
                        percentage = 100
                        if tax_line.get('base_amount_currency') != 0.0:
                            percentage = (tax_line.get('tax_amount_currency') / tax_line.get('base_amount_currency')) * 100
                        # percentage = (tax_line.get('tax_amount_currency') / tax_line.get('base_amount_currency')) * 100
                        tax_val = (amount * percentage) / 100

                        tax_line.update({
                            'tax_amount_currency': tax_val,
                            'tax_amount': tax_val,
                            'base_amount': amount,
                            'base_amount_currency': amount,
                        })
                    so_line.update({
                        'base_amount': amount,
                        'base_amount_currency': amount,
                    })
                res.update({
                    'total_amount_currency': total_amount,
                    'total_amount': total_amount,
                })
        return res