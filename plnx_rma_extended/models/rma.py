# -*- coding: utf-8 -*-

from odoo import models, fields, api,Command,_
# from odoo.tests import Form
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import timedelta

from odoo.osv import expression
import logging
import re

_logger = logging.getLogger(__name__)

rma_return_caused_by = [('admin_error', 'Administrative Error'),
                        ('customer_error', 'Customer'),
                        ('logistic_error', 'Logistic'),
                        ('order_entry_error', 'Order Entry'),
                        ('sales_error', 'Sales'),
                        ('warehouse_error', 'Warehouse'),
                        ]


class RMA(models.Model):
    _inherit = 'rma'

    @api.onchange('move_id')
    def _onchange_move_id(self):
        for rec in self:
            rec.picking_id = rec.move_id.picking_id.id

    # return_reason_id = fields.Many2one(
    #     comodel_name="rma.return.reason",
    #     string="Return Reason",
    #     copy=False,
    #     tracking=True,
    #     required=False,
    # )

    # channel = fields.Selection(related="partner_id.channel", string="Channel")
    partner_channel_id = fields.Many2one('channel.channel', related="partner_id.partner_channel_id", string="Channel")
    emirate = fields.Char(related="partner_id.emirate", string="Emirate ID")

    # return_reason_type_id = fields.Many2one(related="return_reason_id.type", string="Type", store=True)

    # return_caused_by = fields.Many2one(
    #     comodel_name="res.users",
    return_caused_by = fields.Selection(
            selection=rma_return_caused_by,
        string="Return Caused By",
        copy=False,
        tracking=True,

    )
    # return_caused_by_ids = fields.Many2many('rma.return.caused.config', compute="_compute_return_caused_by_ids",
    #                                      string="Return Reason")

    # @api.depends('crm_team_id')
    # def _compute_return_caused_by_ids(self):
    #     for rec in self:
    #         rec.return_caused_by_ids = None
    #         if rec.crm_team_id:
    #             domains = self.env['rma.return.caused.by'].search([('sales_teams', '=', rec.crm_team_id.id)])
    #             return_caused_by_ids = domains.mapped('return_caused_by_ids')
    #             rec.return_caused_by_ids= [(6, 0, return_caused_by_ids.ids)]

    return_caused_by_id = fields.Many2one('rma.return.caused.config', required=False,)
    # return_caused_by = fields.Many2many('rma.return.caused.config',
    #                                     string="Return Caused By",
    #                                     copy=False,
    #                                     tracking=True,
    #                                     required=True,
    #                                     )

    barcode = fields.Char(
        string='Barcode',
        copy=False,
        tracking=True,
        related='product_id.barcode',
        readonly=True,
        store=True
    )

    collection_request_date = fields.Date(
        string="Collection Request Date",
        copy=False,
        tracking=True,
    )

    customer_account = fields.Many2one(
        comodel_name="account.account",
        string="Customer Account",
        copy=False,
        tracking=True,
        related='partner_id.property_account_receivable_id'
    )

    remarks = fields.Text(
        string="Remarks",
        copy=False,
        tracking=True,
    )

    grv_no = fields.Char(
        string="GRV No",
        copy=False,
        tracking=True,
    )

    grv_amount = fields.Float(
        string="GRV Amount",
        copy=False,
        tracking=True,
    )

    expiry_date = fields.Date(
        string="Expiry Date",
        copy=False,
        tracking=True,
    )

    product_line_ids = fields.One2many('rma.product.line', 'rma_id', 'Product Lines',compute="compute_line_ids",store=True,readonly=False)
    line_ids = fields.One2many('rma.line', 'rma_id', 'Lines',compute="compute_line_ids",store=True,readonly=False)
    invoice_line_ids = fields.One2many('rma.invoice.line', 'rma_id', 'Invoice Lines',store=True,readonly=False)
    rma_type = fields.Selection([('base_on_product', 'Base on product'), ('base_on_delivery', 'Base on Delivery'), ('base_on_invoice', 'Base on Invoice')],
                                default='base_on_product', string="RMA Type", required=True)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        if 'rma_type' in res and res['rma_type'].get('selection'):
            res['rma_type']['selection'] = [
                (k, v) for k, v in res['rma_type']['selection']
                if k != 'base_on_delivery'
            ]
        return res

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        domain=(
            "["
            "    ('state', 'in', ['posted']),"
            "    ('move_type', 'in', ['out_invoice']),"
            "    ('partner_id', 'child_of', commercial_partner_id),"
            "]"
        ),
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        domain=[("type", "in", ["consu", "product"])],
        compute="_compute_product_id",
        store=True,
        readonly=False,
    )
    product_uom = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM",
        required=False,
        default=lambda self: self.env.ref("uom.product_uom_unit").id,
        compute="_compute_product_uom",
        store=True,
        readonly=False,
    )
    reception_move_ids = fields.Many2many(
        comodel_name="stock.move",
        string="Reception move",
        copy=False,
    )
    operation_type = fields.Selection(related="operation_id.operation_type",store=True)
    outlet_name = fields.Char(related="partner_id.outlet_short_name",string="Outlet Name", required=False)
    outlet_short_name = fields.Char(related="partner_id.outlet_short_name",string="Outlet")
    customer_account = fields.Char(string="Customer Account",compute="compute_customer_account",store=True)
    division = fields.Selection([
        ('food', 'Food'),
        ('non_food', 'Non-Food'),
        ('mars', 'MARS')
    ], string='Division')

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id
    )
    approved_by = fields.Many2one('res.users',string="Approved By")
    is_set_draft = fields.Boolean(string="Is Set Draft",copy=False)
    delivery_required = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Delivery Required",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ('submit','Submitted'),
            ("confirmed", "Confirmed"),
            ("received", "Received"),
            ("waiting_return", "Waiting for return"),
            ("waiting_replacement", "Waiting for replacement"),
            ("refunded", "Refunded"),
            ("returned", "Returned"),
            ("replaced", "Replaced"),
            ("finished", "Finished"),
            ("locked", "Locked"),
            ("cancelled", "Canceled"),
            ('product_under_inspection', 'Product Under Inspection'),
        ],
        default="draft",
        copy=False,
        tracking=True,
    )
    sales_person_id = fields.Many2one('res.partner',string="Sales Person",compute='_compute_sales_person_id',store=True, readonly=False, precompute=True)
    customer_worker_ids = fields.Many2many('res.partner',string="Customer Workers",compute="compute_customer_worker_ids",store=True)

    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        if self.invoice_id:
            self.grv_no = self.invoice_id.name
            self.partner_invoice_id = self.invoice_id.partner_id
            self.partner_shipping_id = self.invoice_id.partner_shipping_id
            self.sales_person_id  = self.invoice_id.assign_to
            self.origin = self.invoice_id.invoice_origin


    @api.depends('partner_id')
    def compute_customer_worker_ids(self):
        for record in self:
            customer_worker_ids = []
            if record.partner_id:
                worker_ids = self.env['customer.mapping'].sudo().search([('customer_id','=',record.partner_id.id)]).mapped('customer_map_lines').mapped('worker_id')
                if worker_ids:
                    customer_worker_ids = worker_ids.ids
            record.customer_worker_ids = customer_worker_ids


    @api.depends('rma_type','picking_id','partner_id')
    def _compute_sales_person_id(self):
        for rec in self:
            sales_person_id = False
            if rec.rma_type == 'base_on_delivery':
                if rec.picking_id and rec.picking_id.sale_id and rec.picking_id.sale_id.assign_to:
                    sales_person_id =rec.picking_id.sale_id.assign_to.id
            if rec.rma_type == 'base_on_invoice':
                if rec.invoice_id:
                    sales_person_id = rec.invoice_id.invoice_user_id.partner_id.id if rec.invoice_id.invoice_user_id and rec.invoice_id.invoice_user_id.partner_id else False
            rec.sales_person_id = sales_person_id
            # if not rec.sales_person_id and sales_person_id:
            #     rec.sales_person_id = sales_person_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        refund_operation_id = self.env['rma.operation'].sudo().search([('operation_type','=','refund')],limit=1)
        if refund_operation_id:
            res['operation_id'] = refund_operation_id.id
        return res

    def action_submit_rma(self):
        for record in self:
            record.state = 'submit'

    def action_set_to_draft_button(self):
        for record in self:
            if record.reception_move_ids:
                pickings = record.reception_move_ids.mapped('picking_id').filtered(lambda s:s.state not in ['done','cancel'])
                # pickings.sudo().write({'state':'draft'})
                for picking in pickings:
                    picking.action_cancel()
            elif record.reception_move_id:
                pickings = record.reception_move_id.mapped('picking_id').filtered(lambda s:s.state not in ['done','cancel'])
                # pickings.sudo().write({'state':'draft'})
                for picking in pickings:
                    picking.action_cancel()
            record.state = 'draft'
            record.is_set_draft = True

    @api.depends('partner_id')
    def compute_customer_account(self):
        for record in self:
            if record.partner_id and record.partner_id.bank_ids:
                account_number_list = record.partner_id.bank_ids.mapped('acc_number')
                record.customer_account = ','.join(account_number_list)
            else:
                record.customer_account = False

    @api.depends("location_id","grv_amount")
    def _compute_warehouse_id(self):
        for record in self.filtered("location_id"):
            record.warehouse_id = record.location_id.warehouse_id.id
            # record.warehouse_id = self.env["stock.warehouse"].search(
            #     [("rma_loc_id", "parent_of", record.location_id.id)], limit=1
            # )
            # conf_grv_amount = float(self.env['ir.config_parameter'].sudo().get_param('plnx_rma_extended.grv_amount') or 50)
            # if not record.warehouse_id and record.grv_amount <= conf_grv_amount and record.location_id:
            #     record.warehouse_id = record.location_id.warehouse_id.id


    @api.onchange('rma_type')
    def onchange_rma_type(self):
        if self.rma_type == 'base_on_product':
            self.picking_id = False
            self.invoice_id = False
        elif self.rma_type == 'base_on_invoice':
            self.product_id = False
            self.picking_id = False
            self.product_line_ids = None
        elif self.rma_type == 'base_on_delivery':
            self.product_id = False
            self.product_line_ids = None

    @api.depends('picking_id','invoice_id')
    def compute_line_ids(self):
        for record in self:
            line_val_list = [(5, 0, 0)]
            if record.rma_type == 'base_on_delivery':
                for move in record.picking_id.move_ids:
                    line_val_list.append(
                        Command.create({'move_id': move.id, 'product_id': move.product_id.id, 'product_uom_qty': move.quantity,'product_uom_id': move.product_uom.id}))
            if record.rma_type == 'base_on_invoice' and not record.invoice_line_ids:
                for line in record.invoice_id.invoice_line_ids:
                    line_val_list.append(
                        Command.create({'product_id': line.product_id.id,
                                        'product_uom_qty': line.quantity,
                                        'product_uom_id': line.product_uom_id.id,
                                        'price_unit':line.price_unit,
                                        'move_line_id': line.id,
                                        'analytic_distribution':line.analytic_distribution,
                                        'product_packaging_price':line.product_packaging_price,
                                        'exercise_price':line.exercise_price,
                                        'discount':line.discount,
                                        'tax_id':[(4,tax.id) for tax in line.tax_ids],
                                        }))
            elif record.rma_type == 'base_on_invoice' and record.invoice_line_ids and len(record.invoice_line_ids) > 0:
                for line in record.invoice_line_ids:
                    line_val_list.append(
                        Command.create({'product_id': line.product_id.id,
                                        'product_uom_qty': line.product_uom_qty,
                                        'product_uom_id': line.product_uom_id.id,
                                        'price_unit':line.price_unit,
                                        'move_line_id': line.move_line_id.id,
                                        'analytic_distribution':line.analytic_distribution,
                                        'product_packaging_price':line.product_packaging_price,
                                        'exercise_price':line.exercise_price,
                                        'discount':line.discount,
                                        'tax_id':[(4,line.tax_id.id)] if line.tax_id else False,
                                        'return_reason_id': line.return_reason_id.id,
                                        'return_reason_type_id': line.return_reason_type_id.id,
                                        'return_caused_by_id': line.return_caused_by_id.id,
                                        'product_packaging_qty': line.product_packaging_qty,
                                        # 'product_packaging_id': line.product_packaging_id.id,
                                        }))

            record.line_ids = line_val_list

    # Validation business methods
    def _ensure_required_fields(self):
        """This method is used to ensure the following fields are not empty:
        [
            'partner_id', 'partner_invoice_id', 'partner_shipping_id',
            'product_id', 'location_id'
        ]

        This method is intended to be called on confirm RMA action and is
        invoked by:
        rma._check_required_after_draft
        rma.action_confirm
        """
        required = [
            "partner_id",
            "partner_shipping_id",
            "partner_invoice_id",
            "location_id",
        ]
        for record in self:
            desc = ""
            for field in filter(lambda item: not record[item], required):
                field_record = (
                    self.env["ir.model.fields"]
                    .sudo()
                    .search(
                        [
                            ("model_id.model", "=", record._name),
                            ("name", "=", field),
                        ]
                    )
                )
                desc += f"\n{field_record.field_description}"
            if desc:
                raise ValidationError(_("Required field(s):%s") % desc)

    def action_confirm(self):
        super().action_confirm()
        for record in self:
            if record.crm_team_id and record.crm_team_id.team_type == 'van_sale':
                record.auto_confirm_rma_and_picking()
        # for record in self:
        #     conf_grv_amount = float(self.env['ir.config_parameter'].sudo().get_param('plnx_rma_extended.grv_amount') or 50)
        #     if record.delivery_required == 'yes' and record.grv_amount > conf_grv_amount:
        #         if record.rma_type == 'base_on_product' and record.reception_move_id:
        #             record._create_all_pickings_from_rule_chain(record.reception_move_id)
        #         else:
        #             if record.reception_move_ids:
        #                 record._create_all_pickings_from_rule_chain(record.reception_move_ids)

    def _create_all_pickings_from_rule_chain(self,initial_moves):
        moves = initial_moves
        all_moves = self.env['stock.move']
        while moves:
            new_moves = moves._push_apply()
            all_moves |= new_moves
            moves = new_moves
        return all_moves

    # def _create_all_pickings_from_rule_chain(self, initial_moves):
        # StockRule = self.env['stock.rule']
        # StockMove = self.env['stock.move']
        # StockPicking = self.env['stock.picking']
        # moves = initial_moves
        # picking_ids = self.env['stock.picking']
        # while moves:
        #     next_moves = self.env['stock.move']
        #     picking_map = {}
        #     for move in moves:
        #         rule = move.rule_id
        #         if not rule:
        #             continue
        #         next_rule = StockRule.search([
        #             ('location_src_id', '=', move.location_dest_id.id),
        #             ('route_id', '=', rule.route_id.id),
        #         ], limit=1)
        #         if not next_rule:
        #             continue
        #         picking_key = (
        #             next_rule.picking_type_id.id,
        #             next_rule.location_src_id.id,
        #             next_rule.location_dest_id.id,
        #             move.partner_id.id or False,
        #         )
        #         if picking_key not in picking_map:
        #             picking = StockPicking.create({
        #                 'picking_type_id': next_rule.picking_type_id.id,
        #                 'location_id': next_rule.location_src_id.id,
        #                 'location_dest_id': next_rule.location_dest_id.id,
        #                 'origin': move.origin,
        #                 'move_type': 'direct',
        #                 'company_id': move.company_id.id,
        #                 'partner_id': move.partner_id.id or False,
        #             })
        #             picking_ids += picking
        #             picking_map[picking_key] = picking
        #         else:
        #             picking = picking_map[picking_key]
        #         downstream_move = StockMove.create({
        #             'name': move.name,
        #             'company_id': move.company_id.id,
        #             'product_id': move.product_id.id,
        #             'product_uom_qty': move.product_uom_qty,
        #             'product_uom': move.product_uom.id,
        #             'location_id': next_rule.location_src_id.id,
        #             'location_dest_id': next_rule.location_dest_id.id,
        #             'procure_method': 'make_to_stock',
        #             'picking_type_id': next_rule.picking_type_id.id,
        #             'picking_id': picking.id,
        #             'state': 'draft',
        #             'origin': move.origin,
        #             'group_id': move.group_id.id,
        #             'rule_id': next_rule.id,
        #             'move_orig_ids': [(4, move.id)],
        #             'product_packaging_id': move.product_packaging_id.id if move.product_packaging_id else False,
        #         })
        #         move.move_dest_ids |= downstream_move
        #         next_moves |= downstream_move
        #     moves = next_moves.filtered(lambda m: m.state == 'draft')
        # return picking_ids


    # def action_confirm(self):
    #     """Invoked when 'Confirm' button in rma form view is clicked."""
    #     self.ensure_one()
    #     self._ensure_required_fields()
    #     if self.state == "draft":
    #         if self.picking_id and self.line_ids:
    #             reception_move = self._create_receptions_from_picking()
    #         else:
    #             reception_move = self._create_receptions_from_product()
    #         reception_move.picked = True
    #         self.write({"reception_move_ids": reception_move.ids,'reception_move_id': reception_move[0].id, "state": "confirmed","approved_by":self.env.user.id})
    #         self._add_message_subscribe_partner()
    #         self._send_confirmation_email()

    def _create_receptions_from_picking(self):
        self.ensure_one()
        # stock_return_picking_form = Form(
        #     self.env["stock.return.picking"].with_context(
        #         active_ids=self.picking_id.ids,
        #         active_id=self.picking_id.id,
        #         active_model="stock.picking",
        #     )
        # )
        return_wizard = self.env['stock.return.picking'].with_context(
            active_ids=self.picking_id.ids, active_id=self.picking_id.id, active_model='stock.picking'
        ).sudo().create({})
        # return_wizard = stock_return_picking_form.save()
        if self.location_id:
            return_wizard.location_id = self.location_id.id
        move_ids = self.line_ids.mapped('move_id')
        return_wizard.product_return_moves.filtered(
            lambda r: r.move_id not in move_ids
        ).unlink()
        return_lines = return_wizard.product_return_moves
        for return_line in return_lines:
            line = self.line_ids.filtered(lambda s:s.move_id == return_line.move_id)
            return_line.update(
                {
                    "quantity": line.product_uom_qty,
                    # The to_refund field is now True by default, which isn't right in the
                    # RMA creation context
                    "to_refund": False,
                }
            )
        # set_rma_picking_type is to override the copy() method of stock
        # picking and change the default picking type to rma picking type.
        picking_action = return_wizard.with_context(
            set_rma_picking_type=True
        ).action_create_returns()
        picking_id = picking_action["res_id"]
        picking = self.env["stock.picking"].browse(picking_id)
        picking.origin = f"{self.name} ({picking.origin})"
        if self.collection_request_date:
            picking.scheduled_date = self.collection_request_date
        picking.trx_type = 'return_collection'
        if self.delivery_required == 'yes':
            picking.delivery_required = True
        if self.delivery_required == 'no' and self.responsible_worker_id:
            picking.picking_driver_id = self.responsible_worker_id.id
        move = picking.move_ids
        move.priority = self.priority
        return move

    def create_return(self, scheduled_date, qty=None, uom=None):
        """Intended to be invoked by the delivery wizard"""
        group_returns = self.env.company.rma_return_grouping
        if "rma_return_grouping" in self.env.context:
            group_returns = self.env.context.get("rma_return_grouping")
        self._ensure_can_be_returned()
        self._ensure_qty_to_return(qty, uom)
        group_dict = {}
        rmas_to_return = self.filtered("can_be_returned")
        for record in rmas_to_return:
            key = (
                record.partner_shipping_id.id,
                record.company_id.id,
                record.warehouse_id,
            )
            group_dict.setdefault(key, self.env["rma"])
            group_dict[key] |= record
        if group_returns:
            grouped_rmas = group_dict.values()
        else:
            grouped_rmas = rmas_to_return
        for rmas in grouped_rmas:
            origin = ", ".join(rmas.mapped("name"))
            picking_vals = rmas[0]._prepare_returning_picking_vals(origin)
            for rma in rmas:
                if rma.rma_type == 'base_on_delivery':
                    for line in rma.line_ids:
                        picking_vals["move_ids"].append(
                            (0, 0, rma.with_context(line=line)._prepare_returning_move_vals(scheduled_date, qty, uom))
                        )
                else:
                    picking_vals["move_ids"].append(
                        (0, 0, rma._prepare_returning_move_vals(scheduled_date, qty, uom))
                    )
            picking = self.env["stock.picking"].sudo().create(picking_vals)
            for rma in rmas:
                rma.message_post(
                    body=_(
                        'Return: <a href="#" data-oe-model="stock.picking" '
                        'data-oe-id="%(id)d">%(name)s</a> has been created.'
                    )
                    % ({"id": picking.id, "name": picking.name})
                )
            picking.action_confirm()
            picking.action_assign()
            picking.message_post_with_source(
                "mail.message_origin_link",
                render_values={"self": picking, "origin": rmas},
                subtype_id=self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note"),
            )
        rmas_to_return.sudo().write({"state": "waiting_return"})

    # @api.model_create_multi
    # def create(self, vals_list):
    #     records = super(RMA,self).create(vals_list)
    #     for record in records:
    #         if record.crm_team_id and record.crm_team_id.team_type == 'van_sale':
    #             record.auto_confirm_rma_and_picking()
    #     return records

    def auto_confirm_rma_and_picking(self):
        # self.action_confirm()
        picking = self.reception_move_id.picking_id
        picking.sudo().action_assign_driver()
        picking.sudo().action_collect()
        try:
            picking.action_put_in_pack()
        except:
            pass
        try:
            action = picking.sudo().button_validate()
            if self.user_id and self.user_id.user_type == 'sales_user':
                # 2) AUTO-CONFIRM WIZARDS (expiry/backorder/immediate)
                def _expired_lot_cmds(picking):
                    """
                    Build default lot line commands for the expiry wizard.
                    Uses any of life_date/use_date/expiration_date/removal_date to decide expiry.
                    """
                    cmds = []
                    now = fields.Datetime.now()
                    for ml in picking.move_line_ids:
                        lot = ml.lot_id
                        if not lot:
                            continue
                        # consider the earliest relevant expiry-like date
                        exp_dt = lot.use_date or lot.expiration_date or lot.removal_date
                        if exp_dt and exp_dt <= now:
                            cmds.append((0, 0, {
                                'product_id': ml.product_id.id,
                                'name': lot.name or '',
                            }))
                    return cmds

                def _auto_confirm_picking_wizards(action_dict, picking, acting_user):
                    """
                    Follows any wizard actions returned by button_validate and confirms them automatically.
                    Ensures expected context keys (e.g., default_lot_ids) exist for the expiry wizard.
                    """
                    WIZ_METHODS = {
                        'expiry.picking.confirmation': 'process',  # your custom / product_expiry wizard
                        'stock.immediate.transfer': 'process',  # standard
                        'stock.backorder.confirmation': 'process',
                        # or 'process_cancel_backorder' to skip backorders
                    }

                    max_hops = 5
                    while isinstance(action_dict, dict) and action_dict.get(
                            'type') == 'ir.actions.act_window' and max_hops > 0:
                        res_model = action_dict.get('res_model')
                        method = WIZ_METHODS.get(res_model, 'process')

                        # 1) Build a safe context
                        ctx = dict(action_dict.get('context') or {})
                        ctx.update({
                            'active_model': 'stock.picking',
                            'active_id': picking.id,
                            'active_ids': [picking.id],
                        })

                        # 2) Ensure the keys this wizard expects exist
                        if res_model in ('expiry.picking.confirmation', 'confirm.expiry'):
                            # If the action didn't supply default_lot_ids, derive or at least set empty.
                            ctx.setdefault('default_lot_ids', _expired_lot_cmds(picking))
                            # Optional niceties – some implementations read these:
                            ctx.setdefault('default_show_lots', bool(ctx['default_lot_ids']))
                            ctx.setdefault('default_description', 'Auto-confirmed from API')

                        WizardEnv = self.env[res_model].with_context(ctx).with_user(acting_user).sudo()
                        res_id = action_dict.get('res_id')
                        wiz = WizardEnv.browse(res_id) if res_id else WizardEnv.create({})

                        # 3) Call the wizard method. If it still complains about missing keys, retry with hard-safe defaults.
                        try:
                            action_dict = getattr(wiz, method)() or None
                        except KeyError as ke:
                            # Safety net: some custom code does ctx.pop('default_lot_ids') with no default.
                            if str(ke) == "'default_lot_ids'":
                                WizardEnv = WizardEnv.with_context(
                                    {**WizardEnv.env.context, 'default_lot_ids': []})
                                wiz = WizardEnv.browse(res_id) if res_id else WizardEnv.create({})
                                action_dict = getattr(wiz, method)() or None
                            else:
                                raise
                        max_hops -= 1

                    return True

                # run the auto-confirm if a wizard popped
                if isinstance(action, dict) and action.get('type') == 'ir.actions.act_window':
                    _auto_confirm_picking_wizards(action, picking, self.env.user)

                if not self.refund_id:
                    refund_id = self.env['account.move'].sudo().search([('invoice_origin','=',self.name)], limit=1)
                    if refund_id:
                        self.refund_id = refund_id.id
            if self.user_id and self.user_id.user_type == 'sales_user' and self.partner_id and self.partner_id.customer_type == 'cash':
                self._create_refund_for_rma()
            # elif self.user_id and self.user_id.user_type == 'sales_user' and self.partner_id and self.partner_id.customer_type == 'credit' and self.partner_id.is_credit_hold == True:
            #     self._create_refund_for_rma()
        except Exception as e:
            _logger.info("what is happend here")
            _logger.info(str(e))
            error_message = str(e)
            if self.user_id and self.user_id.user_type == 'sales_user':
                if "The entry" in error_message and "must be in draft." in error_message:
                    expiry_refund_id = self.env['account.move'].sudo().search([('invoice_origin', '=', self.name)])
                    if expiry_refund_id and not self.refund_id:
                        self.refund_id = expiry_refund_id.id
                        self.sudo().write({"refund_id": expiry_refund_id.id})
                        try:
                            if self.partner_id and self.partner_id.customer_type != 'credit':
                                self._create_refund_for_rma()
                        except Exception as e:
                            _logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                            _logger.info(str(e))

    def _create_refund_for_rma(self):
        try:
            company_id = self.refund_id.company_id.id
            journal = False

            custodian_id = self.env['custodian'].sudo().search(
                [("responsible_custodian", "=", self.sales_person_id.id)], limit=1)
            for one in custodian_id.journal_ids:
                if one.type == "cash":
                    journal = one
            if not journal:
                journal = self.env['account.journal'].sudo().search([
                    ('type', '=', 'cash'),
                ])
            journal_id = journal.id
            ctx = {
                'active_model': 'account.move.line',
                'active_ids': self.refund_id.line_ids.ids,
                'company_id': company_id,
                'allowed_company_ids': [company_id]
            }

            account_payment_register = self.env['account.payment.register'].sudo().with_context(**ctx).sudo().create({
                'journal_id': journal_id,
                'responsible_id': self.sales_person_id.id,
                'group_payment': True,
                'custodian_id': custodian_id.id,
            })

            account_payment_register.action_create_payments()
        except UserError as ue:
            error_message = str(ue)

            if "The entry" in error_message and "must be in draft." in error_message:
                def _extract_move_id_from_error(msg: str):
                    """
                    Parse '(id 598930)' or 'id 598930' from a UserError message.
                    """
                    m = re.search(r'\(id\s*(\d+)\)', msg)
                    if not m:
                        m = re.search(r'\bid\s*([0-9]{3,})\b', msg)
                    return int(m.group(1)) if m else None

                def _link_payment_move_to_invoice(move_id, invoice, user):
                    """
                    Given an account.move ID for a payment entry, reconcile it with the (posted) invoice.
                    Works on v14+ where payments are account.payment + move, or pure move fallback.
                    """
                    if not move_id or not invoice:
                        return False

                    Move = self.env['account.move'].sudo()
                    move = Move.browse(int(move_id))
                    if not move.exists():
                        return False

                    # Find account.payment if present
                    payment = False
                    if 'payment_id' in move._fields and move.payment_id:
                        payment = move.payment_id
                    elif 'account.payment' in self.env:
                        payment = self.env['account.payment'].sudo().search(
                            [('move_id', '=', move.id)], limit=1)

                    # Ensure both documents are posted
                    if invoice.state != 'posted':
                        invoice.with_user(user.id).sudo().action_post()

                    if payment and hasattr(payment, 'state') and payment.state != 'posted':
                        payment.with_user(user.id).sudo().action_post()
                    elif move.state != 'posted':
                        move.with_user(user.id).sudo().action_post()

                    # Company sanity check (avoid cross-company reconciliation surprises)
                    if move.company_id.id != invoice.company_id.id:
                        raise UserError(
                            "Payment company differs from invoice company; cannot reconcile automatically.")

                    # Grab open receivable/payable lines on both sides
                    def _is_rp(line):
                        at = getattr(line.account_id, 'account_type', False) or getattr(
                            line.account_id, 'internal_type', False)
                        return at in (
                            'asset_receivable', 'liability_payable', 'receivable', 'payable')

                    inv_lines = invoice.line_ids.filtered(lambda l: _is_rp(l) and not l.reconciled)
                    pay_lines = move.line_ids.filtered(lambda l: _is_rp(
                        l) and not l.reconciled and l.partner_id.id == invoice.partner_id.id)

                    if not inv_lines or not pay_lines:
                        # Nothing to reconcile (maybe already done or wrong lines)
                        return False

                    (inv_lines + pay_lines).with_user(user.id).sudo().reconcile()
                    invoice.matched_payment_ids = [(4, payment.id)]
                    invoice.sudo().write({"matched_payment_ids": [(4, payment.id)]})
                    return True

                move_id = _extract_move_id_from_error(error_message)
                # reconcile that existing payment JE with your refund invoice
                _link_payment_move_to_invoice(move_id, self.refund_id, self.env.user)
            # elif "The Customer Reference" in error_message and "is already used for this customer" in error_message:
            #     pass

    def _prepare_returning_move_vals(self, scheduled_date, quantity=None, uom=None):
        result_package_id = False
        if self.env.context.get('line'):
            line =self.env.context.get('line')
            move = self.reception_move_ids.filtered(lambda s:s.origin_returned_move_id == line.move_id)
            move_orig_ids = [(4, move.id)]
            product_uom_qty = line.product_uom_qty
            product_uom  = line.product_uom_id.id
            product_id = line.product_id
            return_reason_id = line.return_reason_id.id
            product_packaging_id = line.product_packaging_id.id or False
            product_packaging_qty = line.product_packaging_qty
            result_package_id = line.quant_package_id.id or False
        else:
            move_orig_ids = [(4, self.reception_move_id.id)]
            product_uom_qty = quantity or self.product_uom_qty
            product_uom = self.product_uom.id
            product_id = self.product_id
            return_reason_id = None
            product_packaging_id = False
            product_packaging_qty = 0.0
        self.ensure_one()
        return {
            "product_id": product_id.id,
            "name": product_id.with_context(
                lang=self.partner_shipping_id.lang or "en_US"
            ).display_name,
            "product_uom_qty": product_uom_qty,
            "product_uom": uom and uom.id or product_uom,
            "location_id": self.location_id.id,
            "location_dest_id": self.reception_move_id.location_id.id,
            "date": scheduled_date,
            "rma_id": self.id,
            "move_orig_ids": move_orig_ids,
            "company_id": self.company_id.id,
            'return_reason_id': return_reason_id.id or None ,
            'product_packaging_id': product_packaging_id,
            'product_packaging_qty': product_packaging_qty,
            'result_package_id': result_package_id
        }

    @api.depends("product_uom_qty", "delivered_qty","rma_type")
    def _compute_remaining_qty(self):
        """Compute 'remaining_qty' and 'remaining_qty_to_done' fields.

        remaining_qty: is used to set a default quantity of replacing
        or returning of product to the customer.

        remaining_qty_to_done: the aim of this field to control when the
        RMA cam be set to 'delivered' state. An RMA with
        remaining_qty_to_done <= 0 can be set to 'delivery'. It is used
        in stock.move._action_done method of stock.move and
        rma.extract_quantity.
        """
        for r in self:
            if r.rma_type == 'base_on_delivery':
                r.remaining_qty = sum(r.line_ids.mapped('product_uom_qty')) - r.delivered_qty
            else:
                r.remaining_qty = r.product_uom_qty - r.delivered_qty

    @api.depends(
        "delivery_move_ids",
        "delivery_move_ids.state",
        "delivery_move_ids.scrapped",
        "delivery_move_ids.product_uom_qty",
        "delivery_move_ids.quantity",
        "delivery_move_ids.product_uom",
        "product_uom",
    )
    def _compute_delivered_qty(self):
        """Compute 'delivered_qty' and 'delivered_qty_done' fields.

        delivered_qty: represents the quantity delivery or to be
        delivery. For each move in delivery_move_ids the quantity done
        is taken, if it is empty the reserved quantity is taken,
        otherwise the initial demand is taken.

        delivered_qty_done: represents the quantity delivered and done.
        For each 'done' move in delivery_move_ids the quantity done is
        taken. This field is used to control when the RMA cam be set
        to 'delivered' state.
        """
        for record in self:
            if record.rma_type == 'base_on_delivery':
                delivered_qty = 0.0
                for move in record.delivery_move_ids.filtered(
                        lambda r: r.state != "cancel" and not r.scrapped
                ):
                    line = record.line_ids.filtered(lambda s:s.product_id == move.product_id)
                    if move.quantity:
                        quantity = move.product_uom._compute_quantity(
                            move.quantity, line.product_uom_id or record.product_uom
                        )
                        delivered_qty += quantity
                    elif move.product_uom_qty:
                        delivered_qty += move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom_id or record.product_uom
                        )
            else:
                delivered_qty = 0.0
                for move in record.delivery_move_ids.filtered(
                    lambda r: r.state != "cancel" and not r.scrapped
                ):
                    if move.quantity:
                        quantity = move.product_uom._compute_quantity(
                            move.quantity, record.product_uom
                        )
                        delivered_qty += quantity
                    elif move.product_uom_qty:
                        delivered_qty += move.product_uom._compute_quantity(
                            move.product_uom_qty, record.product_uom
                        )
            record.delivered_qty = delivered_qty

    def action_print_rma_receipt(self):
        if self.state == 'draft':
            raise UserError('Please Confirm RMA Receipt')
        return self.env.ref('plnx_rma_extended.action_rma_record_receipt_report').report_action(self.id)

    def get_rma_receipt(self):
        last_picking = self.env['stock.picking']
        if self.operation_id and self.operation_id.operation_type == 'replace':
            picking = self.delivery_move_ids.mapped("picking_id")
            while picking:
                if len(picking) == 1:
                    last_picking = picking
                    picking = picking._get_next_transfers()
                else:
                    for p in picking:
                        last_picking = p
                        picking = picking._get_next_transfers()
        else:
            picking = self.reception_move_id.picking_id
            while picking:
                if len(picking) == 1:
                    last_picking = picking
                    picking = picking._get_next_transfers()
                else:
                    for p in picking:
                        last_picking = p
                        picking = picking._get_next_transfers()
        return last_picking

    def _prepare_picking_vals(self):

        if self.rma_type == 'base_on_invoice':
            move_lines = []
            move_line_records = []
            for product in self.line_ids.filtered(lambda x:x.product_id.type != 'service'):
                sale_order = self.invoice_id.sale_id if self.invoice_id.sale_id else False
                lot_ids = False
                if sale_order:
                    # Get delivery pickings
                    delivery_pickings = sale_order.picking_ids.filtered(
                        lambda p: p.picking_type_code in ['outgoing', 'dropship'] and p.state in ['done','loaded_dispatched'])

                    # Get stock move lines with lot info
                    lot_ids = delivery_pickings.mapped('move_line_ids').filtered(
                        lambda x: x.product_id.id == product.product_id.id).mapped('lot_id')

                move_lines.append((
                    0,
                    0,
                    {
                        "product_id": product.product_id.id,
                        "name": product.product_id.name
                                or product.product_id.with_context(lang=self.partner_id.lang or "en_US").display_name,
                        "location_id": self.partner_shipping_id.property_stock_customer.id,
                        "location_dest_id": self.location_id.id,
                        "product_uom_qty": product.product_uom_qty,  # This assumes same qty for each
                        **({'route_ids': [(6, 0,
                                           self.warehouse_id.rma_route_id.ids)], } if self.warehouse_id and self.warehouse_id.rma_route_id and self.crm_team_id and self.crm_team_id.team_type != 'van_sale' else {})
                    },
                ))

                if lot_ids:
                    try:
                        for one_lot in lot_ids:
                            if product.return_reason_id and product.return_reason_id.is_salable != True:
                                one_lot.sudo().is_salable = False
                    except:
                        pass
                    move_line_records.append((0, 0, {
                        "product_id": product.product_id.id,
                        "lot_id": lot_ids[0].id if lot_ids else False,
                        "qty_done": product.product_uom_qty,
                        "product_uom_id": product.product_id.uom_id.id,
                        "location_id": self.partner_shipping_id.property_stock_customer.id,
                        "location_dest_id": self.location_id.id,
                    }))
            picking_driver_id = False
            if self.crm_team_id and self.crm_team_id.team_type == 'van_sale' and self.responsible_worker_id:
                picking_driver_id = self.responsible_worker_id.id
            return {
                "picking_type_id": self.warehouse_id.rma_in_type_id.id,
                "origin": self.name,
                "partner_id": self.partner_shipping_id.id,
                "location_id": self.partner_shipping_id.property_stock_customer.id,
                "location_dest_id": self.location_id.id,
                "move_ids_without_package": move_lines,
                "move_line_ids_without_package": move_line_records,
                "picking_driver_id": picking_driver_id,
                "trx_type": 'return_collection'
            }
        else:
            res = super()._prepare_picking_vals()
            res['move_ids'] = []
            res['move_line_ids'] = []
            res['trx_type'] = 'return_collection'
            if self.delivery_required == 'yes':
                res['delivery_required'] = True
            if self.delivery_required == 'no' and self.responsible_worker_id:
                res['picking_driver_id'] = self.responsible_worker_id.id
            if self.crm_team_id and self.crm_team_id.team_type == 'van_sale' and self.responsible_worker_id:
                res['picking_driver_id'] = self.responsible_worker_id.id
            if self.collection_request_date:
                res['scheduled_date'] = self.collection_request_date
            for line in self.product_line_ids:
                lot_id = False
                lot = False
                internal_reference = False
                expiration_date = False
                _logger.info("--------------------- before lot ------------")
                if line.lot_number:
                    _logger.info("--------------------- inside if ------------ ", line.lot_number)

                    lot = self.env['stock.lot'].search([
                        ('name', '=', line.lot_number),
                        ('product_id', '=', line.product_id.id)
                    ], limit=1)
                    if not lot:
                        _logger.info("--------------------- not lot ------------")

                        lot = self.env['stock.lot'].sudo().create({
                            'name': line.lot_number,
                            'product_id': line.product_id.id,
                            'production_date' : line.production_date or False
                        })
                    # if lot.expiration_date:
                    #     _logger.info("--------------------- inside lot expiration lot ------------ ", lot.expiration_date)
                    #
                    #     expiration_date = lot.expiration_date
                    if line.production_date:
                        expiration_date = line.production_date + timedelta(days=line.product_id.expiration_time)
                        lot.expiration_date = expiration_date
                        _logger.info("--------------------- elif calc line expiration date ------------", expiration_date)

                    if expiration_date:
                        internal_reference = expiration_date.strftime('%Y%m')
                    lot_id = lot.id
                elif line.production_date:
                    _logger.info("--------------------- inside big elif ------------")
                    expiration_date = line.production_date + timedelta(days=line.product_id.expiration_time)
                    lot_name = expiration_date.strftime('%Y%m')
                    internal_reference = expiration_date.strftime('%Y%m')
                    existing_lot = self.env['stock.lot'].search([
                        '|', ('name', '=', lot_name), ('production_date', '=', line.production_date),
                        ('product_id', '=', line.product_id.id)], limit=1)
                    if existing_lot:
                        _logger.info("--------------------- inside elif first if ------------")

                        lot_id = existing_lot.id
                    else:
                        _logger.info("--------------------- inside elif not exsisitng ------------")

                        lot = self.env['stock.lot'].sudo().create({
                            'name': lot_name,
                            'product_id': line.product_id.id,
                            'production_date': line.production_date,
                            'expiration_date': expiration_date
                        })
                        if lot:
                            _logger.info("--------------------- after create second lot ------------")

                            lot_id= lot.id
                try:
                    if lot:
                        if line.return_reason_id and line.return_reason_id.is_salable != True:
                            lot.sudo().is_salable = False
                except:
                    pass
                res['move_ids'].append(
                    (
                        0, 0, {
                            'product_id': line['product_id'].id,
                            'name': line['product_id'].with_context(
                                lang=self.partner_id.lang or "en_US"
                            ).display_name,
                            'location_id': self.partner_shipping_id.property_stock_customer.id,
                            'location_dest_id': self.location_id.id,
                            'product_uom_qty': line['product_uom_qty'],
                            'return_reason_id': line['return_reason_id'].id,
                            'product_packaging_id' : line['product_packaging_id'].id or False,
                            'product_packaging_qty' : line['product_packaging_qty'],
                            # 'move_line_ids': [(0, 0, {
                            #     'product_id': line['product_id'].id,
                            #     'location_id': self.partner_shipping_id.property_stock_customer.id,
                            #     'location_dest_id': self.location_id.id,
                            #     'product_uom_id': line['product_uom_id'].id,
                            #     'quantity': line['product_uom_qty'],
                            #     'lot_id': lot_id,
                            #     'production_date' : line['production_date'] or False,
                            #     'result_package_id' : line['quant_package_id'].id or False,
                            #     'expiration_date' : expiration_date,
                            #     'internal_reference' : internal_reference
                            # })],
                            **({'route_ids': [(6, 0, self.warehouse_id.rma_route_id.ids)],} if self.warehouse_id and self.warehouse_id.rma_route_id and self.crm_team_id and self.crm_team_id.team_type != 'van_sale' else {})
                        }
                    )
                )
                res['move_line_ids'].append((0, 0, {
                                'product_id': line['product_id'].id,
                                'location_id': self.partner_shipping_id.property_stock_customer.id,
                                'location_dest_id': self.location_id.id,
                                'product_uom_id': line['product_uom_id'].id,
                                'quantity': line['product_uom_qty'],
                                'lot_id': lot_id,
                                'production_date' : line['production_date'] or False,
                                'result_package_id' : line['quant_package_id'].id or False,
                                'expiration_date' : expiration_date,
                                'internal_reference' : internal_reference
                            }))
        return res

    def _prepare_refund_line_vals(self):
        # Override the base RMA method
        """Hook method for preparing a refund line Form.

        This method could be override in order to add new custom field
        values in the refund line creation.

        invoked by:
        rma.action_refund
        """
        self.ensure_one()
        refund_lines = []
        if self.rma_type in ['base_on_delivery','base_on_invoice']:
            for line in  self.line_ids:
                vals = {
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'price_unit': line.price_unit or line.product_id.lst_price,
                    'rma_id': line.rma_id.id,
                }
                if self.rma_type in ['base_on_invoice']:
                    vals.update({
                        'product_packaging_price': line.product_packaging_price,
                        'exercise_price': line.exercise_price,
                        'analytic_distribution': line.analytic_distribution,
                        'discount': line.discount,
                        'tax_ids': [(4, tax.id) for tax in line.tax_id],
                    })
                refund_journal_id = self.env['account.journal'].sudo().search(
                    [('type', '=', 'sale'), ('name', 'ilike', 'Customer Invoices')], limit=1)
                if refund_journal_id and refund_journal_id.default_rma_account_id:
                    vals['account_id'] = refund_journal_id.default_rma_account_id.id
                refund_lines.append((0, 0, vals))
        elif self.rma_type == 'base_on_product':
            for line in self.product_line_ids:
                price_unit = line.product_id.list_price
                pricelist_id = self.partner_id.property_product_pricelist
                if pricelist_id:
                    item = pricelist_id.item_ids.filtered(lambda s:s.product_tmpl_id == line.product_id.product_tmpl_id)
                    if item and item.fixed_price:
                        price_unit = item.fixed_price
                if line.price_unit:
                    price_unit = line.price_unit
                # last_invoice_line = self.env['account.move.line'].search([
                #     ('product_id', '=', line.product_id.id),
                #     ('move_id.partner_id', '=', line.partner_id.id),
                #     ('move_id.move_type', 'in', ['out_invoice']),
                #     ('move_id.state', '=', 'posted'),
                # ], order='create_date DESC', limit=1)
                # if last_invoice_line:
                #     last_sale_price = last_invoice_line.price_unit
                #     print(f"Last sale price for product {line.product_id.name}: {last_sale_price}")
                # else:
                #     last_sale_price = 0
                #     print("No invoice found for this product. so refund will take lst price of product (%s)"%(line.product_id.name))

                vals = {
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'product_uom_id': line.product_uom_id.id,
                    # 'price_unit': last_sale_price or line.product_id.lst_price,
                    'exercise_price': line.excise_tax,
                    'price_unit': price_unit,
                    'rma_id': line.rma_id.id,
                }
                refund_journal_id = self.env['account.journal'].sudo().search(
                    [('type', '=', 'sale'), ('name', 'ilike', 'Customer Invoices')], limit=1)
                if refund_journal_id and refund_journal_id.default_rma_account_id:
                    vals['account_id'] = refund_journal_id.default_rma_account_id.id
                refund_lines.append((0, 0, vals))


        return refund_lines
        # return {
        #     "product_id": self.product_id.id,
        #     "quantity": self.product_uom_qty,
        #     "product_uom_id": self.product_uom.id,
        #     "price_unit": self.product_id.lst_price,
        #     "rma_id": self.id,
        # }

    def _prepare_refund_vals(self, origin=False):
        res = super()._prepare_refund_vals(origin)
        res['is_rma_refund'] = True
        res['bill_date'] = self.expiry_date
        if (
            self.env.context.get("from_rma_server_action", False)
            and self.reception_move_id
            and self.reception_move_id.state == "done"
            and self.reception_move_id.picking_id.date_done
        ):
            received_dt = self.reception_move_id.picking_id.date_done
            res['invoice_date'] = received_dt
            res['invoice_date_due'] = received_dt
            res['date'] = received_dt
            res['delivery_date'] = received_dt
        # res['ref'] = self.grv_no
        res['ref'] = self.name
        return res

    def _server_action_fix_rma_refund_and_svl_vals(self):
        import logging
        _logger = logging.getLogger(__name__)
        env = self.env

        def _get_all_next_pickings(picking):
            next_picking_ids = env['stock.picking']
            while picking:
                if len(picking) == 1:
                    next_picking_ids |= picking
                    picking = picking._get_next_transfers()
                else:
                    for p in picking:
                        next_picking_ids |= p
                        picking = picking._get_next_transfers()
            return next_picking_ids

        def _get_correct_unit_cost(svl):
            move = svl.stock_move_id
            if move.product_id.lot_valuated:
                # unit_cost = {lot: lot.standard_price for lot in move.lot_ids}
                unit_cost = svl.lot_id.standard_price if svl.lot_id else move.product_id.standard_price
            else:
                unit_cost = move.product_id.standard_price
            if move.product_id.cost_method != 'standard':
                unit_cost = move._get_price_unit()  # May be negative (i.e. decrease an out move).
                unit_cost = unit_cost.get(svl.lot_id)
            return unit_cost

        def _get_rma_lines_cogs_mapping(rma, invoices):
            """Return proportional COGS value from invoices related to original source document (sales order or transfer)"""
            rma_line_cogs_map = {}
            # for invoice in invoices:
            for line in rma.line_ids:
                total_cost = 0
                total_qty = 0
                product = line.product_id
                qty = line.product_uom_qty

                # expense lines = COGS  TODO: VERIFY THIS LOGIC
                # Compute proportional COGS value for a product qty from a set of posted invoices
                aml = invoices.line_ids.filtered(
                    lambda l: l.product_id == product and l.account_id.internal_group == 'expense' and l.display_type == 'cogs'
                )
                if aml:
                    total_cost += sum(aml.mapped('debit')) - sum(aml.mapped('credit'))
                    total_qty += sum(invoices.invoice_line_ids.filtered(lambda l: l.product_id == product).mapped('quantity'))

                if not total_qty:
                    rma_line_cogs_map[line] = 0
                else:                    
                    # rma_line_cogs_map[line] = (total_cost / total_qty) * qty
                    rma_line_cogs_map[line] = (total_cost / total_qty)  # Unit cost

            return rma_line_cogs_map

        def _get_rma_svl_cogs_mapping(rma, svls):
            rma_svl_cogs_mapping = {}
            for svl in svls:
                product = svl.product_id
                if product.id in rma_svl_cogs_mapping:
                    rma_svl_cogs_mapping[product.id] |= svl
                else:
                    rma_svl_cogs_mapping[product.id] = svl
            return rma_svl_cogs_mapping

        # def _update_rma_refund_and_svls(rma, product, qty, correct_value):
        def _update_rma_refund_and_svls(rma, rma_line_cogs_map, rma_product_svl_cogs_mapping):
            """Update RMA refund journal items + SVLs for this RMA"""
            refund = rma.refund_id.sudo()
            if refund and refund.state == 'posted':
                refund.button_draft()

            # Update refund journal items
            # expense lines = COGS  TODO: VERIFY THIS LOGIC
            # aml = refund.line_ids.filtered(
            #     lambda l: l.product_id == product and l.account_id.internal_group == 'expense'
            # )
            # for line in aml:
            #     # reset debit/credit proportional to qty
            #     if correct_value >= 0:
            #         line.debit = correct_value
            #         line.credit = 0.0
            #     else:
            #         line.debit = 0.0
            #         line.credit = abs(correct_value)

            refund.with_context(rma_line_cogs_map=rma_line_cogs_map)._post(soft=False)

            # Update RMA SVLs as per original SVLs values
            picking = rma.reception_move_id.picking_id
            rma_pickings = _get_all_next_pickings(picking)            
            rma_pickings = rma_pickings.filtered(lambda p: p.picking_type_id.code == 'incoming')
            svl_model = env['stock.valuation.layer']
            moves = rma_pickings.move_ids.filtered(lambda m: m.state == 'done' and m.product_id.valuation == 'real_time')
            if not moves:
                return

            company = picking.company_id
            currency = company.currency_id

            rma_svls = svl_model.search([('stock_move_id', 'in', moves.ids)])

            for product_id, original_svls in rma_product_svl_cogs_mapping.items():
                if not original_svls:
                    continue

                qty = abs(sum(original_svls.mapped('quantity')))
                correct_unit_cost = abs(sum(original_svls.mapped('unit_cost')))
                correct_value = abs(sum(original_svls.mapped('value')))

                rma_svl = rma_svls.filtered(lambda s: s.product_id.id == product_id)

                # delete wrong accounting entries first
                svl_journal_entry = rma_svl.account_move_id.sudo()
                corrected_value = (correct_value/qty) * rma_svl.quantity
                corrected__unit_cost = (correct_unit_cost/qty) * rma_svl.quantity
                if (
                    svl_journal_entry
                    and svl_journal_entry.state == "posted"
                    and rma_svl.unit_cost != corrected__unit_cost
                    and rma_svl.value != corrected_value
                ):
                    svl_journal_entry.button_draft()  # Reset to draft
                    # svl_journal_entry._post(soft=False)
                    svl_journal_entry.unlink()

                # update SVL values
                rma_svl.write({
                    'unit_cost': corrected__unit_cost,
                    'value': corrected_value,
                    'remaining_value': corrected_value,
                })

                # regenerate accounting entries
                rma_svl._validate_accounting_entries()

        def _rewrite_svl_and_accounting_for_moves(picking):
            svl_model = env['stock.valuation.layer']

            moves = picking.move_ids.filtered(lambda m: m.state == 'done' and m.product_id.valuation == 'real_time')
            if not moves:
                return

            company = picking.company_id
            currency = company.currency_id

            svls = svl_model.search([('stock_move_id', 'in', moves.ids)])
            if not svls:
                return

            # Fix SVL unit_cost/value and it's accounting entries
            for svl in svls:
                if svl.stock_move_id:
                    qty = svl.quantity
                    correct_unit_cost = _get_correct_unit_cost(svl)
                    correct_value = currency.round(correct_unit_cost * qty)

                    updates = {
                        'unit_cost': correct_unit_cost,
                        'value': correct_value,
                        'remaining_value': correct_value,
                    }
                    svl.write(updates)

                svl_journal_entry = svl.account_move_id.sudo()
                if svl_journal_entry and svl_journal_entry.state == 'posted':
                    svl_journal_entry.button_draft() # Reset to draft
                    # svl_journal_entry._post(soft=False)
                    svl_journal_entry.unlink()
                svl._validate_accounting_entries()
                svl_journal_entry = svl.account_move_id

        for rma in self:
            msg = ""
            if rma.rma_type == 'base_on_product':                
                picking = rma.reception_move_id.picking_id

                rma_pickings = _get_all_next_pickings(picking)
                rma_refund = rma.refund_id.sudo()

                rma_refund.button_draft() # Reset to draft
                rma_refund._post(soft=False) # Post the refund again to correct the journal items COGS values

                # Correct SVL and accounting entries of it
                for picking in rma_pickings:
                    if picking.picking_type_id.code == 'incoming':
                        _rewrite_svl_and_accounting_for_moves(picking)

            elif rma.rma_type == 'base_on_invoice' and rma.invoice_id:
                invoices = rma.invoice_id
                invoices = invoices.filtered(lambda inv: inv.state == 'posted')
                if not invoices:
                    msg += f"\nNo Origin Invoices found for RMA: {rma.name} !!!\n"
                    continue

                related_sale_orders = invoices.invoice_line_ids.sale_line_ids.order_id
                rma_product_svl_cogs_mapping = {}
                if related_sale_orders:
                    related_pickings = related_sale_orders.picking_ids.filtered(lambda p: p.picking_type_code in ['outgoing'])
                    if related_pickings:
                        svls = self.env['stock.valuation.layer'].search([
                            ('stock_move_id.picking_id', 'in', related_pickings.ids),
                            ('product_id', 'in', rma.line_ids.product_id.ids),
                        ])  
                        if svls:                  
                            rma_product_svl_cogs_mapping = _get_rma_svl_cogs_mapping(rma, svls)

                rma_line_cogs_map = _get_rma_lines_cogs_mapping(rma, invoices)
                _update_rma_refund_and_svls(rma, rma_line_cogs_map, rma_product_svl_cogs_mapping)

            elif rma.rma_type == 'base_on_delivery' and rma.picking_id and rma.picking_id.picking_type_code == 'outgoing':
                picking = rma.picking_id  # Origin Source Picking of RMA
                sale_order = picking.sale_id                                
                if not sale_order:
                    root_picking = picking
                    while root_picking.move_orig_ids:
                        root_picking = root_picking.move_orig_ids.mapped('picking_id')
                        if root_picking and root_picking.sale_id:
                            sale_order = root_picking.sale_id[0]
                            break

                if not sale_order:
                    next_pickings = _get_all_next_pickings(picking)
                    if next_pickings.sale_id:
                        sale_order = next_pickings.sale_id[0]
                    else:
                        msg += f"\nNo Sales Order found for RMA: {rma.name} !!!\n"
                        continue

                # collect all SVLs from stock moves of those pickings
                svls = self.env['stock.valuation.layer'].search([
                    ('stock_move_id.picking_id', 'in', rma.picking_id.ids),
                    ('product_id', 'in', rma.line_ids.product_id.ids),
                ])

                rma_product_svl_cogs_mapping = _get_rma_svl_cogs_mapping(rma, svls)

                # Find posted invoices linked to SO
                invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice')
                if not invoices:
                    msg += f"\nNo Origin Invoices found for RMA: {rma.name} !!!\n"
                    continue

                rma_line_cogs_map = _get_rma_lines_cogs_mapping(rma, invoices)
                # _update_rma_refund_and_svls(rma, product, qty, correct_value)
                _update_rma_refund_and_svls(rma, rma_line_cogs_map, rma_product_svl_cogs_mapping)

            if msg:
                _logger.info(msg)

