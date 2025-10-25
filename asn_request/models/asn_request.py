from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import groupby


class AsnRequest(models.Model):
    _name = 'asn.request'
    _description = 'ASN Request'
    _rec_name = 'bl_no_asn_no'
    _inherit = ["mail.thread", "mail.activity.mixin"]


    bl_no_asn_no = fields.Char(string='ASN No', required=True, default=lambda self: _("New"), tracking=True)
    bl_no = fields.Char(string="BL No")
    supplier_id = fields.Many2one('res.partner', string='Supplier Name', required=True)
    responsible_id = fields.Many2one('res.users', string='Responsible', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    shipment_mode = fields.Selection(
        [('land', 'Land'), ('ocean', 'Ocean'), ('air', 'Air')],
        string='Shipment Mode',
    )
    port_of_loading = fields.Char(string='Port of Loading')
    port_of_discharge = fields.Char(string='Port of Discharge')
    vessel_name = fields.Char(string='Vessel Name')
    voyage_no = fields.Char(string='Voyage No')
    shipping_line = fields.Char(string='Shipping Line')
    total_bl_net_weight = fields.Float(string='Total BL Net Weight')
    total_bl_gross_wt = fields.Float(string='Total BL Gross Wt')
    document_receipt_date = fields.Date(string='Document Receipt Date')
    dispatched_date = fields.Date(string='Dispatched Date (Sail Date)')
    eta_uae_port = fields.Date(string='ETA in UAE Port')
    expected_arrival_wh = fields.Date(string='Expected Arrival in WH')
    remarks = fields.Text(string='Remarks')
    free_period = fields.Integer(string='Free Period')
    actual_arrived_port_date = fields.Date(string='Actual Arrived at Port Date',copy=False)
    demurrage_start_date = fields.Date(string='Demurrage Start Date')
    receipt_no = fields.Char(string='Receipt No')
    received_in_wh_date = fields.Date(string='Received in Warehouse Date')
    municipality_clearance_status = fields.Selection(
        [
            ('in_progress', 'In Progress'),
            ('dip', 'DIP'),
            ('pending_lab_test', 'Pending Lab Test'),
            ('other_pending', 'Other Pending'),
            ('exceptional_manual_release', 'Exceptional - Manual Release'),
            ('inspection_completed_released_closed', 'Inspection Completed & Released - Closed'),
        ],
        string='Municipality Clearance Status',
    )
    demurrage_amount = fields.Monetary(string='Demurrage Amount')
    excise_declaration_no = fields.Char(string='Excise Declaration No')
    boe_no = fields.Char(string='BOE No')
    boe_date = fields.Date(string='BOE Date')
    municipality_release_no = fields.Char(string='Municipality Release No (FIRS/CPIP)')
    firs_cpip_document_date = fields.Date(string='FIRS/CPIP Document Date')
    demurrage_paid = fields.Boolean(string='Demurrage Paid')
    currency_id = fields.Many2one('res.currency', string='Currency')
    line_ids = fields.One2many('asn.request.line', 'asn_request_id', string='ASN Request Line')
    # ==============================================================================
    state = fields.Selection(
        selection=[
            ('on_way', 'Shipment on the way'),
            ('at_port', 'Arrived at port'),
            ('in_warehouse', 'Arrived at warehouse'),
            ('stock_added', 'Stock added in inventory'),
            ('municipality_clearance_pending', 'Municipality Clearance Pending'),
            ('released_manually', 'Released manually'),
            ('municipality_release_done_closed', 'Municipality Release Done - Closed'),
        ],
        string='State',
        default='on_way',
        tracking=True
    )
    grn_created = fields.Boolean(string="GRN Created", copy=False)
    picking_count = fields.Integer(compute="_compute_picking_count",store=True)
    picking_ids = fields.Many2many('stock.picking', string="Pickings",copy=False)
    asn_landed_cost_ids = fields.One2many('asn.stock.landed.cost', 'asn_request_id', string="Landed Cost")
    landed_cost_count = fields.Integer(compute="_compute_landed_cost_count")
    stock_landed_cost_ids = fields.Many2many('stock.landed.cost', string="Stock Landed cost",copy=False)

    @api.model
    def _get_default_bl_no_asn_no(self):
        return self.env["ir.sequence"].next_by_code("asn.request")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("bl_no_asn_no", _("New")) == _("New"):
                vals["bl_no_asn_no"] = self._get_default_bl_no_asn_no()
        requests = super().create(vals_list)
        return requests

    def copy(self, default=None):
        default = dict(default or {})
        self.ensure_one()
        default.update({"bl_no_asn_no": self._get_default_bl_no_asn_no()})
        return super().copy(default)

    @api.depends('picking_ids','picking_ids.state')
    def _compute_picking_count(self):
        for record in self:
            pickings = self.picking_ids
            # pickings = record.line_ids.mapped('purchase_order_id').mapped('picking_ids')
            if record.line_ids and pickings:
                record.picking_count = len(pickings)
                if pickings.filtered(lambda s: s.state == 'done') and len(pickings) == len(
                        pickings.filtered(lambda s: s.state == 'done')) and record.state == 'in_warehouse':
                    record.state = 'stock_added'
                # record.picking_ids = pickings.ids
            else:
                record.picking_count = 0

    @api.depends('stock_landed_cost_ids')
    def _compute_landed_cost_count(self):
        for record in self:
            if record.stock_landed_cost_ids:
                record.landed_cost_count = len(record.stock_landed_cost_ids)
            else:
                record.landed_cost_count = 0

    def open_action_view_pickings(self):
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
        result['domain'] = [('id', 'in', self.picking_ids.ids)]
        return result

    def open_action_landed_cost(self):
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id('stock_landed_costs.action_stock_landed_cost')
        result['domain'] = [('id', 'in', self.stock_landed_cost_ids.ids)]
        return result

    def _compute_states(self):
        asn_stage_ids = self.env['asn.stage'].search([], order='sequence')
        return [(
            str(stage.name).replace(" ", "_").swapcase(),
            stage.name,
        ) for stage in asn_stage_ids]

    @api.onchange('actual_arrived_port_date')
    def _onchange_actual_arrived_port_date(self):
        if self.actual_arrived_port_date and self.state == 'on_way':
            self.state = 'at_port'

    # @api.onchange('eta_uae_port')
    # def _onchange_eta_uae_port(self):
    #     if self.eta_uae_port and self.state == 'on_way':
    #         self.state = 'at_port'

    @api.onchange('received_in_wh_date')
    def onchange_received_in_wh_date(self):
        if self.received_in_wh_date and self.state == 'at_port':
            self.state = 'in_warehouse'

    @api.onchange('municipality_clearance_status')
    def _onchange_municipality_clearance_status(self):
        if self.municipality_clearance_status == 'exceptional_manual_release':
            self.state = 'released_manually'
        elif self.municipality_clearance_status == 'inspection_completed_released_closed':
            self.state = 'municipality_release_done_closed'

    def action_create_grn(self):
        purchase_orders = self.line_ids.mapped('purchase_order_id')
        if 0 in self.line_ids.mapped('qty_in_invoice'):
            raise UserError('please set quantity in Qty In Invoice field')
        purchase_orders.with_context(from_asn_request=True, asn_record=self)._create_picking()
        # self.state = 'in_warehouse'
        self.grn_created = True
        stock_move_ids = self.line_ids.mapped('purchase_order_line_id').mapped('move_ids')
        # pickings = self.line_ids.mapped('purchase_order_id').mapped('picking_ids')
        picking_ids = stock_move_ids.filtered(lambda s:s.asn_line_id in self.line_ids).mapped('picking_id')
        self.picking_ids = picking_ids
        for pic in picking_ids:
            pic.asn_no_id = self.id
        # for op_line in picking_ids.move_ids_without_package:
        #     for rec in self.line_ids.filtered(lambda l:l.product_product_id == op_line.product_id):
        #         op_line.product_uom_qty = rec.qty_in_invoice

    def action_create_landed_cost(self):
        if not self.asn_landed_cost_ids:
            raise UserError('please configure landed cost')
        vendor_landed_cost_ids = groupby(self.asn_landed_cost_ids, lambda s: (s.partner_id, s.picking_id))
        landed_cost_list = []
        for (partner,picking_id), asn_landed_cost_lines in vendor_landed_cost_ids:
            cost_line_vals = []
            picking_ids = []
            for asn_landed_cost_line in asn_landed_cost_lines:
                cost_line_vals.append((0, 0, {
                    'product_id': asn_landed_cost_line.product_id.id,
                    'name': asn_landed_cost_line.name,
                    'account_id': asn_landed_cost_line.account_id.id,
                    'split_method': asn_landed_cost_line.split_method,
                    'price_unit': asn_landed_cost_line.price_unit,
                }))
            picking_ids.append(picking_id.id)
            vals = {
                'company_id': self.company_id.id,
                'cost_lines': cost_line_vals,
                'picking_ids': picking_ids
            }
            landed_cost = self.env['stock.landed.cost'].create(vals)
            if landed_cost:
                for line in asn_landed_cost_lines:
                    line.sudo().write({'stock_landed_cost_id': landed_cost.id})
                landed_cost_list.append(landed_cost.id)
        if len(landed_cost_list) > 0:
            self.stock_landed_cost_ids = landed_cost_list
