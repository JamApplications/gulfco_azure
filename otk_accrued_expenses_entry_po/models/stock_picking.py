from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _description = 'Stock Picking'


    services_ids = fields.One2many('services.lines', 'picking_id')
    is_service_only_grn = fields.Boolean(
        string='Service Only GRN',
        compute='_compute_is_service_only_grn',
    )
    
    grn_state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string="GRN State", store=True)

    def _compute_is_service_only_grn(self):
        for picking in self:
            picking.is_service_only_grn = (
                picking.picking_type_id.code == 'incoming'
                and bool(picking.services_ids)
                and not picking.move_ids
            )
    
    def _get_all_related_backorder_pickings(self, picking):
        """Return all backorders and original pickings in the backorder chain."""
        all_pickings = self.env['stock.picking']

        def collect(pick):
            nonlocal all_pickings
            if pick in all_pickings:
                return
            all_pickings |= pick
            if pick.backorder_id:
                collect(pick.backorder_id)
            if pick.backorder_ids:
                for child in pick.backorder_ids:
                    collect(child)

        collect(picking)
        return all_pickings
    
    def _generate_service_valuation_lines(self):
        """
        Generate account move lines for services in a separate journal entry.
        """
        self.ensure_one()
        service_lines = {}
        partner_id = self.partner_id
        service_lines_records = self.services_ids
        for service in service_lines_records:
            debit_value = self.company_id.currency_id.round(service.price_unit * service.product_qty)
            credit_value = debit_value
            credit_account_id = service.po_line_id.order_id.accrued_account_id.id
            debit_account_id = service.product_id.property_account_expense_id.id or service.product_id.categ_id.property_account_expense_categ_id.id
            if not debit_account_id:
                raise UserError(_("Missing Debit account configuration for services."))

            if not credit_account_id:
                raise UserError(_("Missing Credit account configuration for services."))
            qty_for_entry = service.product_qty

            # Adjust the quantity if there are existing journal items for the same purchase line
            if service.po_line_id:
                po_line_id = service.po_line_id
                qty_for_entry = service.product_qty
                entry_value = self.company_id.currency_id.round(qty_for_entry * po_line_id.price_unit)
                debit_value = entry_value
                credit_value = entry_value

            service_lines[f'service_debit_{service.id}'] = {
                'name': service.product_id.display_name,
                'product_id': service.product_id.id,
                'quantity': qty_for_entry,
                'product_uom_id': service.product_id.uom_id.id,
                'ref': f"{self.name} - Accrual",
                'partner_id': partner_id.id,
                'balance': debit_value,
                'account_id': debit_account_id,
                'service_po_line_id': service.po_line_id.id if service.po_line_id else False,
                'analytic_distribution': service.analytic_distribution if hasattr(service, 'analytic_distribution') else False,
            }
            service_lines[f'service_credit_{service.id}'] = {
                'name': service.product_id.display_name,
                'product_id': service.product_id.id,
                'quantity': qty_for_entry,
                'product_uom_id': service.product_id.uom_id.id,
                'ref': f"{self.name} - Accrual",
                'partner_id': partner_id.id,
                'balance': -credit_value,
                'account_id': credit_account_id,
                'service_po_line_id': service.po_line_id.id if service.po_line_id else False,
                'analytic_distribution': service.analytic_distribution if hasattr(service, 'analytic_distribution') else False,
            }
            service.po_line_id.qty_received = qty_for_entry
        return service_lines
    
    def button_validate_grn(self):
        """
        Create a separate journal entry for service-related lines.
        """
        self.ensure_one()
        service_lines = self._generate_service_valuation_lines()
        if not service_lines:
            return  # No services to process
        # Get the journal from the product category (similar to stock valuation for consumables)
        first_service = self.services_ids[0]
        if not first_service:
            return  # No service lines found

        journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
                ('type', '=', 'general'),
                ('is_accrued_journal','=',True)
            ], limit=1) or first_service.product_id.categ_id.property_stock_journal

        if not journal_id:
            raise UserError(_("Please configure a Stock Journal in the product category."))
        move_vals = {
            'journal_id': journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': f"{self.name} - {first_service.product_id.name}" if first_service else self.name,
            'partner_id': self.partner_id.id, 
            'line_ids': [(0, 0, line) for line in service_lines.values()],
        }
        # Create the separate journal entry
        service_move = self.env['account.move'].create(move_vals)
        service_move.action_post()  # Post the move automatically
        self.grn_state = "done"
        for service in self.services_ids:
            done_lines = self.env['services.lines'].search([
                ('po_line_id', '=', service.po_line_id.id),
                '|',
                ('picking_id.grn_state', '=', 'done'),
                ('picking_id.state', '=', 'done')
            ])
            if done_lines:
                service.po_line_id.qty_received = sum(done_lines.mapped('product_qty'))
    
    def button_validate(self):
        # for service in self.services_ids:
        #     service.po_line_id.qty_received += service.product_qty
            # service.po_line_id.qty_service_received += service.product_qty

        # Native validation
        res = super().button_validate()

        if not self.services_ids:
            return res

        # All pickings after validation
        pickings_after = self.env['stock.picking'].search([('group_id', 'in', self.mapped('group_id').ids)])
        
        for original_picking in self:
            new_or_existing_pickings = pickings_after - original_picking

            for target_picking in new_or_existing_pickings.filtered(lambda p: p.origin == original_picking.origin and p.state not in ['done', 'cancel', 'returned']):
                for orig_service in original_picking.services_ids:
                    po_line = orig_service.po_line_id
                    if not po_line or not po_line.product_qty:
                        continue

                    # Total received = sum of all service lines in validated pickings of this PO line
                    all_backorder_chain = self._get_all_related_backorder_pickings(original_picking)
                    validated_pickings = all_backorder_chain.filtered(lambda p: p.state == 'done')
                    total_received_qty = sum(self.env['services.lines'].search([
                        ('po_line_id', '=', po_line.id),
                        ('picking_id', 'in', validated_pickings.ids),
                        ('picking_id.state', '=', 'done'),
                    ]).mapped('product_qty'))

                    # If this is a direct backorder picking, adjust remaining qty
                    if target_picking.backorder_id:
                        final_qty = orig_service.po_line_id.product_qty - total_received_qty
                    else:
                        final_qty = total_received_qty

                    # Skip if qty is zero
                    if not final_qty:
                        continue

                    # Check if service line already exists for this po_line
                    existing_service = target_picking.services_ids.filtered(lambda l: l.po_line_id.id == po_line.id and l.product_id.id == orig_service.product_id.id)
                    if existing_service:
                        # Update existing service line
                        existing_service.write({
                            'product_qty': total_received_qty,
                            'product_uom_qty': total_received_qty,
                        })
                        existing_service.po_line_id.qty_received = total_received_qty
                    else:
                        # Create new service line
                        self.env['services.lines'].create({
                            'product_id': orig_service.product_id.id,
                            'product_uom_qty': final_qty,
                            'product_qty': final_qty,
                            'price_unit': orig_service.price_unit,
                            'po_line_id': po_line.id,
                            'picking_id': target_picking.id,
                            'analytic_distribution': orig_service.analytic_distribution,
                        })

        # Generate Accounting accrual entries for services/consu
        for service in self.services_ids:
            # service.po_line_id.qty_received += service.product_qty
            done_lines = self.env['services.lines'].search([
                ('po_line_id', '=', service.po_line_id.id),
                '|',
                ('picking_id.grn_state', '=', 'done'),
                ('picking_id.state', '=', 'done')
            ])
            if done_lines:
                service.po_line_id.qty_received = sum(done_lines.mapped('product_qty'))
            try:
                service.po_line_id.order_id.action_generate_accrued_entry()
            except:
                pass
        return res
