from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from collections import defaultdict

class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    picking_id = fields.Many2one('stock.picking', string="Picking")
    summery_line_ids = fields.One2many(
        'stock.landed.cost.summery.line',
        'landed_cost_id',
        string='Landed Cost Summary Report Lines',
        compute="compute_summery_line_ids",
        store=True
    )

    @api.depends('picking_ids','picking_ids.move_ids','amount_total','valuation_adjustment_lines','valuation_adjustment_lines.additional_landed_cost')
    def compute_summery_line_ids(self):
        for cost in self:
            summary_lines = [(5, 0, 0)]
            for picking in cost.picking_ids:
                for move in picking.move_ids:
                    product = move.product_id
                    qty = move.product_uom_qty
                    po_line = move.purchase_line_id
                    unit_price = po_line.price_unit or 0.0
                    currency = po_line.currency_id or move.company_id.currency_id
                    # po_cost = po_line.price_subtotal
                    po_cost = unit_price * qty
                    po_cost_local = currency._convert(po_cost, cost.company_id.currency_id, cost.company_id,
                                                      fields.Date.today())

                    # excise_duty = po_line.excise_price_total
                    excise_duty = po_line.exercise_price * qty
                    # hdr_charges = excise_duty + cost.amount_total + po_cost_local
                    hdr_charges = sum(cost.valuation_adjustment_lines.filtered(lambda s:s.product_id == product and s.move_id == move).mapped('additional_landed_cost'))
                    # total_cost_aed = excise_duty + cost.amount_total + po_cost_local
                    total_cost_aed = excise_duty + hdr_charges + po_cost_local
                    if qty > 0:
                        landed_cost_per_unit = total_cost_aed / qty
                    else:
                        landed_cost_per_unit = 0.0
                    summary_lines.append((0, 0, {
                        'product_id': product.id,
                        'trx_qty': qty,
                        'unit_price': unit_price,
                        'currency_code': currency.name,
                        'po_cost': po_cost,
                        'po_cost_local': po_cost_local,
                        'unit_excise_cost':po_line.exercise_price,
                        'excise_duty': excise_duty,
                        'hdr_charges': hdr_charges,
                        'total_cost_aed':total_cost_aed,
                        'landed_cost_per_unit': landed_cost_per_unit,
                    }))
            cost.summery_line_ids = summary_lines



    def get_last_linked_picking(self, picking):
        """
        Get the last linked picking in the transfer chain.
        Args:
            picking: stock.picking record to start from
        Returns:
            stock.picking: The last picking in the chain
        """
        if not picking:
            return picking

        current_picking = picking

        while current_picking:
            # Get next transfers using the standard Odoo method
            next_pickings = current_picking._get_next_transfers()
            # Filter for done pickings only
            done_pickings = next_pickings.filtered(lambda p: p.state == 'done' and p.picking_type_code in ["incoming","internal"])
            if not done_pickings:
                break
            # Choose the latest one based on scheduled_date, with fallback to create_date
            current_picking = done_pickings.sorted(
                lambda p: p.scheduled_date or p.create_date,
                reverse=True
            )[0]
        return current_picking


    def button_validate(self):
        before_cost = {}
        adj_product_before_cost = {}
        for rec in self:
            for pick in rec.picking_ids:
                before_cost.update({pick.product_id.id: pick.product_id.standard_price})
        res = super().button_validate()
        seen_po = set()
        for rec in self:
            for picking in rec.picking_ids:
                # Create Excise Value Journal Entry
                if picking.purchase_id.id not in seen_po:
                    po_line_move_ids = picking.move_ids.filtered(lambda s:s.purchase_line_id)
                    if po_line_move_ids:
                        exice_move_ids = po_line_move_ids.filtered(lambda s:s.purchase_line_id.exercise_price > 0.0)
                        if exice_move_ids and picking.purchase_id.enable_costing:
                            seen_po.add(picking.purchase_id.id)
                            picking.create_exice_journal_entery(exice_move_ids)

                last_picking = self.get_last_linked_picking(picking)
                # last_picking = self.get_last_linked_picking(picking)
                
                # Single DB call
                stock_quants = self.env['stock.quant'].sudo().search([
                    ('lot_id', 'in', last_picking.move_line_ids.lot_id.ids),
                    ('location_id', 'child_of', last_picking.location_dest_id.id),
                    ('not_landed_quantity', '>', 0),
                ])

                # Group by lot_id for direct access
                quants_by_lot = {}
                for quant in stock_quants:
                    if quant.lot_id.id not in quants_by_lot:
                        quants_by_lot[quant.lot_id.id] = quant
                    else:
                        quants_by_lot[quant.lot_id.id] |= quant
    
                for line in last_picking.move_line_ids:
                    if line.lot_id:
                        stock_quants = quants_by_lot.get(line.lot_id.id, self.env['stock.quant'])
                        if line.result_package_id:
                            stock_quants = stock_quants.filtered(lambda q: q.package_id == line.result_package_id)
                        # if stock_quants:
                        #     stock_quants.write({'not_landed_quantity': 0})                        
                        for quant in stock_quants:
                            not_landed = quant.not_landed_quantity - line.quantity
                            quant.not_landed_quantity = max(0, not_landed)
                            quant.quantity = quant.quantity + line.quantity
                            quant.reserved_quantity = quant.reserved_quantity - line.quantity

            # Additional landed cost adjustment in cost
            for line in rec.valuation_adjustment_lines.filtered(lambda l: l.move_id):
                product = line.move_id.product_id
                if product and product.id in before_cost:
                    adj_product_before_cost[product.id] = before_cost[product.id]

            # # Now run AVCO move costing on incoming pickings' moves
            # avco_moves = rec.picking_ids.move_ids.filtered(
            #     lambda m: m.picking_id.picking_type_id.code == "incoming"
            # )
            # if avco_moves:
            #     avco_moves.with_context(force_avco_update_after_lc=True).product_price_update_before_done(before_cost=adj_product_before_cost)

            # Process deferred SVLs now
            deferred_svls = self.env['stock.valuation.layer'].sudo().search([
                ('stock_move_id.picking_id', 'in', rec.picking_ids.ids),
                ('is_deferred_costing', '=', True)
            ])

            if deferred_svls:
                # Unset flag
                deferred_svls.write({"is_deferred_costing": False})

                # Run processing now
                deferred_svls._validate_accounting_entries()
                deferred_svls._validate_analytic_accounting_entries()
                deferred_svls._check_company()
            
            # Now run AVCO move costing on incoming pickings' moves
            avco_moves = rec.picking_ids.move_ids.filtered(
                lambda m: m.picking_id.picking_type_id.code == "incoming"
            )
            if avco_moves:
                avco_moves.with_context(force_avco_update_after_lc=True).product_price_update_before_done(before_cost=adj_product_before_cost)
            
                
            if deferred_svls:    
                # For every in move, run the vacuum for the linked product.
                company = (
                    deferred_svls.mapped("company_id")
                    and deferred_svls.mapped("company_id")[0]
                    or self.env.company
                )
                products_to_vacuum = deferred_svls.stock_move_id.filtered(
                    lambda m: m.picking_id.picking_type_id.code == "incoming"
                ).mapped("product_id")
                # products_to_vacuum._run_fifo_vacuum(company)
        return res

    def get_valuation_lines(self):
        self.ensure_one()
        lines = []

        for move in self._get_targeted_move_ids():
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.cost_method not in ('fifo', 'average') or move.state == 'cancel' or not move.quantity:
                continue
            qty = move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id)
            former_cost = sum(move._get_stock_valuation_layer_ids().mapped('value'))
            if move.purchase_line_id and move.purchase_line_id.is_excise and move.purchase_line_id.order_id and move.purchase_line_id.order_id.enable_costing:
                # former_cost = move.purchase_line_id.price_subtotal
                excise_price = move.purchase_line_id.exercise_price
                excise_price_total = move.purchase_line_id.excise_price_total
            else:
                # former_cost = sum(move._get_stock_valuation_layer_ids().mapped('value'))
                excise_price = 0.0
                excise_price_total = 0.0
            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': qty,
                'former_cost': former_cost,
                'weight': move.product_id.weight * qty,
                'volume': move.product_id.volume * qty,
                'excise_price':excise_price,
                'excise_price_total':excise_price * qty
            }
            lines.append(vals)

        if not lines:
            target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
            raise UserError(_("You cannot apply landed costs on the chosen %s(s). Landed costs can only be applied for products with FIFO or average costing method.", target_model_descriptions[self.target_model]))
        return lines

    @api.onchange('picking_ids')
    def onchange_picking_ids(self):
        # get all stock landed cost containing same picking
        if self.picking_ids:
            domain = [('picking_ids', 'in', self.picking_ids.ids)]
            landed_costs = self.env['stock.landed.cost'].search(domain)
            if landed_costs:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _('There are already landed costs applied to the selected picking(s). Please review them before proceeding.'),
                    }
                }

class StockLandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name or ''
        self.split_method = self.product_id.product_tmpl_id.split_method_landed_cost or self.split_method or 'equal'
        self.price_unit = self.product_id.standard_price or 0.0
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        # change account expense instead of stock input
        # self.account_id = accounts_data['stock_input']
        self.account_id = accounts_data['expense']


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    excise_price = fields.Monetary('Excise Price')
    excise_price_total = fields.Monetary('Excise Price Total')

    @api.depends('former_cost', 'additional_landed_cost','excise_price_total')
    def _compute_final_cost(self):
        for line in self:
            line.final_cost = line.former_cost + line.additional_landed_cost + line.excise_price_total
