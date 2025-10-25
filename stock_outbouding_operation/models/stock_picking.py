from dateutil.relativedelta import relativedelta
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo import _, api, fields, models
from odoo.exceptions import UserError,ValidationError
from datetime import date
import copy
import math
import io
import zipfile
import base64


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    status_label = fields.Char(string="Status", compute="_compute_status_label", store=True)
    draft_trigger = fields.Boolean(string='Draft trigger')
    delivery_planned_date = fields.Date('Delivery Planned date')
    priority_no = fields.Integer("Priority")

    @api.depends('state', 'picking_type_id', 'picking_type_id.name')
    def _compute_status_label(self):
        for picking in self:
            label = dict(self._fields['state'].selection).get(picking.state, picking.state)
            if picking.state == 'assigned':
                if 'Pick' in (picking.picking_type_id.name or ''):
                    label = 'Ready to Pick'
                elif 'Pack' in (picking.picking_type_id.name or ''):
                    label = 'Ready to Verify'
                elif 'Delivery' in (picking.picking_type_id.name or ''):
                    # label = 'Loaded & dispatched & Ready to deliver'
                    label = 'Planned'
            elif picking.state == 'done':
                if 'Pick' in (picking.picking_type_id.name or ''):
                    label = 'Picked'
                elif 'Pack' in (picking.picking_type_id.name or ''):
                    label = 'Verification Done'
                elif 'Delivery' in (picking.picking_type_id.name or ''):
                    label = 'Ready To Deliver'
            elif picking.state == 'loaded_dispatched':
                if 'Delivery' in (picking.picking_type_id.name or ''):
                    label = 'Loaded & Dispatched Done'

            elif picking.state not in ['done', 'assigned']:
                label = picking.state.capitalize()
            if picking.state == 'confirmed':
                label = 'Awaiting planning'
            picking.status_label = label

    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),

        ('loaded_dispatched', 'Loaded & Dispatched'),
        ('delivered_partial', 'Delivered Partial'),
        ('scheduled', 'Scheduled'),
        ('rescheduled', 'Rescheduled'),
        ('returned', 'Returned'),
        ('rescheduled_item_offload_in_warehouse', 'rescheduled - item Offload in warehouse'),
        ('wh_d_return', 'Delivered Partial - Item Offload in Warehouse'),
        ('wh_return', 'Returned - Item Offload in Warehousee'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('delivered', 'Delivered'),
    ], string='Status',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    custom_state_trigger = fields.Boolean('Custom State Trigger', default=False, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        created_pickings = super().create(vals_list)
        for record in self:
            if record.is_out_type and record.picking_driver_id:
                previous_transfers = self.env['stock.picking']
                pickings = record._get_previous_transfers()
                pickings = pickings.filtered(lambda s:s.id != record.id)
                while pickings:
                    if len(pickings) == 1:
                        previous_transfers += pickings
                        pickings = pickings._get_previous_transfers()
                    else:
                        for p in pickings:
                            previous_transfers += p
                            pickings = p._get_previous_transfers()
                if previous_transfers:
                    previous_transfers.sudo().with_context(set_driver_previous=True).write(
                        {'picking_driver_id': record.picking_driver_id.id})
        return created_pickings

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if not self.env.context.get('set_driver_previous'):
            for record in self:
                if vals.get('picking_driver_id') and record.is_out_type and record.picking_driver_id:
                    previous_transfers = self.env['stock.picking']
                    pickings = record._get_previous_transfers()
                    pickings = pickings.filtered(lambda s: s.id != record.id)
                    while pickings:
                        if len(pickings) == 1:
                            previous_transfers += pickings
                            pickings = pickings._get_previous_transfers()
                        else:
                            for p in pickings:
                                previous_transfers += p
                                pickings = p._get_previous_transfers()
                    if previous_transfers:
                        previous_transfers.sudo().with_context(set_driver_previous=True).write({'picking_driver_id': record.picking_driver_id.id})
        return res

    # def make_all_delivery_planned(self):
    #     for rec in self:
    #         if rec.state == 'draft':
    #             self.action_assign()
    #             rec.state = 'planned'

    def planing_delivery(self):
        for rec in self:
            if rec.picking_driver_id and rec.delivery_planned_date and rec.picking_type_code == 'outgoing':
                rec.action_assign()
                rec.state = 'planned'
                related_pickings = self.env['stock.picking'].search([('origin', '=', rec.origin)])
                related_pickings.write({'planning_status': True})
            elif rec.is_pick_type:
                related_pickings = self.env['stock.picking'].search([('origin', '=', rec.origin)])
                related_pickings.write({'planning_status': True})

            else:
                raise ValidationError("Please define required field Driver & Delivery Planned date on the delivery (%s)"%(rec.name))

    def delivery_load_dispatched(self):
        for rec in self:
            if rec.state == 'planned':
                rec.state = 'assigned'
            if rec.state == 'done':
                rec.state = 'loaded_dispatched'

    def wh_rescheduled(self):
        for rec in self:
            rec.custom_state_trigger = True

    def loaded_dispatched(self):
         for rec in self:
             rec.action_confirm()
             rec.custom_state_trigger = True

    def schedule_delivery(self):
        for rec in self:
            if rec.delivery_planned_date:
                if rec.delivery_planned_date and rec.delivery_planned_date < date.today():
                    raise ValidationError("Delivery Planning Date cannot be a past date.")
            else:
                raise ValidationError("Please define Delivery Planned date!")
            if rec.state == 'loaded_dispatched':
                rec.state = 'scheduled'
            else:
                rec.state = 'rescheduled'


    def create_return_rma_entry(self):
        for rec in self:
            rma_vals = {
                'rma_type': 'base_on_delivery',
                'picking_id': rec.id,
                'partner_id': rec.partner_id.id,
                'crm_team_id': rec.sale_id.team_id.id or None if rec.sale_id else None,
                'operation_id': self.env['rma.operation'].search([('operation_type', '=', 'refund')], limit=1).id,
                'collection_request_date': date.today() or None,
                'origin': 'Delivery - ' + rec.name
            }
            rma = self.env['rma'].create(rma_vals)
            rma.compute_line_ids()

    def loaded_dispatched_delivery(self):
        for rec in self:
            # if rec.state == 'loaded_dispatched':
            rec.state = 'delivered'

    def ship_confirm_button_validate(self):
        for rec in self:
            rec.button_validate()

    def cust_rescheduled(self):
        for rec in self:
            rec.custom_state_trigger = True

    # @api.depends('move_type', 'move_ids.state', 'move_ids.picking_id', 'custom_state_trigger','draft_trigger')
    # def _compute_state(self):
    #     for picking in self:
    #         if picking.picking_type_code == 'outgoing':
    #
    #             # raise UserError(str(picking._context))
    #             if picking.draft_trigger:
    #                 picking.state = 'draft'
    #                 picking.draft_trigger = False
    #                 continue
    #             if picking.state in ['confirmed', 'assigned'] and picking.custom_state_trigger:
    #                 picking.state = 'loaded_dispatched'
    #             elif picking.state in ['done'] and picking.custom_state_trigger:
    #                 if sum(picking.move_ids_without_package.mapped('product_uom_qty')) <= sum(picking.move_ids_without_package.mapped('quantity')):
    #                     continue
    #                 else:
    #                     self.state = 'delivered_partial'
    #             elif picking.state == 'delivered_partial' and picking.custom_state_trigger:
    #                 self.state = 'rescheduled'
    #             elif picking.state == 'rescheduled' and picking.custom_state_trigger:
    #                 self.state = 'rescheduled_item_offload_in_warehouse'
    #
    #
    #             # else:
    #             #     res = super(StockPicking, self)._compute_state()
    #             #     if picking.state in ['confirmed', 'assigned'] and picking.picking_type_code == 'outgoing':
    #             #         picking.state = 'loaded_dispatched'
    #             #         picking.custom_state_trigger = True
    #             #     return res
    #         else:
    #             return super(StockPicking, self)._compute_state()

    show_previous_pickings = fields.Boolean(compute='_compute_show_previous_pickings')

    @api.depends('move_ids.move_orig_ids','move_ids.move_dest_ids')
    def _compute_show_previous_pickings(self):
        self.show_previous_pickings = len(self._get_previous_transfers()) != 0

    def _get_previous_transfers(self):
        previous_pickings = self.move_ids.move_orig_ids.picking_id
        return previous_pickings.filtered(lambda p: p not in self.return_ids)

    def action_previous_transfer(self):
        previous_transfers = self._get_previous_transfers()

        if len(previous_transfers) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "views": [[False, "form"]],
                "res_id": previous_transfers.id
            }
        return {
            'name': _('Next Transfers'),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "views": [[False, "list"], [False, "form"]],
            "domain": [('id', 'in', previous_transfers.ids)],
        }

    def action_open_sale_order(self):
        self.ensure_one()
        if self.sale_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales Order',
                'view_mode': 'form',
                'res_model': 'sale.order',
                'res_id': self.sale_id.id,
                'target': 'current',
            }

    def action_open_purchase_order(self):
        self.ensure_one()
        if self.purchase_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Purchase Order',
                'view_mode': 'form',
                'res_model': 'purchase.order',
                'res_id': self.purchase_id.id,
                'target': 'current',
            }

    def action_open_backorder(self):
        self.ensure_one()
        if self.backorder_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Backorder',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': self.backorder_id.id,
                'target': 'current',
            }

    picker_partner_id = fields.Many2one('res.partner', string="Picker")
    picking_driver_id = fields.Many2one('res.partner', string="Driver")
    is_pick_type = fields.Boolean(compute="compute_picking_type", store=True)
    is_pack_type = fields.Boolean(compute="compute_picking_type", store=True)
    is_out_type = fields.Boolean(compute="compute_picking_type", store=True)
    trx_type = fields.Selection([('direct_delivery_order', 'Direct Delivery Order'),
                                 ('return_collection', 'Return Collection'),
                                 ('branch_delivery', 'Branch Delivery'),
                                 ('cross_docking_order', 'Cross Docking Order'),
                                 ('3pl_orders', '3PL Orders'),
                                 ('van_load', 'Van Load'),
                                 ('van_offload', 'Van Offload'),
                                 ('purchase', 'Purchase'),
                                 ('internal_transfer', 'Internal Transfer'),
                                 ('foc_receiving', 'Foc Receiving'),
                                 ('miscellaneous_receiving', 'Miscellaneous Receiving'),
                                 ('scrap_issuance', 'Scrap Issuance'),
                                 ('damage_expiry_issue_out', 'Damage Expiry Issue out'),
                                 ('stock_takeover', 'Stock Takeover'),
                                 ('consumable_issuance', 'Consumable Issuance'),
                                 ('sample', 'Sample')], string="TRX Type")

    show_reset_to_draft = fields.Boolean(default=False)
    execise_declare_no = fields.Text("Excise Declaration No")
    invoice_no = fields.Text("Invoice No")
    packing_slip = fields.Text("Packing Slip / Delivery Note")
    vehicle_number = fields.Text("Vehicle Number")
    number_of_containers = fields.Text("Number Of Container")
    asn_no_id = fields.Many2one("asn.request","ASN Number")
    bl_no_asn_no = fields.Char(string='Asn No.',related="asn_no_id.bl_no_asn_no", store=True)
    shipping_doc_ref = fields.Char("Shipping Document Ref (BL/AWB)")
    bill_of_entry_no = fields.Char("Bill of Entry Number")
    remark_picking = fields.Text("Remark")
    date_time = fields.Datetime("Container Arrival date &time")
    emirates_id = fields.Many2one('res.country.state',string="Emirates",related="partner_id.state_id",store=True)
    qty_in_pallet_case = fields.Float(string='QTY in Pallet (Case)', compute='_compute_qty_in_pallet_case', store=True)

    po_no = fields.Char(string='PO No.',related="sale_id.po_number", store=True)
    po_expiry_date = fields.Date(string='PO Expiry Date',related="sale_id.po_expiry_date", store=True)
    commitment_date = fields.Datetime(string='Delivery Request Date',related="sale_id.commitment_date", store=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson',related="sale_id.user_id", store=True)
    delivery_required = fields.Boolean('Required Plan',compute="compute_delivery_required",store=True,readonly=False)
    date_localization = fields.Date(string='Geolocation Date', related="partner_id.date_localization",)
    city = fields.Char(string="City",related="partner_id.city",store=True)

    @api.depends('sale_id','sale_id.delivery_required')
    def compute_delivery_required(self):
        for record in self:
            delivery_required = False
            if record.request_order_id and record.is_out_type:
                delivery_required = True

            if record.sale_id and record.sale_id.delivery_required == 'yes':
                delivery_required = True
            record.delivery_required = delivery_required


    @api.depends('move_ids.qty_in_case')
    def _compute_qty_in_pallet_case(self):
        for picking in self:
            picking.qty_in_pallet_case = sum(picking.move_ids.mapped('qty_in_case'))

    @api.depends('picking_type_id')
    def compute_picking_type(self):
        for record in self:
            is_pick_type = False
            is_pack_type = False
            is_out_type = False
            if record.picking_type_id and record.picking_type_id.warehouse_id.pick_type_id == record.picking_type_id:
                is_pick_type = True
            if record.picking_type_id and record.picking_type_id.warehouse_id.pack_type_id == record.picking_type_id:
                is_pack_type = True
            if record.picking_type_id and record.picking_type_id.warehouse_id.out_type_id == record.picking_type_id:
                is_out_type = True
            record.is_pick_type = is_pick_type
            record.is_pack_type = is_pack_type
            record.is_out_type = is_out_type

    def button_validate(self):
        for record in self:
            if record.is_pick_type and record.move_ids_without_package.filtered(lambda m: not m.picker_partner_id):
                raise UserError(_("Please Select first Picker before validate."))
            if (record.is_out_type or record.picking_type_id.code == 'incoming') and not record.has_packages and record.move_ids.filtered(lambda s:s.product_id.packaging_ids) and record.move_line_ids:
                raise UserError(_('Please define Packages!'))
            if record.is_out_type and not record.picking_driver_id:
                raise UserError(_("Please Select first Driver before validate."))
            # if record.filtered(lambda s:s.is_pick_type) and record.create_date.date().month != date.today().month and record.move_ids.filtered(lambda s:s.division in ['food','non_food']):
            #     raise UserError(_("You can only validate picking on same month"))
            if (
                    record.picking_type_id.code == 'internal'
                    and record.location_dest_id.usage == 'internal'
                    and record.location_dest_id == record.picking_type_id.warehouse_id.lot_stock_id
                    and not record.forklift_partner_id
            ):
                raise UserError(_("Please select Forklift "))
        res = super().button_validate()
        self.custom_state_trigger = True
        return res


    # move_ids_without_package

    # def action_confirm(self):
    #     for record in self:
    #         if record.is_out_type and not record.picking_driver_id:
    #             raise UserError(_("Please Select first Driver before validate."))
    #     res = super().action_confirm()
    #
    #     return res

    def action_customer_shelf_life(self):
        if self.partner_id and self.partner_id.parent_id:
            partner = self.partner_id.parent_id
        else:
            partner = self.partner_id
        if partner and partner.product_shelf_life_ids:
            for line in self.move_line_ids.filtered(lambda s:s.lot_id):
                product_shelf_line = partner.product_shelf_life_ids.filtered(
                    lambda s: s.product_id == line.product_id and not s.product_category)
                if not product_shelf_line:
                    product_shelf_line = partner.product_shelf_life_ids.filtered(
                        lambda s: s.product_category == line.product_id.categ_id)
                if product_shelf_line:
                    product_shelf_line = product_shelf_line[0]
                    if line.expiration_date:
                        shelf_expiration_date = date.today() + relativedelta(months=product_shelf_line.shelf_life)
                        # shelf_expiration_date = shelf_expiration_date.replace(day=1)
                        if line.expiration_date.date() < shelf_expiration_date:
                            lot_id = self.env['stock.lot']
                            package_id = self.env['stock.quant.package']
                            owner_id = self.env['res.partner']
                            quants = self.env['stock.quant'].with_context(product_shelf_life_expiration=shelf_expiration_date)._get_reserve_quantity(
                                self.product_id, line.location_id, line.quantity, product_packaging_id=line.move_id.product_packaging_id,
                                uom_id=line.product_uom_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                                strict=False)
                            if quants:
                                taken_quantity = 0
                                rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                                candidate_lines = {}
                                candidate_lines[line.location_id, line.package_id, line.owner_id] = line
                                move_line_vals = []
                                grouped_quants = {}
                                # Handle quants duplication
                                for quant, quantity in quants:
                                    if (quant.location_id, quant.lot_id, quant.package_id,
                                        quant.owner_id) not in grouped_quants:
                                        grouped_quants[
                                            quant.location_id, quant.lot_id, quant.package_id, quant.owner_id] = [quant,
                                                                                                                  quantity]
                                    else:
                                        grouped_quants[
                                            quant.location_id, quant.lot_id, quant.package_id, quant.owner_id][
                                            1] += quantity
                                for reserved_quant, quantity in grouped_quants.values():
                                    taken_quantity += quantity
                                    to_update = candidate_lines.get((reserved_quant.location_id,
                                                                     reserved_quant.package_id,
                                                                     reserved_quant.owner_id))
                                    if to_update:
                                        uom_quantity = line.product_id.uom_id._compute_quantity(quantity,
                                                                                                to_update.product_uom_id,
                                                                                                rounding_method='HALF-UP')
                                        uom_quantity = float_round(uom_quantity, precision_digits=rounding)
                                        uom_quantity_back_to_product_uom = to_update.product_uom_id._compute_quantity(
                                            uom_quantity, line.product_id.uom_id, rounding_method='HALF-UP')
                                    if to_update and float_compare(quantity, uom_quantity_back_to_product_uom,
                                                                   precision_digits=rounding) == 0:
                                        to_update.with_context(reserved_quant=reserved_quant).quantity = uom_quantity
                                        line.sudo().write({'lot_id': reserved_quant.lot_id.id, 'expiration_date': reserved_quant.lot_id.expiration_date})
                            # lot_id = self.env['stock.lot'].search(
                            #     [('location_id', '=', line.location_id.id),
                            #      ('expiration_date', '>', shelf_expiration_date)],
                            #     limit=1, order='expiration_date asc')
                            # if lot_id:
                            #     line.sudo().write({'lot_id': lot_id, 'expiration_date': lot_id.expiration_date})
                            else:

                                self.sudo().write({'show_reset_to_draft':True})
                                return {
                                    'type': 'ir.actions.client',
                                    'tag': 'display_notification',
                                    'params': {
                                        'type': 'info',
                                        'title': _('Warning'),
                                        'message': _('No date of available lots for the selected product match customer needs and you can Change location and to click on the draft button'),
                                        'next': {'type': 'ir.actions.act_window_close'},
                                    },
                                }
    def action_set_to_draft(self):
        self.state = 'draft'
        self.show_reset_to_draft = False


    planning_status = fields.Boolean(string="Planning Status", default=False,readonly=True)

    # division = fields.Selection([('food', 'Food'), ('non_food', 'Non-Food'), ('mars', 'Mars')], string="Division")
    # brand_ids = fields.Many2many('product.brand', string="Brands")
    # qty_in_plt = fields.Float(string="Qty in PLT")
    # qty_in_ctn = fields.Float(string="Qty in CTN")

    division = fields.Selection([
        ('food', 'Food'),
        ('non_food', 'Non-Food'),
        ('3pl', '3PL'),
        ('local', 'LOCAL'),
        ('posm', 'POSM'),
        ('mars', 'Mars')
    ], string="Division", compute="_compute_aggregated_values", store=True)

    brand_ids = fields.Many2many('product.brand', string="Brands", compute="_compute_aggregated_values", store=True)

    qty_in_plt = fields.Float(string="Qty in PLT", compute="_compute_aggregated_values", store=True)
    qty_in_ctn = fields.Float(string="Qty in CTN", compute="_compute_aggregated_values", store=True)

    @api.depends('move_ids_without_package', 'move_ids_without_package.product_id', 'move_ids_without_package.product_uom_qty',
                 'move_ids_without_package.division', 'move_ids_without_package.brand_id', 'move_ids_without_package.quantity')
    def _compute_aggregated_values(self):
        for picking in self:
            brands = set()
            division_vals = set()
            total_plt = 0.0
            total_ctn = 0.0

            for move in picking.move_ids_without_package:
                product = move.product_id.product_tmpl_id

                # Collect brand
                if product.brand_id:
                    brands.add(product.brand_id.id)

                # Collect division (optional: use your own logic if from product or move)
                if product.division:
                    division_vals.add(product.division)

                # packaging_ids
                # Calculate PLT and CTN
                move_qty = move.quantity or 0.0
                if not move_qty:
                    continue

                # Loop through all packaging types of the product
                for packaging in product.packaging_ids:
                    if not packaging or not packaging.qty or packaging.qty <= 0:
                        continue

                    package_type = packaging.package_type_id
                    if not package_type:
                        continue

                    # Accumulate PLT
                    if package_type.is_pallete_package:
                        total_plt += move_qty / packaging.qty

                    # Accumulate CTN
                    elif package_type.type == 'ctn':
                        total_ctn += move_qty / packaging.qty

            picking.qty_in_plt = round(total_plt, 2)
            picking.qty_in_ctn = round(total_ctn, 2)
            picking.brand_ids = [(6, 0, list(brands))]

            # Assign division only if exactly one unique
            picking.division = division_vals.pop() if len(division_vals) == 1 else False

    def action_see_packages(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_package_view")
        packages = self.move_line_ids.mapped('result_package_id')
        other_packages = self.env['stock.quant.package'].sudo().search([('stock_move_id','in',self.move_ids.ids)])
        if other_packages:
            action['domain'] = [('id', 'in', packages.ids + other_packages.ids)]
        else:
            action['domain'] = [('id', 'in', packages.ids)]
        action['context'] = {'picking_id': self.id}
        return action

    def action_put_in_pack(self, move_lines_to_pack=False):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            move_line_ids = self._package_move_lines(move_lines_to_pack=move_lines_to_pack)
            if move_line_ids:
                if self.picking_type_code == 'incoming':
                    in_stock_moves  = move_line_ids.mapped('move_id')
                    # good_tag_id = self.env.ref('stock_3dbase.stock_location_tag_good')
                    good_tag_id = self.env['stock.location.tag'].search([('is_inbound', '=', True)], limit=1)
                    for in_stock_move in in_stock_moves:
                        pallete_packages = in_stock_move.product_id.packaging_ids.filtered(
                            lambda s: s.package_type_id.is_pallete_package)
                        no_creating_package = 0
                        for pallete_package in pallete_packages:
                            move_quantity = sum(
                                in_stock_move.filtered(lambda s: pallete_package in s.product_id.packaging_ids).mapped(
                                    'quantity'))
                            if pallete_package.qty > 0.0:
                                no_creating_package += math.ceil(move_quantity / pallete_package.qty)
                        # package_ids = []
                        first_package = False
                        if no_creating_package > 0:
                            vals = {
                                'stock_move_id': in_stock_move.id,
                                'purchase_order_id': self.purchase_id.id,
                            }
                            if pallete_packages:
                                vals['package_type_id'] = pallete_packages[0].package_type_id.id
                            if good_tag_id:
                                vals['tag_id'] = good_tag_id.id
                            package_vals = [vals.copy() for _ in range(no_creating_package)]
                            packages = self.env['stock.quant.package'].create(package_vals)
                            first_package = packages[0].id

                        # assign first pa
                        # for i in range(no_creating_package):
                        #     package = self.env['stock.quant.package'].create({'stock_move_id': in_stock_move.id,'purchase_order_id':self.purchase_id.id})
                        #     if pallete_packages:
                        #         package.package_type_id = pallete_packages[0].package_type_id.id
                        #     if good_tag_id:
                        #         package.tag_id = good_tag_id.id
                        #     # package_type = in_stock_move.product_packaging_id.package_type_id
                        #     # if len(package_type) == 1:
                        #     #     package.package_type_id = package_type
                        #     package_ids.append(package.id)
                        move_line_ids.write({
                            'result_package_id': first_package if first_package else False,
                        })
                        for picking in move_line_ids.mapped('picking_id'):
                            picking_lines = move_line_ids.filtered(lambda ml: ml.picking_id == picking)
                            self.env['stock.package_level'].with_context(from_put_in_pack=True).create({
                                'package_id': first_package if first_package else False,
                                'picking_id': picking.id,
                                'location_id': picking_lines[0].location_id.id,
                                'location_dest_id': picking_lines[0].location_dest_id.id,
                                'move_line_ids': [(6, 0, picking_lines.ids)],
                                'company_id': picking.company_id.id,
                            })
                    return True
                elif self.picking_type_code == 'outgoing':
                    out_move_line_ids = move_line_ids.filtered(lambda ml: ml.state != 'done')
                    for move_line in out_move_line_ids:
                        if not move_line.location_dest_id:
                            product = move_line.product_id
                            quantity = move_line.qty_done or move_line.product_uom_qty or 1.0
                            default_dest_location = move_line._get_default_dest_location()
                            if default_dest_location:
                                location = default_dest_location._get_putaway_strategy(
                                    product=product,
                                    quantity=quantity,
                                    package=False
                                )
                                if location:
                                    move_line.location_dest_id = location.id
                    pallete_package_type = self.env['stock.package.type'].search(
                        [('is_pallete_package', '=', True)], limit=1
                    )
                    if not pallete_package_type:
                        raise UserError(
                            "No pallet package type found. Please define one with 'Is Pallet Package' enabled.")
                    grouped_by_location = {}
                    for move_line in out_move_line_ids:
                        key = move_line.location_dest_id.id
                        grouped_by_location[key] = grouped_by_location.get(key, self.env['stock.move.line']) | move_line
                    for location_dest_id, move_lines in grouped_by_location.items():
                        driver_id = False
                        if self.picking_driver_id:
                            driver_id = self.picking_driver_id.id
                        package = self.env['stock.quant.package'].create({
                            'package_type_id': pallete_package_type.id,
                            'purchase_order_id':self.purchase_id.id,
                            'driver_id':driver_id

                        })
                        move_lines.write({
                            'result_package_id': package.id,
                        })
                        for picking in move_lines.mapped('picking_id'):
                            picking_lines = move_lines.filtered(lambda ml: ml.picking_id == picking)
                            self.env['stock.package_level'].with_context(from_put_in_pack=True).create({
                                'package_id': package.id,
                                'picking_id': picking.id,
                                'location_id': picking_lines[0].location_id.id,
                                'location_dest_id': picking_lines[0].location_dest_id.id,
                                'move_line_ids': [(6, 0, picking_lines.ids)],
                                'company_id': picking.company_id.id,
                            })
                    return True
                else:
                    res = self._pre_put_in_pack_hook(move_line_ids)
                    if not res:
                        package = self._put_in_pack(move_line_ids)
                        return self._post_put_in_pack_hook(package)
                    return res
            raise UserError(
                _("There is nothing eligible to put in a pack. Either there are no quantities to put in a pack or all products are already in a pack."))

    def action_print_related_so_invoices(self):
        invoice_ids = self.env['account.move']

        for picking in self:
            if picking and picking.sale_id:
                sale_order = picking.sale_id
                related_invoices = sale_order.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel'
                )
                invoice_ids |= related_invoices

        if not invoice_ids:
            raise UserError("No related invoices found to print.")

        # Prepare zip in memory
        zip_buffer = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)


        for invoice in invoice_ids:
            pdf_content, _= self.env["ir.actions.report"].sudo()._render_qweb_pdf(
                'stock_outbouding_operation.tax_account_invoices',
                invoice.id,

            )
            filename = f"invoice_{invoice.name.replace('/', '_')}.pdf"
            zip_file.writestr(filename, pdf_content)

        zip_file.close()
        zip_buffer.seek(0)

        # Create and return attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'Invoices.zip',
            'type': 'binary',
            'datas': base64.b64encode(zip_buffer.read()),
            'mimetype': 'application/zip',
            'res_model': 'stock.picking' if self.mapped('id') else self._name,
            'res_id': self[0].id,
        })

        download_url = f'/web/content/{attachment.id}?download=true'
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'new',
        }
