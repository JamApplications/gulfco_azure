import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
from collections import defaultdict
import logging
import time

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    landed_cost_ids = fields.One2many('stock.landed.cost', 'picking_id', string='Landed Costs')
    enable_costing = fields.Boolean(string="Enable Costing", compute="_compute_enable_costing")

    def button_validate(self):
        _logger.info("GULFCO_STOCK_COSTING_CONTROL")
        res = super(StockPicking, self).button_validate()
        t0 = time.perf_counter()
        for picking in self:
            warehouse = picking.picking_type_id.warehouse_id
            warehouse_stock_location = False
            picking_location_dest_id = picking.location_dest_id
            if warehouse:
                warehouse_stock_location = warehouse.lot_stock_id
            if picking.state == 'done':
                po_line_move_ids = picking.move_ids.filtered(lambda s:s.purchase_line_id and s.purchase_line_id.exercise_price > 0.0)
                _logger.info("GULFCO_STOCK_COSTING_CONTROL po_line_move_ids: %s" % (po_line_move_ids))
                if po_line_move_ids and not picking.purchase_id.enable_costing:
                    # exice_move_ids = po_line_move_ids.filtered(lambda s:s.purchase_line_id.exercise_price > 0.0)
                    _logger.info(
                        "GULFCO_STOCK_COSTING_CONTROL po_line_move_ids: %s" % (po_line_move_ids))
                    _logger.info(
                        "GULFCO_STOCK_COSTING_CONTROL picking.purchase_id.enable_costing: %s" % (picking.purchase_id.enable_costing))
                    picking.create_exice_journal_entery(po_line_move_ids)
            if picking.enable_costing:
                continue

            if picking.picking_type_id.code == "incoming":
                purchase_order = picking.purchase_id
                enable_costing = purchase_order.enable_costing if purchase_order else False
                if enable_costing:
                    _logger.info("GULFCO_STOCK_COSTING_CONTROL inside incoming")
                    
                    # Use SQL to efficiently group quantities per lot/product/location/package
                    # This replaces the Python loop with a single SQL query
                    self.env.cr.execute("""
                        SELECT 
                            lot_id,
                            product_id,
                            %s as location_dest_id,
                            result_package_id,
                            SUM(quantity) as total_qty,
                            COUNT(*) as line_count
                        FROM stock_move_line
                        WHERE picking_id = %s 
                            AND lot_id IS NOT NULL 
                            AND quantity > 0
                        GROUP BY lot_id, product_id, result_package_id
                    """, (picking.location_dest_id.id, picking.id))
                    
                    lot_quantities_data = self.env.cr.fetchall()
                    no_lines = sum(row[5] for row in lot_quantities_data)  # Total line count
                    
                    _logger.info(
                        "GULFCO_STOCK_COSTING_CONTROL processed %s lines" % no_lines)

                    # Bulk update quants using SQL
                    for lot_id, product_id, location_dest_id, result_package_id, total_qty, _ in lot_quantities_data:
                        _logger.info(
                            "GULFCO_STOCK_COSTING_CONTROL processing lot %s with qty %s" % (lot_id, total_qty))
                        
                        if result_package_id:
                            # Update quants with package
                            self.env.cr.execute("""
                                SELECT sq.id
                                FROM stock_quant sq
                                WHERE sq.lot_id = %s 
                                    AND sq.product_id = %s 
                                    AND sq.location_id IN (
                                        SELECT id FROM stock_location 
                                        WHERE parent_path LIKE (
                                            SELECT parent_path || '%%' 
                                            FROM stock_location 
                                            WHERE id = %s
                                        )
                                    )
                                    AND sq.package_id = %s
                            """, (lot_id, product_id, location_dest_id, result_package_id))
                            quants_to_update = self.env.cr.fetchall()
                            quants = self.env['stock.quant'].browse([q[0] for q in quants_to_update])
                            quants.write({'not_landed_quantity': total_qty})
                            
                            _logger.info(
                                "GULFCO_STOCK_COSTING_CONTROL updated %s quants for package %s" % 
                                (self.env.cr.rowcount, result_package_id))
                        else:
                            # Update quants without package                    
                            self.env.cr.execute("""
                                SELECT sq.id
                                FROM stock_quant sq
                                WHERE sq.lot_id = %s 
                                    AND sq.product_id = %s 
                                    AND sq.location_id IN (
                                        SELECT id FROM stock_location 
                                        WHERE parent_path LIKE (
                                            SELECT parent_path || '%%' 
                                            FROM stock_location 
                                            WHERE id = %s
                                        )
                                    )
                                    AND (package_id IS NULL OR package_id = 0)
                            """, (lot_id, product_id, location_dest_id))
                            quants_to_update = self.env.cr.fetchall()
                            quants = self.env['stock.quant'].browse([q[0] for q in quants_to_update])
                            quants.write({'not_landed_quantity': total_qty})
                            if warehouse and location_dest_id == warehouse_stock_location.id:
                                for quant in quants:
                                    reserved_qty = quant.reserved_quantity + total_qty
                                    quant_qty = quant.quantity - total_qty
                                    quant.reserved_quantity = reserved_qty
                                    quant.quantity = quant_qty
                            
                            _logger.info(
                                "GULFCO_STOCK_COSTING_CONTROL updated %s quants without package" % 
                                self.env.cr.rowcount)

            else:
                purchase_order = picking.purchase_id
                if (
                    not purchase_order
                    and picking.group_id
                    and picking.group_id.stock_move_ids
                    and picking.group_id.stock_move_ids.purchase_line_id
                ):
                    purchase_order = (
                        picking.group_id.stock_move_ids.purchase_line_id.order_id[0]
                    )

                enable_costing = (
                    purchase_order.enable_costing if purchase_order else False
                )

                if picking.picking_type_id.code == "internal":
                    grn = self.env['stock.picking'].sudo().search([
                        ('group_id', '=', picking.group_id.id),
                        ('picking_type_id.code', '=', 'incoming'),
                        ('state', '=', 'done'),
                    ], limit=1)

                    if grn:
                        purchase_order = grn.purchase_id
                        enable_costing = purchase_order.enable_costing if purchase_order else False

                    if picking.enable_costing and picking.location_dest_id:
                        warehouse_id = self.env['stock.warehouse'].sudo().search(
                            [('lot_stock_id', '=', picking.location_dest_id.id)], limit=1)
                        if warehouse_id:
                            self.env.cr.execute("""
                                SELECT sq.id, sml.quantity
                                FROM stock_quant sq
                                JOIN stock_move_line sml ON sq.lot_id = sml.lot_id
                                WHERE sq.location_id IN (
                                    SELECT id FROM stock_location 
                                    WHERE parent_path LIKE (
                                        SELECT parent_path || '%%' 
                                        FROM stock_location 
                                        WHERE id = %s
                                    )
                                )
                                AND sml.picking_id = %s
                            """, (picking.location_dest_id.id, picking.id))
                        
                            quant_mapping = dict(self.env.cr.fetchall())
                            for quant, qty in quant_mapping.items(): 
                                quant_id = self.env['stock.quant'].browse(quant)
                                quant_id.write({
                                    'not_landed_quantity': qty
                                })
                                if warehouse and picking.location_dest_id.id == warehouse_stock_location.id:
                                    for quant in quant_id:
                                        reserved_qty = quant.reserved_quantity + qty
                                        quant_qty = quant.quantity - qty
                                        quant.reserved_quantity = reserved_qty
                                        quant.quantity = quant_qty
                                
                                _logger.info(
                                    "GULFCO_STOCK_COSTING_CONTROL internal transfer updated %s quants" % 
                                    self.env.cr.rowcount)

                if picking.picking_type_id.code != "incoming" and enable_costing:
                    valid_landed_cost = any(lc.state == 'done' for lc in picking.landed_cost_ids)
                        
                    if not valid_landed_cost:
                        self.env.cr.execute("""
                            SELECT sq.id, sml.quantity
                            FROM stock_quant sq
                            JOIN stock_move_line sml ON sq.lot_id = sml.lot_id
                                AND sq.product_id = sml.product_id
                            WHERE sq.location_id IN (
                                SELECT id FROM stock_location 
                                WHERE parent_path LIKE (
                                    SELECT parent_path || '%%' 
                                    FROM stock_location 
                                    WHERE id = %s
                                )
                            )
                            AND sml.picking_id = %s
                            AND sml.lot_id IS NOT NULL
                            AND sml.quantity > 0
                        """, (picking.location_dest_id.id, picking.id))
                        
                        quant_mapping = dict(self.env.cr.fetchall())
                        for quant, qty in quant_mapping.items():                            
                        # if quant_mapping:
                            quant_id = self.env['stock.quant'].browse(quant)
                            quant_id.write({
                                'not_landed_quantity': qty
                            })
                            if warehouse and picking.location_dest_id.id == warehouse_stock_location.id:
                                for quant in quant_id:
                                    reserved_qty = quant.reserved_quantity + qty
                                    quant_qty = quant.quantity - qty
                                    quant.reserved_quantity = reserved_qty
                                    quant.quantity = quant_qty
                            _logger.info(
                                "GULFCO_STOCK_COSTING_CONTROL updated %s quants for non-incoming transfer" % 
                                len(quant_mapping))
        elapsed = time.perf_counter() - t0
        # One clean line in the server log
        _logger.info(
            "gulfco_stock_costing_control PERF button_validate: %.3fs on %d record(s) ids=%s",
            elapsed, len(self), self.ids
        )
        return res

    def create_exice_journal_entery(self,exice_move_ids):
        if not self.company_id.excise_journal_id:
            raise UserError(_('Please configure a Excise Journal from accounting setting'))
        if not self.company_id.excise_debit_account_id:
            raise UserError(_('Please configure a Excise Debit Account from accounting setting'))
        if not self.company_id.excise_credit_account_id:
            raise UserError(_('Please configure a Excise Credit Account from accounting setting'))
        # amount = sum(exice_move_ids.mapped('purchase_line_id').mapped('excise_price_total'))
        amount = sum(
            move.purchase_line_id.exercise_price * move.quantity
            for move in exice_move_ids
            if move.purchase_line_id and move.purchase_line_id.exercise_price and move.quantity
        )
        po_order = exice_move_ids.mapped('purchase_line_id').mapped('order_id')
        move_id = self.env['account.move'].create({
                'journal_id': self.company_id.excise_journal_id.id,
                'date': self.scheduled_date,
                'ref': 'Jounral entries of excise for the  {}'.format(po_order.name),
                'line_ids': [
                    (0, 0, {
                        'name': 'Excise {}'.format(po_order.name),
                        'account_id': self.company_id.excise_debit_account_id.id,
                        'debit': amount,
                        'credit': 0,
                    }),
                    (0, 0, {
                        'name': 'Excise {}'.format(po_order.name),
                        'account_id': self.company_id.excise_credit_account_id.id,
                        'debit': 0,
                        'credit': amount,
                    }),
                ],
                'excise_stock_picking_id': self.id,
            })
        move_id.action_post()
        for exice_move_id in exice_move_ids:
            svl_vals = {
                'company_id': exice_move_id.picking_id.company_id.id,
                'product_id': exice_move_id.product_id.id,
                'description': "Excise Valuation of {}".format(exice_move_id.picking_id.display_name),
                'unit_cost': exice_move_id.purchase_line_id.exercise_price,
                # 'quantity': exice_move_id.quantity,
                'quantity': 0,
                'value': exice_move_id.purchase_line_id.exercise_price * exice_move_id.quantity,
                'account_move_id': move_id.id,
                'stock_move_id':  exice_move_id.id
            }
            self.env['stock.valuation.layer'].create(svl_vals)
        without_hold_exice_move_ids = exice_move_ids.filtered(lambda s: not s.purchase_line_id.order_id.enable_costing)
        without_hold_exice_move_ids.sudo().with_context(force_avco_update_after_lc=True,from_excise_valuation=True).product_price_update_before_done()
        self.sudo().write({'excise_move_id': move_id.id})


    # def _send_notification_to_accounting(self):
    #     accounting_admin_group = self.env.ref('account.group_account_manager', raise_if_not_found=False)

    #     if accounting_admin_group and accounting_admin_group.users:
    #         for user in accounting_admin_group.users:
    #             self.activity_schedule(
    #                 'mail.mail_activity_data_todo',
    #                 user_id=user.id,
    #                 summary="مراجعة التكاليف المضافة",
    #                 note="⚠️ تم استلام المنتجات بدون تكلفة مضافة مرتبطة. الكميات محجوزة حتى تأكيد التكاليف.",
    #             )

    def _compute_enable_costing(self):
        LandedCost = self.env['stock.landed.cost']
        for picking in self:
            purchase_order = picking.purchase_id
            enable_costing = False

            if purchase_order and purchase_order.enable_costing:
                has_valid_landed_cost = LandedCost.search_count([
                    ('picking_ids', 'in', [picking.id]),
                    ('state', '=', 'done')
                ]) > 0
                enable_costing = has_valid_landed_cost

            elif picking.picking_type_id.code == 'internal' and picking.group_id:
                grn = self.env['stock.picking'].sudo().search([
                    ('group_id', '=', picking.group_id.id),
                    ('picking_type_id.code', '=', 'incoming'),
                    ('state', '=', 'done')
                ], limit=1)

                if grn and grn.purchase_id and grn.purchase_id.enable_costing:
                    has_valid_landed_cost = LandedCost.search_count([
                        ('picking_ids', 'in', [grn.id]),
                        ('state', '=', 'done')
                    ]) > 0
                    enable_costing = has_valid_landed_cost

            picking.enable_costing = enable_costing
