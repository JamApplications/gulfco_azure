from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from datetime import datetime,time,timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools.date_utils import start_of, end_of, add, subtract
from odoo.tools.misc import format_date
from odoo.exceptions import UserError
import time as samay
import logging

_logger = logging.getLogger(__name__)



class DemandPlanning(models.Model):
    _name = "demand.planning"
    _description = "Demand Planning"
    _rec_name = 'product_id'

    @api.model
    def _default_warehouse_id(self):
        warehouse = self.env['stock.warehouse'].search(
            self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
        if not warehouse:
            self.env['stock.warehouse']._warehouse_redirect_warning()
        return warehouse

    product_id = fields.Many2one('product.product', string='Product')
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM',
                                     related='product_id.uom_id')
    demand_planning_line_ids = fields.One2many('demand.planning.line', 'demand_planning_id',
                                               'Lines')
    warehouse_id = fields.Many2one('stock.warehouse', 'Production Warehouse',
                                   required=True, default=lambda self: self._default_warehouse_id())
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    code = fields.Char(string="Code", related="product_id.default_code", store=True)
    source_country_id = fields.Many2one('res.country', string="Source", compute="compute_vendor_product_delay",
                                        store=True, readonly=False)
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    type = fields.Selection([('by_supplier', 'By Supplier'), ('by_product', 'By Product')], default="by_supplier")
    # supplier_mos = fields.Integer(related="vendor_id.supplier_mos", store=True)
    supplier_mos = fields.Integer(compute="compute_vendor_product_mos",related=False, store=True)
    vendor_product_delay = fields.Integer(string="Vendor Product Delay", compute="compute_vendor_product_delay",
                                          store=True)

    @api.depends('product_id', 'product_id.seller_ids', 'vendor_id')
    def compute_vendor_product_mos(self):
        for record in self:
            supplier_mos = 0
            if record.product_id:
                seller_info = record.product_id.seller_ids
                if record.vendor_id:
                    seller_info = seller_info.filtered(lambda s: s.partner_id == record.vendor_id)
                if seller_info:
                    supplier_mos = seller_info[0].supplier_mos
            record.supplier_mos = supplier_mos



    @api.depends('product_id', 'product_id.seller_ids', 'vendor_id')
    def compute_vendor_product_delay(self):
        for record in self:
            vendor_product_delay = 0
            source_country_id = False
            if record.type == 'by_supplier' and record.vendor_id:
                seller_info = self.env['product.supplierinfo'].sudo().search(
                    [('partner_id', '=', record.vendor_id.id), ('source_of_good_country_ids', '!=', False)], limit=1,
                    order='id desc')
                if seller_info:
                    source_country_id = seller_info.source_of_good_country_ids[0].id
            elif record.type == 'by_product' and record.product_id:
                seller_info = record.product_id.seller_ids
                if seller_info:
                    seller_info = seller_info[0]
                    if seller_info.source_of_good_country_ids:
                        source_country_id = seller_info.source_of_good_country_ids[0].id
            if record.vendor_id and record.product_id and record.product_id.seller_ids:
                seller_info = record.product_id.seller_ids.filtered(lambda s: s.partner_id == record.vendor_id)
                if seller_info:
                    seller_info = seller_info[0]
                    if seller_info.source_of_good_country_ids:
                        source_country_id = seller_info.source_of_good_country_ids[0].id
                    vendor_product_delay = seller_info[0].delay
            record.vendor_product_delay = vendor_product_delay
            if not record.source_country_id:
                record.source_country_id = source_country_id

    # @api.onchange('vendor_id')
    # def onchange_vendor_id(self):
    #     if self.vendor_id and self.vendor_id.supplier_mos == 0:
    #         raise UserError('MOS is missing for {} this vendor'.format(self.vendor_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        demand_plannings = super(DemandPlanning, self).create(vals_list)
        if not self.env.context.get('supplier_product_demand'):
            for demand_planning in demand_plannings:
                if demand_planning.type == 'by_supplier' and demand_planning.vendor_id:
                    products = self.env['product.supplierinfo'].sudo().search(
                        [('partner_id', '=', demand_planning.vendor_id.id), ('product_tmpl_id', '!=', False)]).mapped(
                        'product_tmpl_id')
                    if products:
                        flag = False
                        vals_list = []
                        for product in products:
                            if product.product_variant_id:
                                if flag:
                                    vals_list.append(
                                        {'product_id': product.product_variant_id.id, 'type': 'by_supplier',
                                         'vendor_id': demand_planning.vendor_id.id,
                                         'source_country_id': demand_planning.source_country_id.id or False})
                                else:
                                    demand_planning.product_id = product.product_variant_id.id
                                flag = True
                        if len(vals_list) > 0:
                            self.with_context(supplier_product_demand=True).create(vals_list)
        return demand_plannings

    @api.model
    def get_demand_planning_view_state(self, domain=False, offset=0, limit=False, period_scale=False):
        start_time = samay.time()
        demand_plannings = self.env['demand.planning'].search(domain or [], offset=offset, limit=limit)
        count = self.env['demand.planning'].search_count(domain or [])
        demand_planning_states = demand_plannings.get_demand_plannings_view_state(period_scale)
        company_groups = self.env.company.read([
            'mrp_mps_show_starting_inventory',
            'mrp_mps_show_demand_forecast',
            'mrp_mps_show_indirect_demand',
            'mrp_mps_show_actual_demand',
            'mrp_mps_show_to_replenish',
            'mrp_mps_show_actual_replenishment',
            'mrp_mps_show_safety_stock',
            'mrp_mps_show_available_to_promise',
            'mrp_mps_show_actual_demand_year_minus_1',
            'mrp_mps_show_actual_demand_year_minus_2',
        ])
        time_taken = samay.time() - start_time
        _logger.info("\nget_demand_planning_view_state took %s seconds", time_taken)
        return {
            'dates': self._date_range_to_str(period_scale),
            'demand_planning_ids': demand_planning_states,
            'demand_planning_period': period_scale or self.env.company.demand_planning_period,
            'default_period': self.env.company.demand_planning_period,
            'demand_planning_period_types': [s[0] for s in
                                             self.env.company._fields['demand_planning_period'].selection],
            'company_id': self.env.company.id,
            'groups': company_groups,
            'count': count,
        }

    def get_demand_plannings_view_state(self, period_scale=False):
        """Optimized version of demand planning view state calculation"""
        if not self:
            return []
        date_range = self._get_date_range(force_period=period_scale)
        read_fields = [
            'product_id',
            'code',
            'source_country_id',
            'supplier_mos',
            'vendor_id',
            'vendor_product_delay'
        ]
        if self.env.user.has_group('uom.group_uom'):
            read_fields.append('product_uom_id')
        demand_planning_states = self.read(read_fields)
        demand_planning_states_by_id = {dps['id']: dps for dps in demand_planning_states}
        location_ids = self.env['stock.location'].search(['|',('is_saleable_location','=',True),('usage','=','production')])
        supplier_location_ids = self.env['stock.location'].search([('usage', '=', 'supplier')])
        out_going_picking_type_ids = self.env['stock.picking.type'].sudo().search([('code', '=', 'outgoing')])
        product_ids = self.product_id.ids

        # Calculate global date range for batch queries
        min_global_date = min(dr[0] for dr in date_range)
        max_global_date = max(dr[1] for dr in date_range)
        min_global_dt = datetime.combine(min_global_date, time.min)
        max_global_dt = datetime.combine(max_global_date, time.max)

        # Batch query for all stock move lines
        all_in_move_lines = self.env['stock.move.line'].search([
            ('state', '=', 'done'),
            ('location_dest_id', 'in', location_ids.ids),
            ('product_id', 'in', product_ids),
            ('date', '<=', max_global_dt)
        ]) if location_ids and product_ids else self.env['stock.move.line']

        all_out_move_lines = self.env['stock.move.line'].search([
            ('state', '=', 'done'),
            ('location_id', 'in', location_ids.ids),
            ('product_id', 'in', product_ids),
            ('date', '<=', max_global_dt)
        ]) if location_ids and product_ids else self.env['stock.move.line']

        # Batch query for near expiry lots
        all_near_expiry_lots = self.env['stock.lot'].search([
            ('product_qty', '>', 0),
            ('product_id', 'in', product_ids)
        ]) if product_ids else self.env['stock.lot']

        # Batch query for purchase order lines
        all_asn_request_lines = self.env['purchase.order.line'].sudo().search([
            ('product_id', 'in', product_ids),
            ('date_planned', '<=', max_global_dt),
            ('date_planned', '>=', min_global_dt),
            ('order_id.state', '=', 'purchase')
        ]) if product_ids else self.env['purchase.order.line']

        # Batch query for supplier move lines
        all_supplier_move_lines = self.env['stock.move.line'].search([
            ('location_id', 'in', supplier_location_ids.ids),
            ('product_id', 'in', product_ids),
            ('date', '<=', max_global_dt),
            ('date', '>=', min_global_dt),
            ('picking_id', '!=', False),
            ('picking_id.return_id', '=', False),
            ('state', '=', 'done')
        ]) if supplier_location_ids and product_ids else self.env['stock.move.line']

        # Batch query for outgoing picking types and sale moves
        all_sale_done_moves = self.env['stock.move'].sudo().search([
            ('picking_type_id', 'in', out_going_picking_type_ids.ids),
            ('product_id', 'in', product_ids),
            ('state', '=', 'done'),
            ('picking_id.date_done', '>=', min_global_dt),
            ('picking_id.date_done', '<=', max_global_dt)
        ]) if out_going_picking_type_ids and product_ids else self.env['stock.move']

        # Reorganize and group data by product_id for efficient lookup
        in_moves_by_product = {}
        out_moves_by_product = {}
        lots_by_product = {}
        po_lines_by_product = {}
        supplier_moves_by_product = {}
        sale_moves_by_product = {}

        for move in all_in_move_lines:
            product_id = move.product_id.id
            if product_id not in in_moves_by_product:
                in_moves_by_product[product_id] = []
            in_moves_by_product[product_id].append(move)

        for move in all_out_move_lines:
            product_id = move.product_id.id
            if product_id not in out_moves_by_product:
                out_moves_by_product[product_id] = []
            out_moves_by_product[product_id].append(move)

        for lot in all_near_expiry_lots:
            product_id = lot.product_id.id
            if product_id not in lots_by_product:
                lots_by_product[product_id] = []
            lots_by_product[product_id].append(lot)

        for line in all_asn_request_lines:
            product_id = line.product_id.id
            if product_id not in po_lines_by_product:
                po_lines_by_product[product_id] = []
            po_lines_by_product[product_id].append(line)

        for move in all_supplier_move_lines:
            product_id = move.product_id.id
            if product_id not in supplier_moves_by_product:
                supplier_moves_by_product[product_id] = []
            supplier_moves_by_product[product_id].append(move)

        for move in all_sale_done_moves:
            product_id = move.product_id.id
            if product_id not in sale_moves_by_product:
                sale_moves_by_product[product_id] = []
            sale_moves_by_product[product_id].append(move)

        for demand_planning in self:
            demand_planning_state = demand_planning_states_by_id[demand_planning['id']]
            demand_planning_state['demand_planning_line_ids'] = []

            demand_planning_product = demand_planning.product_id
            product_id = demand_planning_product.id

            for index, (date_start, date_stop) in enumerate(date_range):
                if date_stop <= date.today():
                    line_data_type = 'Actual'
                else:
                    line_data_type = 'Estimated'
                if period_scale == 'year' and date_start <= date.today() <= date_stop:
                    line_data_type = 'Actual'
                # key = ((date_start, date_stop), demand_planning_product, demand_planning.warehouse_id)
                existing_demand_planning_ids = demand_planning.demand_planning_line_ids.filtered(
                    lambda p: date_start <= p.date <= date_stop)

                opening_stock_qty = 0.0
                opening_stock_regular_qty = 0.0
                near_expiry_qty = 0.0
                receipt_en_route_qty = 0.0
                actual_sales_regular_qty = 0.0
                actual_sales_promo_qty = 0.0
                return_sales_regular_qty = 0.0
                return_sales_promo_qty = 0.0
                min_dt = datetime.combine(date_start, time.min)
                max_dt = datetime.combine(date_stop, time.max)                
                if location_ids:
                    # Calculate opening stock using pre-fetched data
                    in_move_lines = [m for m in in_moves_by_product.get(product_id, []) if m.date <= min_dt]
                    out_move_lines = [m for m in out_moves_by_product.get(product_id, []) if m.date <= min_dt]
                    opening_stock_qty = sum(m.quantity for m in in_move_lines) - sum(m.quantity for m in out_move_lines)
                    opening_stock_regular_qty = sum(
                        m.quantity for m in in_move_lines if m.location_dest_id.is_saleable_location
                    ) - sum(
                        m.quantity for m in out_move_lines if m.location_id.is_saleable_location
                    )

                # Calculate near expiry quantity using pre-fetched data
                near_expiry_lots = lots_by_product.get(product_id, [])
                for near_expiry_lot in near_expiry_lots:
                    expiry_date = near_expiry_lot.expiration_date
                    if expiry_date:
                        months = 6
                        if demand_planning_product.division == 'food':
                            months = 3
                        elif demand_planning_product.division == 'non_food':
                            months = 6
                        elif demand_planning_product.division == 'mars':
                            months = 2
                        expiry_date_stop = date_stop + relativedelta(months=months)
                        if expiry_date.date() <= expiry_date_stop:
                            near_expiry_qty += near_expiry_lot.product_qty

                # Calculate receipt en route using pre-fetched data
                asn_request_lines = [
                    line for line in po_lines_by_product.get(product_id, [])
                    if min_dt <= line.date_planned <= max_dt
                ]

                po_qty = 0
                for asn_request_line in asn_request_lines:
                    if asn_request_line.product_qty < asn_request_line.qty_received:
                        po_qty = po_qty + 0
                    else:
                        po_qty = po_qty + (asn_request_line.product_qty - asn_request_line.qty_received)

                receipt_en_route_qty = po_qty

                # Add supplier moves to receipt en route
                move_lines = [
                    m for m in supplier_moves_by_product.get(product_id, [])
                    if min_dt <= m.date <= max_dt
                ]
                receipt_en_route_qty += sum(m.quantity for m in move_lines)

                # Calculate sales quantities using pre-fetched data
                if out_going_picking_type_ids:            
                    sale_done_move = [
                        m for m in sale_moves_by_product.get(product_id, [])
                        if m.picking_id.date_done and date_start <= m.picking_id.date_done.date() <= date_stop
                    ]

                    return_ids = self.env['stock.picking']
                    lot_ids = self.env['stock.lot']
                    move_lines = self.env['stock.move.line']
                    for move in sale_done_move:
                        return_ids |= move.picking_id.return_ids
                        lot_ids |= move.lot_ids
                        move_lines |= move.move_line_ids

                    return_done_move = return_ids.mapped('move_ids').filtered(
                        lambda s: s.product_id == demand_planning_product and s.state == 'done')
                    traceability_report = self.env['stock.traceability.report']
                    for lot in lot_ids:
                        move_lines = move_lines.filtered(lambda s: s.lot_id == lot)
                        rec_id = lot.id
                        model = 'stock.lot'
                        if rec_id and model == 'stock.lot':
                            lines = self.env['stock.move.line'].search([
                                ('lot_id', '=', rec_id),
                                ('state', '=', 'done'),
                            ])
                        move_line_vals = traceability_report._lines(False, model_id=rec_id, model=model, level=1,
                                                                    move_lines=lines)
                        final_vals = sorted(move_line_vals, key=lambda v: v['date'])
                        lines = traceability_report._final_vals_to_lines(final_vals, level=1)
                        return_movel_lines = return_done_move.mapped('move_line_ids').filtered(
                            lambda s: s.lot_id == lot)
                        if len(lines) > 0:
                            line = lines[0]
                            if line.get('res_model') == 'mrp.production':
                                current_actual_sales_promo_qty = sum(move_lines.mapped('qty_done')) - sum(return_movel_lines.mapped('qty_done'))
                                if line.get('res_id'):
                                    mrp_order_id = self.env['mrp.production'].browse(line.get('res_id'))
                                    if mrp_order_id.move_raw_ids.filtered(lambda s:s.product_id == demand_planning_product):
                                        component_qty = sum(mrp_order_id.move_raw_ids.filtered(
                                            lambda s: s.product_id == demand_planning_product).mapped('quantity'))
                                        actual_sales_promo_qty +=  current_actual_sales_promo_qty * component_qty
                                    else:
                                        actual_sales_promo_qty += current_actual_sales_promo_qty
                                else:
                                    actual_sales_promo_qty += current_actual_sales_promo_qty

                            elif line.get('res_model') == 'stock.picking':
                                picking_id = self.env[line.get('res_model')].browse(line.get('res_id'))
                                if picking_id and picking_id.picking_type_id.code == 'incoming':
                                    actual_sales_regular_qty += sum(move_lines.mapped('qty_done'))
                                    return_sales_regular_qty += sum(return_movel_lines.mapped('qty_done'))
                                    
                cartoon_qty = False
                if demand_planning_product.packaging_ids:
                    ctn_packages = demand_planning_product.packaging_ids.filtered(
                        lambda s: s.package_type_id.type == 'ctn')
                    if ctn_packages:
                        cartoon_qty = ctn_packages[0].qty

                line_values = {
                    'line_data_type': line_data_type,
                    # 'vendor_product_delay':vendor_product_delay,
                    'date_start': date_start,
                    'date_stop': date_stop,
                    'date': date_stop,
                    'opening_stock_qty': opening_stock_qty / cartoon_qty if cartoon_qty else opening_stock_qty,
                    'opening_stock_regular_qty': opening_stock_regular_qty / cartoon_qty if cartoon_qty else opening_stock_regular_qty,
                    'near_expiry_qty': near_expiry_qty / cartoon_qty if cartoon_qty else near_expiry_qty,
                    'receipt_en_route_qty': receipt_en_route_qty / cartoon_qty if cartoon_qty else receipt_en_route_qty,
                    'actual_sales_regular_qty': (
                                                        actual_sales_regular_qty - return_sales_regular_qty) / cartoon_qty if cartoon_qty else actual_sales_regular_qty - return_sales_regular_qty,
                    'actual_sales_promo_qty': actual_sales_promo_qty  / cartoon_qty if cartoon_qty else actual_sales_promo_qty,
                    'regular_sales_qty': existing_demand_planning_ids[
                        0].regular_sales_qty if existing_demand_planning_ids else 0.0,
                    'promotion_sales_qty': existing_demand_planning_ids[
                        0].promotion_sales_qty if existing_demand_planning_ids else 0.0,
                    'to_order_qty': existing_demand_planning_ids[
                        0].to_order_qty if existing_demand_planning_ids else 0.0,
                    'actual_to_order_qty': existing_demand_planning_ids[
                        0].actual_to_order_qty if existing_demand_planning_ids else 0.0,
                    'is_set_manually_to_order': existing_demand_planning_ids[
                        0].is_set_manually_to_order if existing_demand_planning_ids else False,

                }
                copy_line_values = line_values.copy()
                copy_line_values.pop('date_start')
                copy_line_values.pop('date_stop')
                demand_planning_state['demand_planning_line_ids'].append(line_values)
                if existing_demand_planning_ids:
                    existing_demand_planning_ids[0].write(copy_line_values)
                else:
                    copy_line_values.update({'demand_planning_id': demand_planning.id})
                    existing_demand_planning_ids.create(copy_line_values)
        return [demand_planning_states_by_id[_id] for _id in self.ids if _id in demand_planning_states_by_id]

    # def get_demand_plannings_view_state(self, period_scale=False):
    #     # Original - Not optimized --- IGNORE ---
    #     date_range = self._get_date_range(force_period=period_scale)
    #     read_fields = [
    #         'product_id',
    #         'code',
    #         'source_country_id',
    #         'supplier_mos',
    #         'vendor_id',
    #         'vendor_product_delay'
    #     ]
    #     if self.env.user.has_group('uom.group_uom'):
    #         read_fields.append('product_uom_id')
    #     demand_planning_states = self.read(read_fields)
    #     demand_planning_states_by_id = {dps['id']: dps for dps in demand_planning_states}
    #     location_ids = self.env['stock.location'].search(['|',('is_saleable_location','=',True),('usage','=','production')])
        
    #     for demand_planning in self:
    #         demand_planning_state = demand_planning_states_by_id[demand_planning['id']]
    #         demand_planning_state['demand_planning_line_ids'] = []
    #         for index, (date_start, date_stop) in enumerate(date_range):
    #             # if date_start <= date.today() <= date_stop:
    #             #     line_data_type = 'Actual'
    #             # vendor_product_delay = 0
    #             # if demand_planning.vendor_id and demand_planning.product_id:
    #             #     products_supp_info = self.env['product.supplierinfo'].sudo().search(
    #             #         [('partner_id', '=', demand_planning.vendor_id.id),
    #             #          ('product_tmpl_id', '=', demand_planning.product_id.product_tmpl_id.id)], limit=1)
    #             #     if products_supp_info:
    #             #         vendor_product_delay = products_supp_info.delay
    #             if date_stop <= date.today():
    #                 line_data_type = 'Actual'
    #             else:
    #                 line_data_type = 'Estimated'
    #             if period_scale == 'year' and date_start <= date.today() <= date_stop:
    #                 line_data_type = 'Actual'
    #             # key = ((date_start, date_stop), demand_planning.product_id, demand_planning.warehouse_id)
    #             existing_demand_planning_ids = demand_planning.demand_planning_line_ids.filtered(
    #                 lambda p: date_start <= p.date <= date_stop)
    #             product_list = demand_planning.product_id.with_context(to_date=date_stop).read(
    #                 [
    #                     'qty_available',
    #                 ])
    #             opening_stock_qty = 0.0
    #             opening_stock_regular_qty = 0.0
    #             near_expiry_qty = 0.0
    #             receipt_en_route_qty = 0.0
    #             actual_sales_regular_qty = 0.0
    #             actual_sales_promo_qty = 0.0
    #             return_sales_regular_qty = 0.0
    #             return_sales_promo_qty = 0.0
    #             # near_expiry_quants = self.env['stock.quant'].search([
    #             #     ('quantity', '>', 0),
    #             #     ('product_id', '=', demand_planning.product_id.id)
    #             # ])
    #             min_dt = datetime.combine(date_start, time.min)
    #             max_dt = datetime.combine(date_stop, time.max)                
    #             if location_ids:
    #                 # in_move_lines = self.env['stock.move.line'].search([('state','=','done'),('location_dest_id', 'in', location_ids.ids),('product_id','=',demand_planning.product_id.id), ('date', '<=', max_dt),('date', '>=', min_dt)])
    #                 # out_move_lines = self.env['stock.move.line'].search([('state','=','done'),('location_id', 'in', location_ids.ids),('product_id','=',demand_planning.product_id.id), ('date', '<=', max_dt),('date', '>=', min_dt)])
    #                 in_move_lines = self.env['stock.move.line'].search([('state','=','done'),('location_dest_id', 'in', location_ids.ids),('product_id','=',demand_planning.product_id.id), ('date', '<=', min_dt)])
    #                 out_move_lines = self.env['stock.move.line'].search([('state','=','done'),('location_id', 'in', location_ids.ids),('product_id','=',demand_planning.product_id.id), ('date', '<=', min_dt)])
    #                 opening_stock_qty = sum(in_move_lines.mapped('quantity')) - sum(out_move_lines.mapped('quantity'))
    #                 opening_stock_regular_qty = sum(in_move_lines.filtered(lambda s:s.location_dest_id.is_saleable_location).mapped('quantity')) - sum(out_move_lines.filtered(lambda s:s.location_id.is_saleable_location).mapped('quantity'))
    #                 # opening_stock_regular_qty = sum(move_lines.filtered(lambda s:s.location_id.is_saleable_location or s.location_dest_id.is_saleable_location).mapped('quantity'))
    #                 # opening_stock_qty = sum(move_lines.mapped('quantity'))

    #             near_expiry_lots = self.env['stock.lot'].search([
    #                 ('product_qty', '>', 0),
    #                 ('product_id', '=', demand_planning.product_id.id)
    #             ])
    #             for near_expiry_lot in near_expiry_lots:
    #                 expiry_date = near_expiry_lot.expiration_date
    #                 if expiry_date:
    #                     months = 6
    #                     if demand_planning.product_id.division == 'food':
    #                         months = 3
    #                     elif demand_planning.product_id.division == 'non_food':
    #                         months = 6
    #                     elif demand_planning.product_id.division == 'mars':
    #                         months = 2
    #                     # expiration_threshold = expiry_date - relativedelta(months=months)
    #                     # expiry_date_start = date_start + relativedelta(months=months)
    #                     expiry_date_stop = date_stop + relativedelta(months=months)
    #                     if expiry_date.date() <= expiry_date_stop:
    #                         # if  date_start <= expiry_date.date() <= expiry_date_stop:
    #                         # print('---------------------', date_start, near_expiry_lot.product_qty)
    #                         near_expiry_qty += near_expiry_lot.product_qty
    #             # if product_list:
    #             #     opening_stock_qty = product_list[0]['qty_available']
    #             # picking_type_ids = self.env['stock.picking.type'].sudo().search([('code', '=', 'incoming')])
    #             # if picking_type_ids:
    #             #     done_move = self.env['stock.move'].sudo().search([('picking_type_id', 'in', picking_type_ids.ids),
    #             #                                                       (
    #             #                                                           'product_id', '=',
    #             #                                                           demand_planning.product_id.id),
    #             #                                                       ('state', '=', 'done')])
    #             #     if done_move:
    #             #         for move in done_move:
    #             #             if move.picking_id.date_done:
    #             #                 move_date = move.picking_id.date_done.date()
    #             #                 # move_date = move.picking_id.date_done.date() - relativedelta(months=1)
    #             #                 move_date_start = date_start + relativedelta(months=1)
    #             #                 move_date_stop = date_stop + relativedelta(months=1)
    #             #                 if date_start <= move_date <= date_stop:
    #             #                     receipt_en_route_qty += move.quantity
    #             #         done_move = done_move.filtered(
    #             #             lambda p: p.picking_id.date_done and date_start <= p.picking_id.date_done.date() <= date_stop)
    #             #         opening_stock_regular_qty = sum(done_move.mapped('quantity'))



    #             asn_request_lines = self.env['purchase.order.line'].sudo().search(
    #                 [('product_id', '=', demand_planning.product_id.id),
    #                  ('date_planned', '<=', max_dt),
    #                  ('date_planned', '>=', min_dt),('order_id.state','=','purchase')])

    #             po_qty = 0
    #             for asn_request_line in asn_request_lines:
    #                 if asn_request_line.product_qty < asn_request_line.qty_received:
    #                     po_qty = po_qty + 0
    #                 else:
    #                     po_qty = po_qty + (asn_request_line.product_qty - asn_request_line.qty_received)

    #             receipt_en_route_qty = po_qty

    #             location_ids =  self.env['stock.location'].search([('usage','=','supplier')])
    #             move_lines = self.env['stock.move.line'].search(
    #                 [('location_id', 'in', location_ids.ids),('product_id','=',demand_planning.product_id.id),
    #                  ('date', '<=', max_dt), ('date', '>=', min_dt), ('picking_id', '!=', False),('picking_id.return_id','=',False),('state','=','done')])
    #             receipt_en_route_qty = receipt_en_route_qty + sum(move_lines.mapped('quantity'))

    #             out_going_picking_type_ids = self.env['stock.picking.type'].sudo().search([('code', '=', 'outgoing')])
    #             if out_going_picking_type_ids:
    #                 sale_done_move = self.env['stock.move'].sudo().search(
    #                     [('picking_type_id', 'in', out_going_picking_type_ids.ids),
    #                      ('product_id', '=', demand_planning.product_id.id),
    #                      ('state', '=', 'done')])
    #                 sale_done_move = sale_done_move.filtered(
    #                     lambda p: p.picking_id.date_done and date_start <= p.picking_id.date_done.date() <= date_stop)
    #                 return_ids = sale_done_move.mapped('picking_id').mapped('return_ids')
    #                 return_done_move = return_ids.mapped('move_ids').filtered(
    #                     lambda s: s.product_id == demand_planning.product_id and s.state == 'done')
    #                 lot_ids = sale_done_move.mapped('lot_ids')
    #                 traceability_report = self.env['stock.traceability.report']
    #                 for lot in lot_ids:
    #                     move_lines = sale_done_move.mapped('move_line_ids').filtered(lambda s: s.lot_id == lot)
    #                     rec_id = lot.id
    #                     model = 'stock.lot'
    #                     if rec_id and model == 'stock.lot':
    #                         lines = move_lines.search([
    #                             ('lot_id', '=', rec_id),
    #                             ('state', '=', 'done'),
    #                         ])
    #                     move_line_vals = traceability_report._lines(False, model_id=rec_id, model=model, level=1,
    #                                                                 move_lines=lines)
    #                     final_vals = sorted(move_line_vals, key=lambda v: v['date'])
    #                     lines = traceability_report._final_vals_to_lines(final_vals, level=1)
    #                     return_movel_lines = return_done_move.mapped('move_line_ids').filtered(
    #                         lambda s: s.lot_id == lot)
    #                     if len(lines) > 0:
    #                         line = lines[0]
    #                         if line.get('res_model') == 'mrp.production':
    #                             # actual_sales_promo_qty += sum(move_lines.mapped('qty_done'))
    #                             # return_sales_promo_qty += sum(return_movel_lines.mapped('qty_done'))
    #                             current_actual_sales_promo_qty = sum(move_lines.mapped('qty_done')) - sum(return_movel_lines.mapped('qty_done'))
    #                             if line.get('res_id'):
    #                                 mrp_order_id = self.env['mrp.production'].browse(line.get('res_id'))
    #                                 if mrp_order_id.move_raw_ids.filtered(lambda s:s.product_id == demand_planning.product_id):
    #                                     component_qty = sum(mrp_order_id.move_raw_ids.filtered(
    #                                         lambda s: s.product_id == demand_planning.product_id).mapped('quantity'))
    #                                     actual_sales_promo_qty +=  current_actual_sales_promo_qty * component_qty
    #                                 else:
    #                                     actual_sales_promo_qty += current_actual_sales_promo_qty
    #                             else:
    #                                 actual_sales_promo_qty += current_actual_sales_promo_qty
    #                             # opening_stock_qty += sum(move_lines.mapped('qty_done'))

    #                         elif line.get('res_model') == 'stock.picking':
    #                             picking_id = self.env[line.get('res_model')].browse(line.get('res_id'))
    #                             if picking_id and picking_id.picking_type_id.code == 'incoming':
    #                                 # opening_stock_qty += sum(move_lines.mapped('qty_done'))
    #                                 # opening_stock_regular_qty += sum(move_lines.mapped('qty_done'))
    #                                 actual_sales_regular_qty += sum(move_lines.mapped('qty_done'))
    #                                 return_sales_regular_qty += sum(return_movel_lines.mapped('qty_done'))
    #                 # actual_sales_regular_qty = sum(sale_done_move.mapped('quantity')) - sum(return_done_move.mapped('quantity'))
    #                 # actual_sales_promo_qty = actual_sales_regular_qty
    #             # if demand_planning.product_id:
    #             #     template_ids = demand_planning.product_id.product_tmpl_id.ids
    #             #     mrp_bom_ids = self.env['mrp.bom'].search(['|', '|', ('byproduct_ids.product_id', 'in', demand_planning.product_id.ids), ('product_id', 'in', demand_planning.product_id.ids), '&', ('product_id', '=', False), ('product_tmpl_id', 'in', template_ids)])
    #             #     if mrp_bom_ids:
    #             #         bom_line_ids = mrp_bom_ids.mapped('bom_line_ids').mapped('product_qty')
    #             cartoon_qty = False
    #             if demand_planning.product_id.packaging_ids:
    #                 ctn_packages = demand_planning.product_id.packaging_ids.filtered(
    #                     lambda s: s.package_type_id.type == 'ctn')
    #                 if ctn_packages:
    #                     cartoon_qty = ctn_packages[0].qty

    #             line_values = {
    #                 'line_data_type': line_data_type,
    #                 # 'vendor_product_delay':vendor_product_delay,
    #                 'date_start': date_start,
    #                 'date_stop': date_stop,
    #                 'date': date_stop,
    #                 'opening_stock_qty': opening_stock_qty / cartoon_qty if cartoon_qty else opening_stock_qty,
    #                 'opening_stock_regular_qty': opening_stock_regular_qty / cartoon_qty if cartoon_qty else opening_stock_regular_qty,
    #                 'near_expiry_qty': near_expiry_qty / cartoon_qty if cartoon_qty else near_expiry_qty,
    #                 'receipt_en_route_qty': receipt_en_route_qty / cartoon_qty if cartoon_qty else receipt_en_route_qty,
    #                 'actual_sales_regular_qty': (
    #                                                     actual_sales_regular_qty - return_sales_regular_qty) / cartoon_qty if cartoon_qty else actual_sales_regular_qty - return_sales_regular_qty,
    #                 'actual_sales_promo_qty': actual_sales_promo_qty  / cartoon_qty if cartoon_qty else actual_sales_promo_qty,
    #                 'regular_sales_qty': existing_demand_planning_ids[
    #                     0].regular_sales_qty if existing_demand_planning_ids else 0.0,
    #                 'promotion_sales_qty': existing_demand_planning_ids[
    #                     0].promotion_sales_qty if existing_demand_planning_ids else 0.0,
    #                 'to_order_qty': existing_demand_planning_ids[
    #                     0].to_order_qty if existing_demand_planning_ids else 0.0,
    #                 'actual_to_order_qty': existing_demand_planning_ids[
    #                     0].actual_to_order_qty if existing_demand_planning_ids else 0.0,
    #                 'is_set_manually_to_order': existing_demand_planning_ids[
    #                     0].is_set_manually_to_order if existing_demand_planning_ids else False,

    #             }
    #             copy_line_values = line_values.copy()
    #             copy_line_values.pop('date_start')
    #             copy_line_values.pop('date_stop')
    #             demand_planning_state['demand_planning_line_ids'].append(line_values)
    #             if existing_demand_planning_ids:
    #                 # copy_line_values['regular_sales_qty'] = existing_demand_planning_ids[0].regular_sales_qty
    #                 # copy_line_values['promotion_sales_qty'] = existing_demand_planning_ids[0].promotion_sales_qty
    #                 existing_demand_planning_ids[0].write(copy_line_values)
    #             else:
    #                 copy_line_values.update({'demand_planning_id': demand_planning.id})
    #                 existing_demand_planning_ids.create(copy_line_values)
    #     return [demand_planning_states_by_id[_id] for _id in self.ids if _id in demand_planning_states_by_id]

    def _get_date_range(self, years=False, force_period=False):
        date_range = []
        period = force_period or self.env.company.demand_planning_period
        if not years:
            years = 0
        first_day = start_of(
            subtract(fields.Date.today() - relativedelta(months=self.env.company.previous_column_number), years=years),
            period)
        column_range = self.env.company['demand_planning_period_to_display_%s' % period] + self.env.company.previous_column_number
        for columns in range(column_range):
            last_day = end_of(first_day, period)
            date_range.append((first_day, last_day))
            first_day = add(last_day, days=1)
        return date_range

    def _date_range_to_str(self, force_period=False):
        date_range = self._get_date_range(force_period=force_period)
        dates_as_str = []
        period = force_period or self.env.company.demand_planning_period
        for date_start, date_stop in date_range:
            if period == 'year':
                dates_as_str.append(format_date(self.env, date_start, date_format='yyyy'))
            elif period == 'month':
                dates_as_str.append(format_date(self.env, date_start, date_format='MMM yyyy'))
            elif period == 'week':
                dates_as_str.append(_('Week %(week_num)s (%(start_date)s-%(end_date)s/%(month)s)',
                                      week_num=format_date(self.env, date_start, date_format='w'),
                                      start_date=format_date(self.env, date_start, date_format='d'),
                                      end_date=format_date(self.env, date_stop, date_format='d'),
                                      month=format_date(self.env, date_stop, date_format='MMM')
                                      ))
            else:
                dates_as_str.append(format_date(self.env, date_start, date_format='MMM d'))
        return dates_as_str

    def set_demandPlanningId(self, date_index, quantity, period_scale=False):
        self.ensure_one()
        date_start, date_stop = self._get_date_range(force_period=period_scale)[date_index]
        existing_demand_line = self.demand_planning_line_ids.filtered(lambda f:
                                                                      f.date >= date_start and f.date <= date_stop)
        # quantity = float_round(float(quantity), precision_rounding=self.product_uom_id.rounding)
        # quantity_to_add = quantity - sum(existing_demand_line.mapped('regular_sales_qty'))
        if existing_demand_line:
            new_qty = quantity
            # new_qty = existing_demand_line[0].regular_sales_qty + quantity_to_add
            new_qty = float_round(float(new_qty), precision_rounding=self.product_uom_id.rounding)
            existing_demand_line[0].write({
                'regular_sales_qty': new_qty,
            })
        else:
            existing_demand_line.create({
                'date': date_stop,
                'regular_sales_qty': quantity,
                'demand_planning_id': self.id
            })
        return True

    def set_promo_demandPlanningId(self, date_index, quantity, period_scale=False):
        self.ensure_one()
        date_start, date_stop = self._get_date_range(force_period=period_scale)[date_index]
        existing_demand_line = self.demand_planning_line_ids.filtered(lambda f:
                                                                      f.date >= date_start and f.date <= date_stop)
        # quantity = float_round(float(quantity), precision_rounding=self.product_uom_id.rounding)
        # quantity_to_add = quantity - sum(existing_demand_line.mapped('promotion_sales_qty'))
        if existing_demand_line:
            new_qty = quantity
            # new_qty = existing_demand_line[0].regular_sales_qty + quantity_to_add
            new_qty = float_round(float(new_qty), precision_rounding=self.product_uom_id.rounding)
            existing_demand_line[0].write({
                'promotion_sales_qty': new_qty,
            })
        else:
            existing_demand_line.create({
                'date': date_stop,
                'promotion_sales_qty': quantity,
                'demand_planning_id': self.id
            })
        return True

    def set_to_order_qty_demandPlanningId(self, date_index, quantity, period_scale=False):
        self.ensure_one()
        date_start, date_stop = self._get_date_range(force_period=period_scale)[date_index]
        existing_demand_line = self.demand_planning_line_ids.filtered(lambda f:
                                                                      f.date >= date_start and f.date <= date_stop)
        if existing_demand_line:
            new_qty = quantity
            new_qty = float_round(float(new_qty), precision_rounding=self.product_uom_id.rounding)
            existing_demand_line[0].write({
                'to_order_qty': new_qty,
                'actual_to_order_qty': new_qty,
                'is_set_manually_to_order': True
            })
        else:
            existing_demand_line.create({
                'date': date_stop,
                'to_order_qty': quantity,
                'actual_to_order_qty': quantity,
                'demand_planning_id': self.id,
                'is_set_manually_to_order': True
            })
        return True

    def action_order_analysis(self, demand_planning_ids):
        if len(demand_planning_ids) > 0:
            demand_planning_ids = self.browse(demand_planning_ids)
            today = date.today()
            first_day = start_of(today, 'month')
            last_day = end_of(first_day, 'month')
            purchase_request_ids = []
            current_month_demand_lines = demand_planning_ids.mapped('demand_planning_line_ids').filtered(
                lambda s: first_day <= s.date <= last_day)
            other_month_demand_lines = demand_planning_ids.mapped('demand_planning_line_ids').filtered(
                lambda s: s not in current_month_demand_lines)
            purchase_request_model = self.env["purchase.request"]
            purchase_request_line_model = self.env["purchase.request.line"]
            # if current_month_demand_lines and len(current_month_demand_lines) == len(demand_planning_ids):
            purchase_request_vals = self._prepare_purchase_request(current_month_demand_lines)
            pr = purchase_request_model.with_context(from_order_analysis=1,
                                                     order_date=current_month_demand_lines[0].date).create(
                purchase_request_vals)
            request_line_data = self._prepare_purchase_request_line(pr, current_month_demand_lines)
            purchase_request_line_model.create(request_line_data)
            purchase_request_ids.append(pr.id)
            # else:
            #     raise UserError('Please Configure To order qty in all product in current month period')

            # comment code for the creation of other month lines
            # if other_month_demand_lines:
            #     for line in other_month_demand_lines:
            #         other_purchase_request_vals = self.with_context(other_month=True)._prepare_purchase_request(line)
            #         other_pr = purchase_request_model.with_context(from_order_analysis=1, order_date=line.date).create(
            #             other_purchase_request_vals)
            #         other_request_line_data = self._prepare_purchase_request_line(other_pr, line)
            #         purchase_request_line_model.create(other_request_line_data)
            #         purchase_request_ids.append(other_pr.id)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.request',
                'views': [(False, 'list'), (False, 'form')],
                'view_mode': 'list,form',
                'name': 'Order Analysis',
                'target': 'current',
                'domain': [('id', 'in', purchase_request_ids)],
                'context': {"search_default_supplier_id": 1, 'from_order_analysis': 1,
                            'default_request_type': 'order_analysis'}
            }


        else:
            raise UserError('Demand Planning record does not exist')

    @api.model
    def _prepare_purchase_request(self, current_month_demand_lines):
        if self.env.context.get('other_month'):
            date_start = current_month_demand_lines.date
        else:
            date_start = date.today()
        demand_planning_ids = current_month_demand_lines.mapped('demand_planning_id')
        type_obj = self.env["stock.picking.type"]
        company_id = self.env.company.id
        picking_types = type_obj.search(
            [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company_id)]
        )
        if not picking_types:
            picking_types = type_obj.search(
                [("code", "=", "incoming"), ("warehouse_id", "=", False)]
            )
        return {
            "origin": 'Demand Planning {}'.format(date_start.strftime('%Y-%m-%d')),
            "company_id": self.env.company.id,
            "picking_type_id": picking_types[:1].id,
            "group_id": False,
            "requested_by": self.env.user.id,
            "demand_planning_ids": demand_planning_ids.ids,
            "date_start": date_start,
            "request_type": 'order_analysis'
        }

    @api.model
    def _prepare_purchase_request_line(self, request_id, current_month_demand_lines):
        val_list = []
        for line in current_month_demand_lines:
            line_qty = line.actual_to_order_qty
            pallete_qty = line.actual_to_order_qty
            # ctn_packages = line.demand_planning_id.product_id.packaging_ids.filtered(
            #     lambda s: s.package_type_id.type == 'ctn')
            pallete_packages = line.demand_planning_id.product_id.packaging_ids.filtered(
                lambda s: s.package_type_id.is_pallete_package)
            # if ctn_packages:
            #     cartoon_qty = ctn_packages[0].qty
            #     line_qty = cartoon_qty * line_qty
            if pallete_packages:
                if pallete_packages[0].qty > 0.0:
                    pallete_qty = line_qty / pallete_packages[0].qty

            val_list.append({
                "product_id": line.demand_planning_id.product_id.id,
                "name": line.demand_planning_id.product_id.name,
                "date_required": fields.Datetime.now(),
                "product_uom_id": line.demand_planning_id.product_id.uom_po_id.id,
                "product_qty": line_qty,
                "request_id": request_id.id,
                "lrf_qty": line.actual_to_order_qty,
                'purchased_qty': line.actual_to_order_qty,
                "product_packaging_id": pallete_packages[0].id if pallete_packages else False,
                "product_packaging_qty": pallete_qty,
                "country_of_origin": line.demand_planning_id.source_country_id.id or False
            })
        return val_list

    def set_actual_to_order(self, to_order, date_index, period_scale=False):
        self.ensure_one()
        date_start, date_stop = self._get_date_range(force_period=period_scale)[date_index]
        existing_demand_line = self.demand_planning_line_ids.filtered(lambda f:
                                                                      f.date >= date_start and f.date <= date_stop)
        if existing_demand_line:
            new_qty = to_order
            if isinstance(new_qty, float) or isinstance(new_qty, int):
                new_qty = float_round(float(new_qty), precision_rounding=self.product_uom_id.rounding)
            else:
                new_qty = 0.0
            existing_demand_line[0].write({
                'actual_to_order_qty': new_qty
            })
        return True