class RMAOrder(models.Model):
    _inherit = 'rma.order'

    def confirm(self):
        rma_obj = self.env['rma']
        for rec in self:
            for line in rec.rma_line_ids:
                vals = {
                    'picking_id': line.origin_delivery_id.id,
                    'move_id': line.orign_move.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'operation_id': line.operation_id.id,
                    # 'return_reason_id': line.return_reason_id.id,
                    # 'return_caused_by': line.return_caused_by.id,
                    'return_caused_by_id': line.return_caused_by_id.id,
                    'rma_order_id': self.id,
                    'product_line_ids': [(0,0, {'product_id': line.product_id.id,
                                                'product_uom_id': line.product_id.uom_id.id,
                                                'product_uom_qty': line.product_uom_qty,
                                                'return_reason_id': line.return_reason_id.id,
                                                'return_caused_by_id': line.return_caused_by_id.id,
                                                })]

                }
                if not line.rma_id or line.rma_id.state == 'cancelled':
                    rma_id = rma_obj.sudo().create(vals)
                    line.rma_id = rma_id.id
                else:
                    line.rma_id.sudo().write(vals)

            rec.sudo().write({'status': 'confirmed'})


class RMAOrderLine(models.Model):
    _inherit = 'rma.order.line'

    return_reason_id = fields.Many2one(
        comodel_name="rma.return.reason",
        string="Return Reason",
        copy=False,
        tracking=True,
        required=False,
    )

    # return_caused_by = fields.Many2many('rma.return.caused.config',
    #                                     string="Return Caused By",
    #                                     copy=False,
    #                                     tracking=True,
    #                                     required=True,
    #                                     )
    # return_caused_by = fields.Many2one(
    #     comodel_name="res.users",
    return_caused_by = fields.Selection(
        selection=rma_return_caused_by,
        string="Return Caused By",
        copy=False,
        tracking=True,

    )

    return_caused_by_id = fields.Many2one('rma.return.caused.config', required=False,)
