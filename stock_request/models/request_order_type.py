from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)


class RequestOrderType(models.Model):
    _inherit = 'stock.request.order'

    reason_handover_id = fields.Many2one(
        'stock.takeover.reason',
        string='Reason of Handover',
        help="Applicable when direction is Stock Takeover"
    )

    group_id = fields.Many2one(
        "procurement.group",
        string="Procurement Group",
        copy=False
    )

    handover_period_from = fields.Date(string='Handover Period From')
    handover_period_to = fields.Date(string='Handover Period To')

    number_of_pallet = fields.Float('Number of Pallet')

    def action_delivery_recycle_wiz(self):
        return {
            'name': 'Deliver for Recycling',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.request.order.recycle',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.customer_id.id if len(self) == 1 else False,
                'default_number_of_pallet': self.number_of_pallet if len(self) == 1 else 0,
                'active_model': 'stock.request.order',
                'active_ids': self.ids,
            },
        }


    direction = fields.Selection(
        selection=[
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
            ('stock_takeover', 'Stock Takeover'),
        ],
        string="Request Type",
    )


    customer_id = fields.Many2one(
        'res.partner',
        string="Customer",
        help="Select the customer for this request",
        tracking=True,
    )

    visit = fields.Many2one(
        'fsm.order',
        string='Visit',
    )

    delivery_required = fields.Boolean(
        string='Delivery Required', default=False
    )
    supplier_classification_id = fields.Many2one('supplier.classification',
        related='product_id.seller_ids.partner_id.supplier_classification_id',
        string='Supplier Classification',
        store=False
    )

    # supplier_classification = fields.Selection(
    #     related='product_id.seller_ids.partner_id.supplier_classification',
    #     string='Supplier Classification',
    #     store=False
    # )

    new_stockkeeper = fields.Many2one(
        'res.users',
        string="New Stock Keeper",
        domain="[('id', 'in', stock_keeper_user_ids)]",
        # related='location_id.responsible_id',
        readonly=False,
    )

    stock_keeper_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_stock_keeper_users',
        store=False,
    )

    move_type_id = fields.Many2one('stock.location.tag', string="Move Type",)
    move_type = fields.Selection([
        ('sound_to_near_expiry', 'Sound to Near Expiry'),
        ('sound_to_damage', 'Sound to Damage'),
        ('near_to_expiry', 'Near to Expiry'),
    ], string="Move Type")


    destination_id = fields.Many2one(
        'stock.location',
        string="Destination",
        domain="[('tag_ids', 'in', move_type_id)]"
    )

    destination_damage_id = fields.Many2one(
        'stock.location',
        string="Destination",
    )

    @api.onchange('destination_damage_id')
    def _onchange_destination_from_sub_location(self):
        """Refer the value of destination_id field from destination_damage_id"""
        if self.destination_damage_id:
            self.destination_id = self.destination_damage_id



    @api.depends('direction')
    def _compute_stock_keeper_users(self):
        group = self.env.ref('stock_request.stock_group_stock_keeper', raise_if_not_found=False)
        users = group.users if group else self.env['res.users']
        for rec in self:
            rec.stock_keeper_user_ids = users

    reason_for_hand_over = fields.Binary(string="Reason for Hand Over", attachment=True)

    picking_id = fields.Many2one('stock.picking', string='Transfer', readonly=True)
    product_id = fields.Many2one('product.product', string='Product')
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    picking_type_id = fields.Many2one('stock.picking.type', string="Picking Type",
                                      domain="[('warehouse_id', '=', warehouse_id)]")

    location_id = fields.Many2one('stock.location', string="Source Location")

    delivery_location_id = fields.Many2one('stock.location', string='Delivery Location')
    consumable_issuance_type = fields.Selection([('branch', 'Branch'), ('internal', 'Internal')],
                                                string="Consumable Issuance Type")

    stock_scrap_ids = fields.Many2many('stock.scrap','Scraps',compute="compute_stock_scrap_ids",store=True)
    scrap_count = fields.Integer(compute="compute_stock_scrap_ids",store=True)
    to_warehouse_id = fields.Many2one('stock.warehouse', string="To Warehouse")

    def action_van_load_done(self):
        for record in self:
            if record.direction == 'van_load':
                record.state = 'done'
                for req in record.stock_request_ids:
                    req.state = 'done'

    def action_open_stock_scrap(self):
        return {
            'name': _('Scrap Products'),
            'view_mode': 'list,form',
            'res_model': 'stock.scrap',
            'type': 'ir.actions.act_window',
            'domain': [('id','in',self.stock_scrap_ids.ids)],
            'target': 'current',
        }

    @api.depends('stock_request_ids.scrap_id')
    def compute_stock_scrap_ids(self):
        for record in self:
            record.stock_scrap_ids = record.stock_request_ids.mapped('scrap_id')
            record.scrap_count = len(record.stock_scrap_ids)

    def action_confirm(self):
        res = super(RequestOrderType, self).action_confirm()
        for record in self:
            if not record.group_id:
                record.group_id = self.env['procurement.group'].create({
                    'name': record.name,
                })

            picking = None
            if record.direction == 'stock_takeover':
                if record:
                    record.write({'state': 'open'})
                continue
            if record.route_id:
                rules = record.route_id.rule_ids.sorted(key=lambda r: r.sequence)
                if not rules:
                    raise UserError("No rules defined in the selected route.")
                pickings = {}
                picking_ids = []
                picking_created = False
                rules_len = len(rules)
                pickings_by_rule = []
                for idx, rule in enumerate(rules):
                    picking_type = rule.picking_type_id
                    rule_location = rule.location_src_id.id
                    rule_dest_location = rule.location_dest_id.id
                    # Apply Van Load logic → update DEST of last rule
                    if record.direction == 'van_load' and idx == rules_len - 1:
                        rule_dest_location = record.customer_id.van_location.id or rule.location_dest_id.id

                    # Apply Van Offload logic → update SOURCE of first rule
                    if record.direction == 'van_off_load' and idx == 0:
                        rule_location = record.customer_id.van_location.id or rule.location_src_id.id

                    if record.direction == 'sample_issue_out' and idx == 0:
                        rule_dest_location = rules[1].location_src_id.id or rule.rule_dest_location.id

                    if picking_type.id not in list(pickings.keys()): # and not picking_created:
                        trx_type = None
                        if record.direction in ['branch_transfer']:
                            trx_type = 'branch_delivery'
                        elif record.direction in ['sample_issue_out']:
                            trx_type = 'sample'
                        elif record.direction in ['van_load']:
                            trx_type = 'van_load'
                        elif record.direction in ['van_off_load']:
                            trx_type = 'van_offload'
                        elif record.direction in ['foc_receiving']:
                            trx_type = 'foc_receiving'
                        elif record.direction in ['miscellaneous_receiving']:
                            trx_type = 'miscellaneous_receiving'
                        elif record.direction in ['van_off_load']:
                            trx_type = 'damage_expiry_issue_out'
                        elif record.direction in ['damage_expiry_issue_out','miscellaneous_issue_out']:
                            trx_type = 'scrap_issuance'
                        elif record.direction in ['stock_takeover']:
                            trx_type = 'stock_takeover'
                        elif record.direction in ['consumable_issuance']:
                            trx_type = 'consumable_issuance'

                        picking_vals = {
                            'picking_type_id': picking_type.id,
                            'origin': record.name,
                            'location_id': rule_location,
                            'trx_type': trx_type,
                            # 'location_id': record.location_id.id if idx == 0 else rule.location_src_id.id,
                            # 'location_dest_id': record.destination_id.id if idx == len(
                            #     rules) - 1 else rule.location_dest_id.id,
                            'location_dest_id': rule_dest_location,
                            'scheduled_date': fields.Datetime.now(),
                            'note': f"Generated from Stock Request Order {record.name}",
                            'company_id': record.company_id.id,
                            'partner_id': record.customer_id.id,
                            'request_order_id': record.id,
                            'group_id': record.group_id.id,
                        }
                        if record.direction != 'consumable_issuance':
                            picking_vals['is_pick_type'] = True
                        picking = None
                        picking_id = None
                        # if record.direction in ['batch_transfer', 'van_load', 'van_off_load']:
                        picking_id = self.env['stock.picking'].create(picking_vals)
                        # else:
                        #     picking = self.env['stock.picking'].create(picking_vals)
                        move_objs = []
                        for stock_request in record.stock_request_ids:
                            product = stock_request.product_id
                            qty = stock_request.product_uom_qty

                            if product and qty:
                                if record.direction in ('branch_transfer','van_load' ) and picking_type.code in ['internal']:
                                    # To fix duplicate move line issue in stock.move causing quantity to be double of demanded
                                    move_line_ids = []
                                else:
                                    move_line_ids = [(0, 0, {
                                            'product_id': product.id,
                                            'location_id': rule_location,
                                            'location_dest_id': rule_dest_location,
                                            'product_uom_id': product.uom_id.id,
                                            'quantity': qty,
                                            'origin': record.name,
                                            'package_id': stock_request.package_id.id,
                                            'picking_id': picking_id.id,
                                            'lot_id': stock_request.lot_id.id if stock_request.lot_id else False,
                                            'production_date': stock_request.lot_id.production_date if stock_request.lot_id else False,
                                            'expiration_date': stock_request.lot_id.expiration_date if stock_request.lot_id else False,
                                            'internal_reference': stock_request.lot_id.ref if stock_request.lot_id else False,
                                        })]
                                move = self.env['stock.move'].create({
                                    'name': f"Move for {product.name}",
                                    'product_id': product.id,
                                    'product_uom': product.uom_id.id,
                                    'product_uom_qty': qty,
                                    'product_packaging_id': stock_request.product_packaging_id.id,
                                    'product_packaging_qty': stock_request.product_packaging_qty,
                                    'location_id': rule_location,
                                    'origin': record.name,
                                    'group_id': record.group_id.id,
                                    # 'package_id': stock_request.package_id.id,
                                    'location_dest_id': rule_dest_location,
                                    'picking_id': picking_id.id ,#if record.direction in ['batch_transfer','van_load', 'van_off_load'] else picking.id,
                                    'is_claimable': record.is_claimable,
                                    'percentage': record.percentage,
                                    'state': 'draft',
                                    'route_ids': [(6, 0, record.route_id.ids)],
                                    'partner_id': record.customer_id.id,
                                    'move_line_ids': move_line_ids if record.direction in ['van_off_load', 'sample_issue_out'] and idx == 0 else [],
                                    'request_order_id': record.id,
                                    **({
                                           'is_claimable': record.is_claimable,
                                           'percentage': record.percentage,
                                       } if record.direction in ['sample_issue_out',
                                                                 'damage_expiry_issue_out','miscellaneous_issue_out'] else {}),
                                })
                                move_objs.append(move)
                            stock_request.picking_ids = [(4, picking_id.id)] if picking_id else  [(4, picking.id)]


                        if picking_id:
                            # Append BEFORE confirm (so moves still exist)
                            pickings_by_rule.append(
                                (rule, picking_id, self.env['stock.move'].browse([m.id for m in move_objs]))
                            )

                            # Now confirm picking
                            if record.direction in ('branch_transfer','van_load'):
                                picking_id.action_assign()
                                picking_id.action_confirm()
                                picking_ids.append(picking_id.id)
                            else:
                                picking_id.action_confirm()
                                picking_ids.append(picking_id.id)

                        pickings[picking_type.id] = picking_id
                        picking_created = True

                if picking_ids:
                    record.picking_ids = [(6, 0, picking_ids)]

                # Second: link moves between pickings (create origin-dest relationship)
                for i in range(len(pickings_by_rule) - 1):
                    _, source_picking, source_moves = pickings_by_rule[i]
                    _, dest_picking, dest_moves = pickings_by_rule[i + 1]

                    for move_src in source_moves.exists():
                        matching_dest_moves = dest_moves.exists().filtered(
                            lambda m: m.product_id.id == move_src.product_id.id
                        )
                        for move_dest in matching_dest_moves:
                            move_src.write({'move_dest_ids': [(4, move_dest.id)]})


                    # for move_src in source_moves:
                    #     matching_dest_moves = dest_moves.filtered(
                    #         lambda m: m.product_id.id == move_src.product_id.id)
                    #     for move_dest in matching_dest_moves:
                    #         move_src.write({'move_dest_ids': [(4, move_dest.id)]})
                    #         move_dest.write({'move_orig_ids': [(4, move_src.id)]})
            else:
                picking = None
                picking = self.env['stock.picking']
                # picking_type_id = False
                # if record.direction == 'internal_transfer':
                #     picking_type_id = record.warehouse_id.int_type_id.id
                # elif record.direction == 'damage_expiry_issue_out':
                #     picking_type_id = record.warehouse_id.out_type_id.id
                # elif record.direction == 'consumable_issuance':
                #     picking_type_id = record.warehouse_id.pick_type_id.id
                # elif record.direction == 'foc_receiving':
                #     picking_type_id = record.warehouse_id.in_type_id.id
                # elif record.direction == 'van_off_load':
                #     picking_type_id = record.warehouse_id.out_type_id.id
                # elif record.direction == 'van_load':
                #     picking_type_id = record.warehouse_id.pick_type_id.id
                # elif record.direction == 'scrap_issuance':
                #     picking_type_id = record.warehouse_id.int_type_id.id

                if record.direction == 'internal_transfer':
                    picking_group_map = {}

                    # Group stock requests by (source_location, destination_location)
                    for stock_request in record.stock_request_ids:
                        key = (stock_request.source_location.id, stock_request.destination_location.id)
                        picking_group_map.setdefault(key, []).append(stock_request)

                    for (source_location_id, destination_location_id), stock_requests in picking_group_map.items():
                        picking_vals = {
                            'picking_type_id': record.warehouse_id.pick_type_id.id,
                            'location_id': source_location_id,
                            'location_dest_id': destination_location_id,
                            'origin': record.name,
                            'scheduled_date': fields.Datetime.now(),
                            'note': f"Generated from Stock Request Order {record.name}",
                            'company_id': record.company_id.id,
                            'trx_type': 'internal_transfer',
                            'partner_id': record.customer_id.id,
                            'request_order_id': record.id,
                            'group_id': record.group_id.id,
                        }

                        picking_id = self.env['stock.picking'].create(picking_vals)
                        record.picking_ids = [(4, picking_id.id)]

                        for stock_request in stock_requests:
                            stock_request.picking_ids = [(4, picking_id.id)]

                            move_vals = {
                                'name': f"Move for {stock_request.product_id.name}",
                                'product_id': stock_request.product_id.id,
                                'product_uom': stock_request.product_id.uom_id.id,
                                'product_uom_qty': stock_request.product_uom_qty,
                                'location_id': source_location_id,
                                'location_dest_id': destination_location_id,
                                'origin': record.name,
                                'group_id': record.group_id.id,
                                'product_packaging_id': stock_request.product_packaging_id.id,
                                'product_packaging_qty': stock_request.product_packaging_qty,
                                'picking_id': picking_id.id,
                                'state': 'draft',
                                'partner_id': record.customer_id.id,
                                'request_order_id': record.id,
                            }

                            if record.direction in ['sample_issue_out', 'damage_expiry_issue_out','miscellaneous_issue_out']:
                                move_vals.update({
                                    'is_claimable': stock_request.is_claimable,
                                    'percentage': stock_request.percentage,
                                })

                            self.env['stock.move'].create(move_vals)
                        if picking_id:
                            picking_id.action_confirm()
                            picking_id.action_assign()

                # if record.direction == 'internal_transfer':
                #     for stock_request in record.stock_request_ids:
                #         product = stock_request.product_id
                #         qty = stock_request.product_uom_qty
                #         if product and qty:
                #
                #             # Use line-level source/destination
                #             source_location = stock_request.source_location.id
                #             destination_location = stock_request.destination_location.id
                #
                #             picking_vals = {
                #                 'picking_type_id': record.warehouse_id.int_type_id.id,
                #                 'location_id': source_location,
                #                 'location_dest_id': destination_location,
                #                 'origin': record.name,
                #                 'scheduled_date': fields.Datetime.now(),
                #                 'note': f"Generated from Stock Request Order {record.name} (Line ID: {stock_request.id})",
                #                 'company_id': record.company_id.id,
                #                 'partner_id': record.customer_id.id,
                #                 'request_order_id': record.id,
                #             }
                #
                #             # Create one picking per line
                #             picking_id = self.env['stock.picking'].create(picking_vals)
                #             record.picking_ids = [(4, picking_id.id)]
                #             stock_request.picking_ids = [(4, picking_id.id)]
                #
                #             # Create one move per picking
                #             move_vals = {
                #                 'name': f"Move for {product.name}",
                #                 'product_id': product.id,
                #                 'product_uom': product.uom_id.id,
                #                 'product_uom_qty': qty,
                #                 'location_id': source_location,
                #                 'location_dest_id': destination_location,
                #                 'picking_id': picking_id.id,
                #                 'state': 'draft',
                #                 'partner_id': record.customer_id.id,
                #                 'request_order_id': record.id,
                #             }
                #
                #             # Include claimable fields conditionally
                #             if record.direction in ['sample_issue_out', 'damage_expiry_issue_out']:
                #                 move_vals.update({
                #                     'is_claimable': record.is_claimable,
                #                     'percentage': record.percentage,
                #                 })
                #
                #             self.env['stock.move'].create(move_vals)
                #     # record.picking_ids = [(6,0, picking_ids)]
                # if record.direction == 'internal_transfer':
                #     picking_vals = {
                #         'picking_type_id': record.warehouse_id.int_type_id.id,
                #         'location_id': record.location_id.id,
                #         'location_dest_id': record.destination_id.id,
                #         'origin': record.name,
                #         'scheduled_date': fields.Datetime.now(),
                #         'note': f"Generated from Stock Request Order {record.name}",
                #         'company_id': record.company_id.id,
                #         'partner_id': record.customer_id.id,
                #         'request_order_id': record.id,
                #     }
                #     # if record.direction != 'consumable_issuance':
                #     #     picking_vals['is_pick_type'] = True
                #     picking = self.env['stock.picking'].create(picking_vals)
                #     for stock_request in record.stock_request_ids:
                #         product = stock_request.product_id
                #         qty = stock_request.product_uom_qty
                #         if product and qty:
                #             move = self.env['stock.move'].create({
                #                 'name': f"Move for {product.name}",
                #                 'product_id': product.id,
                #                 'product_uom': product.uom_id.id,
                #                 'product_uom_qty': qty,
                #                 'location_id': record.location_id.id,
                #                 'location_dest_id': record.destination_id.id,
                #                 'picking_id': picking.id,
                #                 'state': 'draft',
                #                 'partner_id': record.customer_id.id,
                #                 'request_order_id': record.id,
                #                 **({
                #                        'is_claimable': stock_request.is_claimable,
                #                        'percentage': stock_request.percentage,
                #                    } if record.direction in ['sample_issue_out',
                #                                              'damage_expiry_issue_out'] else {})
                #             })
                elif record.direction == 'consumable_issuance' and record.consumable_issuance_type == 'internal':
                    record.create_stock_scrap()
                elif record.direction in ['damage_expiry_issue_out','scrap_issuance','miscellaneous_issue_out']:
                    record.create_stock_scrap()
                elif record.direction == 'miscellaneous_receiving':
                    picking_vals = {
                        'picking_type_id': record.warehouse_id.in_type_id.id,
                        'location_id': record.location_id.id,
                        'location_dest_id': record.destination_id.id,
                        'origin': record.name,
                        'scheduled_date': fields.Datetime.now(),
                        'note': f"Generated from Stock Request Order {record.name}",
                        'company_id': record.company_id.id,
                        'trx_type': 'miscellaneous_receiving',
                        'partner_id': record.customer_id.id,
                        'request_order_id': record.id,
                        'group_id': record.group_id.id,
                    }
                    picking_id = self.env['stock.picking'].create(picking_vals)
                    record.picking_ids = [(4, picking_id.id)]
                    for stock_request in record.stock_request_ids:
                        stock_request.picking_ids = [(4, picking_id.id)]

                        move_vals = {
                            'name': f"Move for {stock_request.product_id.name}",
                            'product_id': stock_request.product_id.id,
                            'product_uom': stock_request.product_id.uom_id.id,
                            'product_uom_qty': stock_request.product_uom_qty,
                            'location_id': record.location_id.id,
                            'location_dest_id': record.destination_id.id,
                            'origin': record.name,
                            'group_id': record.group_id.id,
                            'product_packaging_id': stock_request.product_packaging_id.id,
                            'product_packaging_qty': stock_request.product_packaging_qty,
                            'picking_id': picking_id.id,
                            'state': 'draft',
                            'partner_id': record.customer_id.id,
                            'request_order_id': record.id,
                            **({
                                   'move_line_ids': [(0, 0, {
                                       'product_id': stock_request.product_id.id,
                                       'location_id': record.location_id.id,
                                       'location_dest_id': record.destination_id.id,
                                       'product_uom_id': stock_request.product_id.uom_id.id,
                                       'quantity': stock_request.product_uom_qty,
                                       'origin': record.name,
                                       'lot_id': stock_request.lot_id.id if stock_request.lot_id else False,
                                       'production_date': stock_request.lot_id.production_date if stock_request.lot_id else False,
                                       'expiration_date': stock_request.lot_id.expiration_date if stock_request.lot_id else False,
                                       'internal_reference': stock_request.lot_id.ref if stock_request.lot_id else False,
                                   })]
                               } if stock_request.lot_id else {})
                        }
                        if record.direction in ['sample_issue_out', 'damage_expiry_issue_out',
                                                'miscellaneous_issue_out']:
                            move_vals.update({
                                'is_claimable': stock_request.is_claimable,
                                'percentage': stock_request.percentage,
                            })
                        self.env['stock.move'].create(move_vals)
                        if picking_id:
                            picking_id.action_confirm()
                            picking_id.action_assign()
            if record.delivery_required and record.direction in ['consumable_issuance']: #, 'sample_issue_out']:

                trx_type = None
                if record.direction in ['branch_transfer']:
                    trx_type = 'branch_delivery'
                elif record.direction in ['sample_issue_out']:
                    trx_type = 'sample'
                elif record.direction in ['van_load']:
                    trx_type = 'van_load'
                elif record.direction in ['van_off_load']:
                    trx_type = 'van_offload'
                elif record.direction in ['foc_receiving']:
                    trx_type = 'foc_receiving'
                elif record.direction in ['miscellaneous_receiving']:
                    trx_type = 'miscellaneous_receiving'
                elif record.direction in ['van_off_load']:
                    trx_type = 'damage_expiry_issue_out'
                elif record.direction in ['damage_expiry_issue_out','miscellaneous_issue_out']:
                    trx_type = 'scrap_issuance'
                elif record.direction in ['stock_takeover']:
                    trx_type = 'stock_takeover'
                elif record.direction in ['consumable_issuance']:
                    trx_type = 'consumable_issuance'

                delivery_picking = self.env['stock.picking'].create({
                    'picking_type_id': record.warehouse_id.out_type_id.id,
                    'trx_type': trx_type,
                    'location_id': record.destination_id.id,
                    'location_dest_id': record.delivery_location_id.id if record.delivery_location_id else record.destination_id.id,
                    'origin': record.name + " - Delivery",
                    'group_id': record.group_id.id,
                    'scheduled_date': fields.Datetime.now(),
                    'note': f"Delivery for Stock Request Order {record.name}",
                    'company_id': record.company_id.id,
                    'partner_id': record.customer_id.id,
                    'request_order_id': record.id,
                    'state': 'draft',
                })

                # if record.delivery_required and record.direction != 'consumable_issuance':
                #     delivery_picking.write({'trx_type': 'sample'})

                for stock_request in record.stock_request_ids:
                    product = stock_request.product_id
                    qty = stock_request.product_uom_qty

                    if product and qty:
                        self.env['stock.move'].create({
                            'name': f"Move for {product.name}",
                            'product_id': product.id,
                            'product_uom': product.uom_id.id,
                            'product_uom_qty': qty,
                            'origin': record.name,
                            'group_id': record.group_id.id,
                            'product_packaging_id': stock_request.product_packaging_id.id,
                            'product_packaging_qty': stock_request.product_packaging_qty,
                            'location_id': record.warehouse_id.pick_type_id.default_location_dest_id.id,
                            'location_dest_id': record.destination_id.id,
                            'picking_id': delivery_picking.id,
                            'is_claimable': record.is_claimable,
                            'percentage': record.percentage,
                            'state': 'draft',
                            'partner_id': record.customer_id.id,
                        })
            if picking and record.direction not in ('branch_transfer', 'van_load', 'van_off_load'):
                record.picking_id = picking.id
            record.state = 'open'

            states = record.stock_request_ids.mapped('state')
            if states and all(state == 'done' for state in states):
                record.state = 'done'

        return res

    def create_stock_scrap(self):
        for stock_request in self.stock_request_ids:
            scrap = self.env['stock.scrap'].create({
                'product_id': stock_request.product_id.id,
                'product_uom_id': stock_request.product_uom_id.id,
                'scrap_qty': stock_request.product_uom_qty,
                'lot_id': stock_request.lot_id.id or False ,
                'package_id': stock_request.package_id.id,
                'origin': stock_request.order_id.name,
                'location_id': stock_request.source_location.id if self.direction != 'scrap_issuance' else self.location_id.id,
                'scrap_location_id': stock_request.destination_location.id if self.direction != 'scrap_issuance' else self.destination_id.id,
            })
            if scrap:
                stock_request.sudo().write({'scrap_id':scrap.id})
                scrap.action_validate()

                if stock_request.mapped('state') == ['done']:
                    stock_request.order_id.write({'state': 'done'})
                # auto validate when scrap created

    def open_picking(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError("No stock picking is linked.")

        return {
            'name': 'Stock Picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'target': 'current',
        }

    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'picking_id': False,
        })
        return super(RequestOrderType, self).copy(default)

    @api.model
    def _get_default_source_location_for_stockkeeper(self, direction=None):
        if direction == 'stock_takeover':
            stockkeeper_group = self.env.ref('stock_request.stock_group_stock_keeper')

            if self.env.user in stockkeeper_group.users:
                location = self.env['stock.location'].search([('responsible_id', 'in', self.env.user.id)], limit=1)
                if location:
                    return location.id
        return None

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        for rec in self:
            if rec.warehouse_id:
                picking_type = self.env['stock.picking.type'].search([
                    ('warehouse_id', '=', rec.warehouse_id.id),
                    ('code', '=', 'stock_request_order')
                ], limit=1)
                rec.picking_type_id = picking_type.id if picking_type else False
            else:
                rec.picking_type_id = False

    @api.onchange('picking_type_id', 'direction')
    def _onchange_picking_type_and_direction(self):
        for record in self:
            if record.direction != 'stock_takeover':
                record.reason_handover_id = False
                record.handover_period_from = False
                record.handover_period_to = False

            record.destination_id = False
            record.location_id = False

            if record.picking_type_id:
                record.location_id = record.picking_type_id.default_location_src_id

            if record.picking_type_id:
                record.destination_id = record.picking_type_id.default_location_dest_id

            # Special Case: stock_takeover
            if record.direction == 'stock_takeover':
                location = self.env['stock.location'].search([('responsible_id', 'in', self.env.user.id)], limit=1)
                if location:
                    record.location_id = location.id

    @api.onchange('direction', 'location_id', 'move_type_id', 'destination_id')
    def onchange_stock_request_line_data(self):
        for rec in self:
            # Reset stock requests if not internal transfer
            if rec.direction in ['damage_expiry_issue_out','miscellaneous_issue_out']:
                continue
            if rec.direction not in ('internal_transfer', 'consumable_issuance'):
                if rec.consumable_issuance_type not in ['internal']:
                    rec.stock_request_ids = None
                    continue
                else:
                    rec.stock_request_ids = None
                    continue

            # Ensure all fields are set for internal transfer
            if not (rec.location_id and rec.destination_id and rec.move_type_id):
                rec.stock_request_ids = None
                continue

            # Clear existing lines
            rec.stock_request_ids = [(5, 0, 0)]

            # Get all child locations except destination
            locations = rec.location_id.with_context(active_test=False).search([
                ('id', 'child_of', rec.sudo().location_id.id)
            ])
            locations = locations - rec.sudo().destination_id

            # Fetch eligible quants
            quants = self.env['stock.quant'].search([
                ('location_id', 'in', locations.ids),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0),
                ('lot_id', '!=', False)
            ])

            product_lines = []
            for quant in quants:
                product = quant.product_id
                lot = quant.lot_id
                expiry_date = lot.expiration_date

                if not expiry_date or not product:
                    continue

                # Get alert_time (default 0 if not set)
                alert_time = product.alert_time or 0

                # Calculate cut-off date based on alert_time
                cutoff_date = date.today() + timedelta(days=alert_time)

                quantity = quant.quantity - quant.reserved_quantity

                # Include lots expiring within alert_time days
                if expiry_date.date() <= cutoff_date and quantity > 0:
                    product_lines.append({
                        'product_id': product.id,
                        'product_uom_qty': quantity,
                        'lot_id': lot.id,
                        'location_id': quant.location_id.id,
                        'source_location': quant.location_id.id,
                        'destination_location': rec.destination_id.id,
                        'product_uom_id': product.uom_id.id,
                        'request_order_id': rec.id,
                        'cost': product.standard_price,
                        'warehouse_id': rec.warehouse_id.id
                    })

            # Add request lines or show warning
            if not product_lines:
                return {
                    'warning': {
                        'title': "No Stock Found",
                        'message': "No products found that are near expiry based on the alert time."
                    }
                }

            for line in product_lines:
                rec.stock_request_ids = [(0, 0, line)]

    # @api.onchange('direction','location_id', 'move_type_id', 'destination_id')
    # def onchange_stock_request_line_data(self):
    #
    #     for rec in self:
    #         if rec.direction != 'internal_transfer':
    #             rec.stock_request_ids = None
    #         if rec.location_id and rec.destination_id and rec.move_type_id and rec.direction == 'internal_transfer':
    #             if rec.direction != 'internal_transfer' or not (
    #                     rec.location_id and rec.destination_id and rec.move_type_id):
    #                 rec.stock_request_ids = None
    #                 return
    #
    #             # Clear existing lines (optional)
    #             rec.stock_request_ids = [(5, 0, 0)]
    #
    #             # Get location and its children
    #             locations = rec.location_id.with_context(active_test=False).search([
    #                 ('id', 'child_of', rec.location_id.id)
    #             ])
    #             locations = locations - rec.destination_id
    #
    #             # Fetch quants with products tracked by lot and having expiry in 3 months
    #             quants = self.env['stock.quant'].search([
    #                 ('location_id', 'in', locations.ids),
    #                 ('location_id.usage', '=', 'internal'),
    #                 ('quantity', '>', 0),
    #                 ('lot_id', '!=', False)
    #             ])
    #
    #             product_lines = []
    #             for quant in quants:
    #                 product = quant.product_id
    #                 lot = quant.lot_id
    #                 expiry_date = lot.expiration_date
    #
    #                 if not expiry_date:
    #                     continue
    #                 product_expiry_time = quant.product_id.expiration_time or 0 if quant.product_id else 0
    #                 three_months_later = date.today() + timedelta(days=product_expiry_time)
    #
    #                 quantity = quant.quantity - quant.reserved_quantity
    #
    #                 # Filter lots expiring within 90 days
    #                 if expiry_date.date() <= three_months_later and quantity > 0:
    #                     product_lines.append({
    #                         'product_id': product.id,
    #                         'product_uom_qty': quantity,
    #                         'lot_id': lot.id,
    #                         'location_id': quant.location_id.id,
    #                         'source_location': quant.location_id.id,
    #                         'destination_location': rec.destination_id.id,
    #                         'product_uom_id': product.uom_id.id,
    #                         'request_order_id': rec.id,
    #                         'warehouse_id': rec.warehouse_id.id
    #                     })
    #
    #             # Add request lines
    #             if not product_lines:
    #                 raise UserError("Stock not found in the child of all source locations!")
    #             for line in product_lines:
    #                 rec.stock_request_ids = [(0, 0, line)]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    supplier_classification_id = fields.Many2one('supplier.classification',
                                                 related='seller_ids.partner_id.supplier_classification_id',
                                                 string='Supplier Classification',
                                                 store=False
                                                 )

    # supplier_classification = fields.Selection(
    #     related='seller_ids.partner_id.supplier_classification',
    #     string='Supplier Classification',
    #     store=False
    # )
