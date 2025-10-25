from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    _description = 'Purchase Orders'

    accrued_account_id = fields.Many2one('account.account', string="Accrued Account",required=False,
                                         related='partner_id.accrued_account_id', readonly=False)

    service_journal_entry_count = fields.Integer(
        compute='_compute_service_journal_entry_count',
        string='Service Journal Entry Count'
    )

    can_generate_accrued_entry = fields.Boolean(
        compute='_compute_can_generate_accrued_entry',
        string="Can Generate Accrued Entry"
    )
    
    service_grn_count = fields.Integer(string="Service GRNs", compute="_compute_service_grn_count")
    
    def _compute_service_grn_count(self):
        StockPicking = self.env['stock.picking']
        for po in self:
            service_grn_count = 0
            # if po.po_type == 'non_tradable' and all(line.product_id.type == 'service' and not line.product_id.is_fixed_asset_product for line in po.order_line):
            if po.po_type == 'non_tradable':
                pickings = StockPicking.search([
                    ('origin', '=', po.name),
                    ('picking_type_id.code', '=', 'incoming'),
                    ('move_ids', '=', False),
                    ('services_ids', '!=', False)
                ])
                service_grn_count = len(pickings)
            po.service_grn_count = service_grn_count

    def action_view_service_grns(self):
        self.ensure_one()
        pickings = self.env['stock.picking'].search([
            ('origin', '=', self.name),
            ('picking_type_id.code', '=', 'incoming'),
            ('move_ids', '=', False),
            ('services_ids', '!=', False)
        ])
        
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(pickings) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        else:
            action['domain'] = [('id', 'in', pickings.ids)]
            action['views'] = [(self.env.ref('stock.vpicktree').id, 'list'), (self.env.ref('stock.view_picking_form').id, 'form')]
        
        action['context'] = {'default_purchase_id': self.id}
        action['name'] = 'Service GRNs'
        return action

    @api.depends("order_line.product_id", "order_line.product_id.type")
    def _compute_has_service_consumable_products(self):
        for order in self:
            order.has_service_products = any(
                line.product_id.type in ["service", "consu"]
                and not line.product_id.is_storable
                and not line.product_id.is_fixed_asset_product
                for line in order.order_line
            )

    @api.depends('order_line.qty_received', 'order_line.qty_service_received', 'order_line.product_id')
    def _compute_can_generate_accrued_entry(self):
        for order in self:
            if (
                order.po_type != 'non_tradable'
                or not order.has_service_products
            ):
                order.can_generate_accrued_entry = False
                continue

            all_ok = False
            for line in order.order_line:
                if line.product_id.type != 'service' or line.product_id.is_fixed_asset_product:
                    continue
                if line.qty_received == 0:
                    all_ok = True  # Not received at all
                    break
                if line.qty_service_received < line.qty_received:
                    all_ok = True  # Some received, not accrued
                    break                
                if line.qty_received < line.product_qty and line.qty_service_received < line.product_qty:
                    all_ok = True  # Some received and accrued, some remaining
                    break
            order.can_generate_accrued_entry = all_ok

    @api.depends('order_line')
    def _compute_service_journal_entry_count(self):
        for order in self:
            po_lines = order.order_line.ids
            aml = self.env['account.move.line'].search([
                ('service_po_line_id', 'in', po_lines)
            ])
            moves = aml.mapped('move_id')
            order.service_journal_entry_count = len(moves)
            

    def action_view_service_journal_entries(self):
        self.ensure_one()
        po_lines = self.order_line.ids
        aml = self.env['account.move.line'].search([
            ('service_po_line_id', 'in', po_lines)
        ])
        move_ids = aml.mapped('move_id').ids

        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('id', 'in', move_ids)]
        action['context'] = {'create': False}
        return action

    def button_approve(self, force=False):
        result = super(PurchaseOrder, self).button_approve(force=force)
        self._create_picking()
        self._create_services_picking()
        return result
    
    def action_generate_backorder_grn(self):
        self.with_context(service_backorder=True)._create_services_picking()
    

    def action_generate_accrued_entry(self):
        # Generate accrued entries for purchase orders usign _create_service_account_move method
        # but only for Received quantities
        for order in self:
            # has_consumable = order.order_line.filtered(lambda l: l.product_id.type == 'consu')
            # has_picking = order.picking_ids.filtered(lambda p: p.state not in ['cancel'])

            if (
                order.po_type == "non_tradable"
                and order.has_service_products
            ):
                for line in order.order_line.filtered(
                    lambda l: l.product_id.type in ["service", "consu"]
                    and not l.product_id.is_fixed_asset_product
                    and not l.product_id.is_storable
                ):
                    if line.qty_received == 0:
                        raise UserError(_("Cannot generate accrued entry. One or more service lines are NOT received."))
                    elif line.qty_service_received == line.product_qty:
                        raise UserError(_("Accrued entry has been already generated for all quantities")) 
                    elif line.qty_received <= line.qty_service_received:
                        raise UserError(_("Cannot generate accrued entry. Some service lines have not been fully received."))
                    elif line.qty_received > line.product_qty:
                        raise UserError(_("Cannot generate accrued entry. Received quantity cannot exceed ordered quantity."))
                # Non-tradable and Service product PO, No consumables, create a accrued journal entry manually
                order._create_service_account_move()
                order._create_consumable_account_move()

    def _prepare_service_picking_values(self, line, picking):
        return {
            "product_id": line.product_id.id,
            "po_line_id": line.id,
            "product_qty": line.product_qty - line.qty_received,
            "product_uom_qty": line.product_qty - line.qty_received,
            "price_unit": line.price_unit,
            "price_subtotal": line.price_subtotal,
            "picking_id": picking.id,
            "analytic_distribution": (
                line.analytic_distribution
                if hasattr(line, "analytic_distribution")
                else False
            ),
        }
        
    def _prepare_service_picking(self):
        # if not self.group_id:
        #     self.group_id = self.group_id.create(self._prepare_group_vals())
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s", self.partner_id.name))
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
            'state': 'assigned',
            'grn_state': 'draft',
        }

    def _create_services_picking(self):
        for order in self.filtered(lambda o: o.po_type == "non_tradable" and o.has_service_products):
            ServiceLines = self.env['services.lines']
            picking_ids = order.picking_ids
            if self._context.get('service_backorder') and picking_ids and picking_ids.filtered(lambda p: p.state not in ['done', 'cancel']):
                for line in order.order_line:
                    if line.product_id.type == 'service':
                        vals = self._prepare_service_picking_values(line, picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])[0])
                        ServiceLines.create(vals)
            elif not self._context.get('service_backorder') and picking_ids:
                for line in order.order_line:
                    if line.product_id.type == 'service':
                        vals = self._prepare_service_picking_values(line, picking_ids[0])
                        ServiceLines.create(vals)
                        # line.qty_service_received = line.product_qty
            else:
                StockPicking = self.env['stock.picking']
                if not order.state in ('purchase', 'done'):
                    raise UserError(_("Sorry, GRN can be generated only for confirmed service PO!"))
                # if any(product.type == 'consu' for product in order.order_line.product_id):
                #     return
                order = order.with_company(order.company_id)
                res = order._prepare_service_picking()
                picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                
                for line in order.order_line:
                    if line.product_id.type == 'service':
                        vals = self._prepare_service_picking_values(line, picking)
                        ServiceLines.create(vals)
                        
                picking.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': picking, 'origin': order},
                    subtype_xmlid='mail.mt_note',
                )
                return True

    # def button_confirm(self):
    #     res = super(PurchaseOrder, self).button_confirm()

    #     for order in self:
    #         has_picking = order.picking_ids.filtered(lambda p: p.state not in ['cancel'])
    #         has_service = order.order_line.filtered(lambda l: l.product_id.type == 'service')
    #         has_consumable = order.order_line.filtered(lambda l: l.product_id.type == 'consu')

    #         if (
    #             has_service
    #             and not has_picking
    #             and not has_consumable
    #             and order.po_type == "non_tradable"
    #             and order.has_service_products
    #         ):
    #             # No picking, and no consumables, create a journal entry manually
    #             order._create_service_account_move()

    #     return res

    def _create_service_account_move(self):
        """
        Create journal entries for service purchases that do not trigger pickings.
        """
        for order in self:
            if order.po_type != "non_tradable" or not order.has_service_products:
                continue

            service_lines = {}
            qty_service_received = {}
            for line in order.order_line.filtered(lambda l: l.product_id.type == 'service'):
                # debit_value = line.price_subtotal
                # credit_value = debit_value

                debit_account_id = line.product_id.property_account_expense_id.id or \
                                   line.product_id.categ_id.property_account_expense_categ_id.id
                credit_account_id = line.order_id.accrued_account_id.id

                if not debit_account_id:
                    raise UserError(_("Please configure an expense account for services."))

                if not credit_account_id:
                    raise UserError(_("Please configure an accrued account for purchases."))

                qty_for_entry = line.qty_received - line.qty_service_received
                # qty_service_received[line.id] = line.qty_service_received + qty_for_entry
                entry_value = self.company_id.currency_id.round(qty_for_entry * line.price_unit)

                service_lines[f'service_debit_{line.id}'] = {
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'quantity': qty_for_entry,
                    'product_uom_id': line.product_id.uom_id.id,
                    'ref': order.name,
                    'partner_id': order.partner_id.id,
                    'balance': entry_value,
                    'account_id': debit_account_id,
                    'service_po_line_id': line.id,
                    'analytic_distribution': line.analytic_distribution if hasattr(line, 'analytic_distribution') else False,
                }
                service_lines[f'service_credit_{line.id}'] = {
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'quantity': qty_for_entry,
                    'product_uom_id': line.product_id.uom_id.id,
                    'ref': order.name,
                    'partner_id': order.partner_id.id,
                    'balance': -entry_value,
                    'account_id': credit_account_id,
                    'service_po_line_id': line.id,
                    'analytic_distribution': line.analytic_distribution if hasattr(line, 'analytic_distribution') else False,
                }

            journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
                ('type', '=', 'general'),
                ('is_accrued_journal','=',True)
            ], limit=1) or order.order_line.product_id.categ_id.property_stock_journal
            journal_id = journal_id[0] if journal_id else False
            if not journal_id:
                raise UserError(_("Please configure a Stock Journal in the product category."))

            move_vals = {
                'journal_id': journal_id.id,
                'date': fields.Date.context_today(self),
                'ref': order.name,
                'partner_id': order.partner_id.id,
                'line_ids': [(0, 0, line) for line in service_lines.values()],
            }

            service_move = self.env['account.move'].create(move_vals)
            service_move.action_post()

            # for line in order.order_line:
            #     if line.product_id.type == 'service':
            #         # Update the service line with the received quantity
            #         line.qty_service_received = qty_service_received.get(line.id, 0.0)
            #         # # Update the line with the account move reference
            #         # line.account_move_id = service_move.id

    def _create_consumable_account_move(self):
        """
        Generate account move lines for non-storable consumables in a separate journal entry.
        """
        for order in self:
            credit_account_id = order.accrued_account_id.id
            if not credit_account_id:
                raise UserError(_("Missing Credit account configuration for services."))
            consumable_lines = {}
            for line in order.order_line.filtered(lambda l: l.product_id.type == 'consu' and not l.product_id.is_storable):
                debit_account_id = line.product_id.property_account_expense_id.id or line.product_id.categ_id.property_account_expense_categ_id.id
                if not debit_account_id:
                    raise UserError(_("Missing Debit account configuration for services."))

                qty_for_entry = line.qty_received - line.qty_service_received
                # qty_service_received[line.id] = line.qty_service_received + qty_for_entry
                entry_value = self.company_id.currency_id.round(qty_for_entry * line.price_unit)
                                
                consumable_lines[f'consumable_debit_{line.id}'] = {
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'quantity': qty_for_entry,
                    'product_uom_id': line.product_id.uom_id.id,
                    'ref': order.name,
                    'partner_id': order.partner_id.id,
                    'balance': entry_value,
                    'account_id': debit_account_id,
                    'service_po_line_id': line.id,
                    'analytic_distribution': line.analytic_distribution if hasattr(line, 'analytic_distribution') else False,
                }
                consumable_lines[f'consumable_credit_{line.id}'] = {
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'quantity': qty_for_entry,
                    'product_uom_id': line.product_id.uom_id.id,
                    'ref': order.name,
                    'partner_id': order.partner_id.id,
                    'balance': -entry_value,
                    'account_id': credit_account_id,
                    'service_po_line_id': line.id,
                    'analytic_distribution': line.analytic_distribution if hasattr(line, 'analytic_distribution') else False,
                }

                journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(self.env.company),
                    ('type', '=', 'general'),
                    ('is_accrued_journal','=',True)
                ], limit=1) or line.product_id.categ_id.property_stock_journal
                journal_id = journal_id[0] if journal_id else False
                if not journal_id:
                    raise UserError(_("Please configure a Stock Journal in the product category."))

                move_vals = {
                    'journal_id': journal_id.id,
                    'date': fields.Date.context_today(self),
                    'ref': order.name,
                    'partner_id': order.partner_id.id,
                    'line_ids': [(0, 0, line) for line in consumable_lines.values()],
                }

                consumable_move = self.env['account.move'].create(move_vals)
                consumable_move.action_post()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    _description = 'Purchase Order Lines'

    account_id = fields.Many2one(comodel_name="account.account", string="Expense Account",
                                 compute='_compute_account_id',store=True)

    qty_service_received = fields.Float(
        string='Quantity Service Received', copy=False, default=0.0, compute='_compute_qty_service_received',
        help="This is the quantity of service product that has been received and journal entry has been created for.")

    def _compute_qty_service_received(self):
        for rec in self:
            qty_service_received = 0
            if (
                rec.order_id.po_type == "non_tradable"
                and rec.product_id.type in ["consu", "service"]
                and not rec.product_id.is_storable
                and not rec.product_id.is_fixed_asset_product
            ):
                aml = self.env["account.move.line"].search(
                    [
                        ("service_po_line_id", "=", rec.id),
                        ("product_id", "=", rec.product_id.id),
                        ("debit", ">", 0),
                    ]
                )
                if aml:
                    qty_service_received = abs(sum(aml.mapped("quantity")))
            rec.qty_service_received = qty_service_received

    @api.depends('product_id','partner_id')
    def _compute_account_id(self):
        for line in self:
            if line.product_id:
                fiscal_position = line.order_id.fiscal_position_id
                accounts = line.with_company(line.company_id).product_id.product_tmpl_id.get_product_accounts(
                    fiscal_pos=fiscal_position)
                # Assign expense account based on product settings
                if (
                    line.order_id
                    and line.order_id.po_type == 'non_tradable'
                    and line.product_id
                    and line.product_id.type in ["service", "consu"]
                    and not line.product_id.is_storable
                    and not line.product_id.is_fixed_asset_product
                ):
                    line.account_id = (
                        line.product_id.property_account_expense_id.id
                        or line.product_id.categ_id.property_account_expense_categ_id.id
                        or accounts["expense"]
                        or line.account_id
                    )
                else:
                    _logger.info(" Non service Product ")
                    line.account_id = accounts['expense'] or line.account_id

            # If no product, attempt to get an account based on the vendor
            elif line.partner_id:
                account_id = self.env['account.account']._get_most_frequent_account_for_partner(
                    company_id=line.company_id.id,
                    partner_id=line.partner_id.id,
                    move_type='in_invoice',
                )
                if account_id:
                    line.account_id = account_id

        # Fallback mechanism for unassigned accounts
        for line in self:
            if not line.account_id and line.display_type not in ('line_section', 'line_note'):
                previous_two_accounts = line.order_id.order_line.filtered(
                    lambda l: l.account_id and l.display_type == line.display_type
                )[-2:].account_id

                if len(previous_two_accounts) == 1 and len(line.order_id.order_line) > 2:
                    line.account_id = previous_two_accounts
                else:
                    line.account_id = False

    @api.onchange('qty_received')
    def _onchange_qty_received_validate(self):
        for line in self:
            order = line.order_id
            if (
                order.po_type == 'non_tradable'
                and order.has_service_products
                and line.product_id.type == 'service'
                and not line.product_id.is_fixed_asset_product
                and line.qty_service_received
                and line.qty_received < line.qty_service_received
            ):
                raise UserError(_(
                    "You cannot reduce 'Received Quantity' (%s) below the already accrued quantity (%s) "
                    "for service product '%s'."
                ) % (line.qty_received, line.qty_service_received, line.product_id.display_name))
