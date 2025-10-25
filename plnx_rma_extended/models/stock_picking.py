# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command
from odoo.osv import expression
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)



class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _rec_names_search = ['sale_id', 'sale_id.invoice_ids.name']

    is_rma_in_type = fields.Boolean(compute="compute_picking_type", store=True)
    is_rma_out_type = fields.Boolean(compute="compute_picking_type", store=True)

    state = fields.Selection(selection_add=[('driver_assigned', 'Driver Assigned'),
                                            ('collation_done', 'Collation Done'),
                                            ('return_offload', 'Returned - Item Offload in Warehouse'),],
                             ondelete={'driver_assigned': 'cascade', 'collation_done': 'cascade'})

    @api.depends('state', 'picking_type_id', 'picking_type_id.name')
    def _compute_status_label(self):
        res = super(StockPicking, self)._compute_status_label()
        for picking in self:
            label = dict(self._fields['state'].selection).get(picking.state, picking.state)
            if picking.is_rma_in_type:
                if picking.state == 'assigned':
                    label = 'Ready for collation'
                elif picking.state == 'driver_assigned':
                    label = 'Driver Assigned'
                elif picking.state == 'collation_done':
                    label = 'Collation Done'
                elif picking.state == 'done':
                    label = 'Return to WH'
                elif picking.state == 'return_offload':
                    label = 'Returned - Item Offload in Warehouse'

                picking.status_label = label
        return res

    def action_assign_driver(self):
        for rec in self:
            if rec.picking_driver_id:
                rec.state = 'driver_assigned'
            else:
                raise UserError(_("Please assign Driver first!"))


    def action_collect(self):
        for rec in self:
            rec.state = 'collation_done'

    def action_item_offload(self):
        for rec in self:
            rec.state = 'return_offload'

    @api.depends('picking_type_id')
    def compute_picking_type(self):
        res = super(StockPicking, self).compute_picking_type()
        for record in self:
            is_rma_in_type = False
            is_rma_out_type = False
            if record.picking_type_id and record.picking_type_id.warehouse_id.rma_in_type_id == record.picking_type_id:
                is_rma_in_type = True
            if record.picking_type_id and record.picking_type_id.warehouse_id.rma_out_type_id == record.picking_type_id:
                is_rma_out_type = True
            record.is_rma_out_type = is_rma_out_type
            record.is_rma_in_type = is_rma_in_type
        return res



    def _action_done(self):
        super(StockPicking, self)._action_done()
        for picking in self:
            if picking.state == 'done':
                for rma in self.env['rma'].sudo().search([('reception_move_id.picking_id', '=', picking.id)]):
                    if rma.operation_id and rma.operation_id.operation_type in ['refund','replace']:
                        origin = rma.name
                        refund_vals = rma._prepare_refund_vals(origin)
                        refund_vals["invoice_line_ids"].extend(
                           rma._prepare_refund_line_vals()
                        )
                        refund = self.env["account.move"].sudo().create(refund_vals)
                        refund.action_post()
                        refund.with_user(self.env.uid).message_post_with_source(
                            "mail.message_origin_link",
                            render_values={"self": refund, "origin": rma},
                            subtype_id=self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note"),
                        )
                        for line in refund.invoice_line_ids:
                            line.rma_id.write(
                                {
                                    "refund_line_id": line.id,
                                    "refund_id": refund.id,
                                    "state": "refunded",
                                }
                            )
                    # rma.action_refund()

    def _check_for_quality_checks(self):
        quality_pickings = self.env['stock.picking']
        if 'post' not in self.env.context:
            for picking in self:
                product_to_check = picking.mapped('move_line_ids').filtered(lambda ml: ml.picked).mapped('product_id')
                if picking.mapped('check_ids').filtered(lambda qc: qc.quality_state == 'none' and (qc.product_id in product_to_check or qc.measure_on == 'operation')):
                    quality_pickings |= picking
        return quality_pickings

    # def button_validate(self):
    #     res = super().button_validate()
    #     for rec in self:
    #         if rec.state == 'done':
    #             rma_move_ids = rec.move_ids.filtered(lambda s: not s.purchase_line_id and s.rma_receiver_ids and s.product_id.exercise_price > 0.0)
    #             if rma_move_ids:
    #                 self.create_rma_exice_journal_entery(rma_move_ids)
    #     return res

    def create_rma_exice_journal_entery(self,rma_move_ids):
        if not self.company_id.excise_journal_id:
            raise UserError(_('Please configure a Excise Journal from accounting setting'))
        if not self.company_id.excise_debit_account_id:
            raise UserError(_('Please configure a Excise Debit Account from accounting setting'))
        if not self.company_id.excise_credit_account_id:
            raise UserError(_('Please configure a Excise Credit Account from accounting setting'))
        amount = 0.0
        for rma_move_id in rma_move_ids:
            amount += rma_move_id.quantity * rma_move_id.product_id.exercise_price
        # amount = sum(rma_move_ids.mapped('product_id').mapped('exercise_price'))
        rma_receiver_ids = rma_move_ids.mapped('rma_receiver_ids')
        move_id = self.env['account.move'].create({
                'journal_id': self.company_id.excise_journal_id.id,
                'date': self.scheduled_date,
                'ref': 'Jounral entries of excise for the  {}'.format(rma_receiver_ids[0].name),
                'line_ids': [
                    (0, 0, {
                        'name': 'Excise {}'.format(rma_receiver_ids[0].name),
                        'account_id': self.company_id.excise_debit_account_id.id,
                        'debit': amount,
                        'credit': 0,
                    }),
                    (0, 0, {
                        'name': 'Excise {}'.format(rma_receiver_ids[0].name),
                        'account_id': self.company_id.excise_credit_account_id.id,
                        'debit': 0,
                        'credit': amount,
                    }),
                ],
                'excise_stock_picking_id': self.id,
            })
        move_id.action_post()
        self.sudo().write({'excise_move_id': move_id.id})
        
        
    def _server_action_correct_receipt_linking_with_rma(self):
        """ - if one of move in done status: move when inv. receiving share same source document and trx type is return collection 
                -> system to check which move linked with RMA. if the move that linked with RMA is canceled system to swap linked to the second move that done and sys to call refund function on RMA.
            - if the moves in ready status: system to check which move is linked with RMA and to cancel the other moves.
            - if RMA has no linked receipt but there exist receipt with the same RMA in origin then link it with RMA.
         """
        # all_receipts = self.filtered(lambda p: p.trx_type == 'return_collection' and p.origin)
        all_receipts = self.filtered(lambda p: p.origin)
        # group receipts by origin
        receipts_by_origin = defaultdict(lambda: self.env['stock.picking'])
        for picking in all_receipts:
            rma_code = picking.origin.split(" ")[0]
            # receipts_by_origin[picking.origin] |= picking
            receipts_by_origin[rma_code] |= picking

        for origin, receipts in receipts_by_origin.items():

            # all pickings belonging to one RMA
            related_rma = receipts.move_ids.rma_receiver_ids
            if not related_rma:
                related_rma = self.env['rma'].search([('name', '=', origin)], limit=1)
            if not related_rma:
                _logger.info(f"\nRMA Not found: {origin}\n")
                continue
            
            # if related_rma.state == 'done':
            #     continue
            
            rma_linked_pickings = self.env['stock.picking']
            picking = related_rma.reception_move_id.picking_id
            while picking:
                if len(picking) == 1:
                    rma_linked_pickings |= picking
                    picking = picking._get_next_transfers()
                else:
                    for p in picking:
                        rma_linked_pickings |= p
                        picking = picking._get_next_transfers()
            
            done_rma_receipts = receipts.filtered(lambda r: r.state == 'done')
            
            if done_rma_receipts:
                done_moves = done_rma_receipts.move_ids
                # if RMA is not linked to the done receipt, re-link
                if not any(picking.state == 'done' for picking in rma_linked_pickings):
                    # unlink wrong receipts
                    # wrong_moves = receipts.mapped('move_ids').filtered(lambda m: related_rma in m.rma_receiver_ids)
                    wrong_moves = rma_linked_pickings.move_ids
                    wrong_moves.write({'rma_receiver_ids': [Command.unlink(related_rma.id)]})

                    # link done receipt to RMA                    
                    # for move in done_rma_receipts.move_ids:
                        # move.write({'rma_receiver_ids': [(4, related_rma.id)]})
                    done_moves.write({'rma_receiver_ids': [Command.link(related_rma.id)]})
                    related_rma.write({'reception_move_ids': done_moves.ids})
                    
                # call refund func if needed
                if related_rma.state not in ('refunded', 'received') or (not related_rma.refund_id and related_rma.can_be_refunded):
                    if not related_rma.can_be_refunded:
                        related_rma.can_be_refunded = True
                    
                    # Costs in RMA Refund to be same as Received cost
                    rma_line_cogs_map = {}
                    # for invoice in invoices:
                    for line in related_rma.line_ids:
                        product = line.product_id
                        svls = done_moves.stock_valuation_layer_ids.filtered(
                            lambda l: l.product_id == product
                        )
                        if svls:
                            rma_line_cogs_map[line] = svls[0].unit_cost # Unit cost
                        else:                    
                            rma_line_cogs_map[line] = 0  
                    related_rma.with_context(from_rma_server_action=True, rma_line_cogs_map=rma_line_cogs_map).action_refund()

            elif receipts and rma_linked_pickings:
                # no done receipts: keep only the linked one and cancel others
                other_receipts = receipts - rma_linked_pickings
                if other_receipts:
                    other_receipts.sudo().action_cancel()
                    
            elif receipts and not rma_linked_pickings:
                # link most forward state receipt with RMA and cancel others

                state_priority = {
                    'draft': 0,
                    'planned': 1,
                    'scheduled': 2,
                    'rescheduled': 3,
                    'waiting': 4,
                    'confirmed': 5,
                    'assigned': 6,   # Ready
                    'driver_assigned': 7,
                    'loaded_dispatched': 8,
                    'collation_done': 9,
                    'delivered_partial': 10,
                    'wh_del_return': 11,
                    'rescheduled_item_offload_in_warehouse': 12,
                    'return_offload': 13,
                    'returned': 14,
                    'wh_return': 15,
                    'delivered': 16,
                    'done': 17, # Highest
                    'cancel': -1,  # lowest
                }

                # pick the most forward receipt
                forward_receipt = max(receipts, key=lambda r: state_priority.get(r.state, -1))

                if forward_receipt and forward_receipt.state != 'cancel':
                    # link chosen receipt with RMA
                    forward_moves = forward_receipt.move_ids
                    forward_moves.write({'rma_receiver_ids': [Command.link(related_rma.id)]})
                    related_rma.write({
                        # 'reception_move_id': forward_moves[0].id,
                        'reception_move_ids': forward_moves.ids,
                    })

                    # cancel all others
                    other_receipts = receipts - forward_receipt
                    if other_receipts:
                        other_receipts.sudo().action_cancel()      
                        
    def _server_action_update_picking_effective_date_and_generate_svl(self):
        # Enhanced Server Action Code for stock.picking model
        processed_pickings = []
        error_pickings = []

        for picking in self:
            try:
                if picking.state not in ['done', 'loaded_dispatched', 'delivered']:
                    continue
                    
                picking_updated = False
                svl_created = 0
                
                # Issue 1: Fix effective date (date_done)
                if not picking.date_done:
                    reference_date = False
                    
                    # Priority 1: Use sale order confirmation date
                    # if picking.sale_id and picking.sale_id.date_order:
                    #     reference_date = picking.sale_id.date_order                    
                            
                    # Priority 1: Use move date if available
                    if picking.move_ids_without_package:
                        move_dates = picking.move_ids_without_package.filtered('date').mapped('date')
                        if move_dates:
                            reference_date = max(move_dates)
                            
                    # Priority 2: Use invoice date from related sale order
                    elif picking.sale_id and picking.sale_id.invoice_ids:
                        latest_invoice = picking.sale_id.invoice_ids.filtered(
                            lambda inv: inv.state in ['posted', 'paid']
                        ).sorted('date', reverse=True)[:1]
                        if latest_invoice:
                            reference_date = latest_invoice.date
                    
                    # Fallback: Use current date
                    if not reference_date:
                        reference_date = picking.scheduled_date or fields.Datetime.now()
                    
                    # Update the date_done
                    picking.write({'date_done': reference_date})
                    picking_updated = True
                    
                # Issue 2: Generate missing SVL entries
                effective_date = picking.date_done
                
                rma_id = False
                if picking.origin and "RMA" in picking.origin.upper():
                    rma_id = self.env['rma'].search([('reception_move_id.picking_id', '=', picking.id)])
                    if not rma_id:
                        rma_id = picking.move_ids.rma_receiver_ids or picking.move_ids.rma_ids
                        
                _get_valued_types = picking.move_ids._get_valued_types()        
                
                # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
                valued_moves = {valued_type: self.env['stock.move'] for valued_type in _get_valued_types}  
                # all_moves = picking.move_ids_without_package.filtered(lambda m: m.state == 'done') 
                all_moves = picking.move_ids.filtered(lambda m: m.state == 'done') 
                
                for move in all_moves:
                    if move.stock_valuation_layer_ids:
                            continue
                    if float_is_zero(move.quantity, precision_rounding=move.product_uom.rounding):
                        continue
                    if not any(move.move_line_ids.mapped('picked')):
                        continue
                    for valued_type in _get_valued_types:
                        if getattr(move, '_is_%s' % valued_type)():
                            valued_moves[valued_type] |= move    
                
                stock_valuation_layers = self.env['stock.valuation.layer'].sudo()            
                # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
                # quantity = move.product_uom_qty
                for valued_type in _get_valued_types:
                    todo_valued_moves = valued_moves[valued_type]
                    if todo_valued_moves:
                        todo_valued_moves._sanity_check_for_valuation()
                        # # Use native Odoo methods to get proper SVL vals
                        # if move._is_out():
                        #     # Outgoing move (delivery, consumption, etc.)
                        #     svl_vals_to_create = move._get_out_svl_vals()
                        # elif move._is_in():
                        #     # Incoming move (receipt, production, etc.)
                        #     svl_vals_to_create = move._get_in_svl_vals()
                        stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)() 
                        svl_created += len(stock_valuation_layers)
                
                # -------------------------
                # 3. Sync SVL values with COGS
                # -------------------------
                for move in all_moves:  
                    is_out_move = move._is_out()                  
                    for svl in move.stock_valuation_layer_ids:
                        svl_date = effective_date

                        # Case A: Delivery -> match with SO invoice COGS
                        if is_out_move and picking.sale_id:
                            cogs_line = picking.sale_id.invoice_ids.filtered(
                                lambda inv: inv.state == 'posted'
                            ).line_ids.filtered(lambda l: l.product_id == move.product_id and l.account_id.internal_group == 'expense' and l.display_type == 'cogs')
                            if cogs_line:
                                # Aggregate debit - credit (COGS value)
                                cogs_value = sum(cogs_line.mapped("debit")) - sum(cogs_line.mapped("credit"))
                                if not float_is_zero(cogs_value, precision_rounding=move.company_id.currency_id.rounding):
                                    new_unit_cost = cogs_value / (cogs_line.quantity or 1.0)
                                    value = new_unit_cost * svl.quantity
                                if not float_is_zero((svl.unit_cost - new_unit_cost), precision_rounding=move.company_id.currency_id.rounding):
                                    svl.write({
                                        "unit_cost": new_unit_cost,
                                        "value": value,
                                        "remaining_value": value,
                                        # "create_date": svl_date,
                                        # "write_date": svl_date,
                                    })

                        # Case B: RMA Receipt -> match with Refund journal item COGS
                        elif rma_id:
                            refund_id = rma_id.refund_id
                            refund_lines = refund_id.line_ids.filtered(lambda l: l.product_id == move.product_id and l.account_id.internal_group == 'expense' and l.display_type == 'cogs')
                            if refund_lines:
                                rma_value = sum(refund_lines.mapped("debit")) - sum(refund_lines.mapped("credit"))
                                if not float_is_zero(rma_value, precision_rounding=move.company_id.currency_id.rounding):
                                    new_unit_cost = rma_value / (refund_lines.product_uom_qty or 1.0)
                                if not float_is_zero((svl.unit_cost - new_unit_cost), precision_rounding=move.company_id.currency_id.rounding):
                                    value = new_unit_cost * svl.quantity
                                    svl.write({
                                        "unit_cost": new_unit_cost,
                                        "value": rma_value,
                                        "remaining_value": rma_value,
                                        # "create_date": svl_date,
                                        # "write_date": svl_date,
                                    })
                        
                        # regenerate accounting entries
                        svl.with_context(datafix_effective_date=effective_date)._validate_accounting_entries()
                        svl._validate_analytic_accounting_entries()
                
                # Record successful processing
                processed_pickings.append({
                    'name': picking.name,
                    'date_updated': picking_updated,
                    'svl_created': svl_created
                })
                
            except Exception as picking_error:
                error_pickings.append({
                    'name': picking.name,
                    'error': str(picking_error)
                })
                _logger.error(f"Error processing picking {picking.name}: {str(picking_error)}")

        # Prepare result message
        success_count = len(processed_pickings)
        error_count = len(error_pickings)

        result_message = f"""
        Processing completed:
        - Successfully processed: {success_count} picking(s)
        - Errors encountered: {error_count} picking(s)

        Successful pickings:
        """

        for pick in processed_pickings:
            result_message += f"- {pick['name']}: Date updated: {pick['date_updated']}, SVL created: {pick['svl_created']}\n"

        if error_pickings:
            result_message += f"\nFailed pickings:\n"
            for pick in error_pickings:
                result_message += f"- {pick['name']}: {pick['error']}\n"

        # Show result
        _logger.info(result_message)      