class DemandPlanningLine(models.Model):
    _name = 'demand.planning.line'
    _order = 'date'
    _description = 'Demand Planning Line'

    demand_planning_id = fields.Many2one('demand.planning',
                                         required=True, ondelete='cascade')
    date = fields.Date('Date', required=True)
    code = fields.Char(related="demand_planning_id.code")
    source_country_id = fields.Many2one('res.country', related="demand_planning_id.source_country_id")
    opening_stock_qty = fields.Float('Opening Stock QTY')
    opening_stock_regular_qty = fields.Float('Opening Stock Regular QTY')
    near_expiry_qty = fields.Float('Opening Stock QTY')
    receipt_en_route_qty = fields.Float('Opening Stock QTY')
    actual_sales_regular_qty = fields.Float('Opening Stock QTY')
    actual_sales_promo_qty = fields.Float('Opening Stock QTY')
    regular_sales_qty = fields.Float('Opening Stock QTY')
    promotion_sales_qty = fields.Float('Opening Stock QTY')
    to_order_qty = fields.Float('To Order')
    line_data_type = fields.Selection([('Actual', 'Actual'), ('Estimated', 'Estimated')], string="Line Data type")
    vendor_product_delay = fields.Integer(string="Vendor Product Delay")
    actual_to_order_qty = fields.Float(string="Actual To Order Qty")
    is_set_manually_to_order = fields.Boolean()

