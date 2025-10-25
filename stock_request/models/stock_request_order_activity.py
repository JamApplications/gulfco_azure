from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class StockRequestOrderActivity(models.Model):
    _inherit = 'stock.request.order'

    is_claimable = fields.Boolean(string="Is Claimable", copy=False)
    percentage = fields.Float(string="Percentage", copy=False)
    total_value = fields.Float(string="Total Value", compute="compute_total_value", store=True)
    
    @api.depends('stock_request_ids', 'stock_request_ids.total_value')
    def compute_total_value(self):
        for record in self:
            total_value = 0            
            if record.stock_request_ids:
                total_value = sum(record.stock_request_ids.mapped('total_value'))
            record.total_value = total_value
            
    @api.constrains('percentage', 'is_claimable')
    def _check_percentage_required(self):
        for record in self:
            if record.is_claimable:
                if not record.percentage:
                    raise UserError(_("Percentage is required when 'Is Claimable' is True."))
                if record.percentage < 0 or record.percentage >= 100:
                    raise UserError(_("Percentage must be between 0 and 100."))

    def action_cancel(self):
        # for record in self:
        #     if record.direction in ['branch_transfer', 'van_load', 'van_off_load']:
        #         if self.env.user != record.location_id.responsible_id:
        #             raise AccessError(_("Only the responsible person of the source location can cancel this batch transfer request."))

        res = super(StockRequestOrderActivity, self).action_cancel()
        return res

    def action_confirm(self):
        for record in self:
            # if record.direction in ['branch_transfer', 'van_load', 'van_off_load']:
            #     if self.env.user != record.location_id.responsible_id:
            #         raise AccessError(_("Only the responsible person of the source location can cancel this batch transfer request."))
            current_user = self.env.user

            updated_responsible = record.location_id.responsible_id - current_user
            if record.new_stockkeeper not in updated_responsible:
                updated_responsible |= record.new_stockkeeper
                # record.location_id.responsible_id = [(4,record.new_stockkeeper.id)]
            record.location_id.responsible_id = [(6, 0, updated_responsible.ids)]

        res = super(StockRequestOrderActivity, self).action_confirm()
        return res



    def action_submit(self):
        for record in self:
            if record.direction == 'stock_takeover' and not record.reason_for_hand_over:
                raise UserError('You must attach at least one file for the Reason for Hand Over.')

            if record.direction != 'stock_takeover' and not record.stock_request_ids:
                raise UserError(
                    _("There should be at least one request item for submitting the order.")
                )

            # if record.direction == 'foc_receiving':
            #     for user in record.location_id.responsible_id:
            #         record.activity_schedule(
            #             'mail.mail_activity_data_todo',
            #             user_id=user.id,
            #             summary="Put Away Operation Needed",
            #             note=f"Stock Request {record.name} Please proceed with the Put Away operation.",
            #             date_deadline=fields.Date.today(),
            #         )
            # else:
            #     if record.direction in ['branch_transfer', 'van_load', 'van_off_load'] or (record.direction == 'consumable_issuance' and record.consumable_issuance_type == 'branch'):
            #         for user in record.location_id.responsible_id:
            #             record.activity_schedule(
            #                 'mail.mail_activity_data_todo',
            #                 user_id=user.id,
            #                 summary="Stock Request Requires Your Approval",
            #                 note=f"Stock Request {record.name} needs to be confirmed or cancelled by you.",
            #                 date_deadline=fields.Date.today(),
            #             )

            record.stock_request_ids.action_submit()


            # if record.new_stockkeeper:
            #     record.location_id.responsible_id = record.new_stockkeeper

            record.state = "submitted"


        return True

    def create(self, vals):
        if 'direction' in vals:
            direction = vals.get('direction')
            if direction:
                if direction in ['foc_receiving','miscellaneous_receiving'] or direction == 'stock_takeover':
                    stockkeeper_group = self.env.ref('stock_request.stock_group_stock_keeper')

                    if self.env.user not in stockkeeper_group.users:
                        raise AccessError(
                            _("You are not authorized to create this type of request. Only Stockkeepers can handle it.")
                        )

        return super(StockRequestOrderActivity, self).create(vals)

class StockMove(models.Model):
    _inherit = 'stock.move'

    is_claimable = fields.Boolean(string="Is Claimable",copy=False)
    percentage = fields.Float(string="Percentage",copy=False)

    request_order_id = fields.Many2one('stock.request.order', string="Request Order")
    direction = fields.Selection(
        related='request_order_id.direction',
        string="Request Type",
        store=True
    )

class StockRequest(models.Model):
    _inherit = 'stock.request'

    is_claimable = fields.Boolean(string="Is Claimable",copy=False)
    percentage = fields.Float(string="Percentage",copy=False)
    cost = fields.Float(string="Cost", groups=False, digits='Stock Request Cost',)

    request_order_id = fields.Many2one('stock.request.order', string="Request Order")
    direction = fields.Selection(
        related='request_order_id.direction',
        string="Request Type",
        store=True
    )
    to_warehouse_id = fields.Many2one('stock.warehouse',related='request_order_id.to_warehouse_id',store=True, string="To Warehouse")
    consumable_issuance_type = fields.Selection(related='request_order_id.consumable_issuance_type',
                                                string="Consumable Issuance Type")

    product_packaging_id = fields.Many2one(
        'product.packaging',
        string="Package",
        domain="[('product_id', '=', product_id)]"
    )
    product_packaging_qty = fields.Integer(string="Package Qty")
    total_value = fields.Float(string="Total Value",compute="compute_total_value",store=True)

    @api.depends('cost','product_uom_qty')
    def compute_total_value(self):
        for record in self:
            record.total_value = record.cost * record.product_uom_qty

    @api.onchange('product_id')
    def _onchange_product_cost(self):
        if self.product_id:
            self.cost = self.product_id.standard_price or 0.0

    @api.onchange('product_packaging_id', 'product_packaging_qty')
    def _onchange_package_fields(self):
        for line in self:
            if line.product_packaging_id and line.product_packaging_qty:
                total_qty = line.product_packaging_qty * line.product_packaging_id.qty
                from_uom = line.product_packaging_id.product_uom_id
                to_uom = line.product_uom_id
                line.product_uom_qty = from_uom._compute_quantity(
                    total_qty,
                    to_uom,
                    rounding_method='HALF-UP'
                )


    # @api.constrains('percentage', 'is_claimable')
    # def _check_percentage_required(self):
    #     for record in self:
    #         if record.is_claimable:
    #             if not record.percentage:
    #                 raise UserError(_("Percentage is required when 'Is Claimable' is True."))
    #             if record.percentage < 0 or record.percentage >= 100:
    #                 raise UserError(_("Percentage must be between 0 and 100."))

    user_has_scd_approval = fields.Boolean(compute='_compute_user_has_scd_approval')

    available_lot_ids = fields.Many2many(
        'stock.lot', compute='_compute_available_lot_ids', string='Available Lots'
    )

    @api.depends('product_id', 'location_id')
    def _compute_available_lot_ids(self):
        for line in self:
            line.available_lot_ids = False
            if line.product_id and line.location_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', 'child_of', line.location_id.id),
                    ('lot_id', '!=', False),
                    ('quantity', '>', 0)
                ])
                line.available_lot_ids = quants.mapped('lot_id')

    @api.depends('name')
    @api.depends_context('uid')
    def _compute_user_has_scd_approval(self):
        user_has_scd_approval = self.env.user.has_group('stock_inventory_adjustment.group_scd_approval')
        for record in self:
            record.user_has_scd_approval = user_has_scd_approval

    @api.depends("product_id", "warehouse_id", "location_id")
    def _compute_route_ids(self):
        route_obj = self.env["stock.route"]
        routes = route_obj.search(
            [("warehouse_ids", "in", self.mapped("warehouse_id").ids + self.mapped('to_warehouse_id').ids)]
        )
        routes_by_warehouse = {}
        for route in routes:
            for warehouse in route.warehouse_ids:
                routes_by_warehouse.setdefault(warehouse.id, self.env["stock.route"])
                routes_by_warehouse[warehouse.id] |= route
        for record in self:
            routes = route_obj
            if record.product_id:
                routes += record.product_id.mapped(
                    "route_ids"
                ) | record.product_id.mapped("categ_id").mapped("total_route_ids")
            if record.direction == 'branch_transfer' or (record.direction == 'consumable_issuance' and record.consumable_issuance_type == 'branch'):
                if record.to_warehouse_id and routes_by_warehouse.get(record.to_warehouse_id.id):
                    routes |= routes_by_warehouse[record.to_warehouse_id.id]
            else:
                if record.warehouse_id and routes_by_warehouse.get(record.warehouse_id.id):
                    routes |= routes_by_warehouse[record.warehouse_id.id]
            parents = record.with_context(get_parents=True).get_parents().ids
            # ruff: noqa: B023
            record.route_ids = routes.filtered(
                lambda r: any(p.location_dest_id.id in parents for p in r.rule_ids)
            )

    def get_parents(self):
        location = self.location_id
        result = location
        while location.location_id:
            location = location.location_id
            result |= location
        return result
