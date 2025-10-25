from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """
        self.ensure_one()

        # Get all stock moves in the same picking or operation
        related_moves = self.picking_id.move_ids if self.picking_id else self.group_id.stock_move_ids

        # Check if any move has a storable product
        has_storable_product = any(move.product_id.is_storable for move in related_moves)

        purchase_order_id = self.purchase_line_id.order_id if self.purchase_line_id else None

        # Process only if the related purchase order is non-tradable and has service products
        if (
            purchase_order_id
            and purchase_order_id.po_type == "non_tradable"
            and purchase_order_id.has_service_products
            and not self.product_id.is_fixed_asset_product
            and not self.product_id.is_storable
            and not has_storable_product
        ):
            valuation_partner_id = self._get_partner_id_for_valuation_lines()

            self._create_service_account_move(valuation_partner_id, svl_id, description)
            self._create_non_storable_consumable_move(valuation_partner_id, description)

            return []

        return super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, svl_id, description):
        """
        Generate the account.move.line values to track stock valuation separately from service and non-storable consumable entries.
        """
        self.ensure_one()

        debit_value = self.company_id.currency_id.round(cost)
        credit_value = debit_value

        valuation_partner_id = self._get_partner_id_for_valuation_lines()

        # Stock valuation move lines
        stock_lines = [(0, 0, line_vals) for line_vals in self._generate_valuation_lines_data(
            valuation_partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id,
            description
        ).values()]

        # Ensure _create_service_account_move runs only once per picking
        if not hasattr(self.env, '_processed_pickings'):
            self.env._processed_pickings = set()  # Store processed pickings

        if self.picking_id.id not in self.env._processed_pickings:
            self.env._processed_pickings.add(self.picking_id.id)
            self._create_service_account_move(valuation_partner_id, svl_id, description)
            self._create_non_storable_consumable_move(valuation_partner_id, description)

        return stock_lines

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        # This method returns a dictionary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()
        if not (
            self.product_id.type == "consu"
            and not self.product_id.is_storable
            and not self.product_id.is_fixed_asset_product
            and self.purchase_line_id
            and self.purchase_line_id.order_id
            and self.purchase_line_id.order_id.po_type == "non_tradable"
        ):
            # Continue with Odoo Native Flow
            return super()._generate_valuation_lines_data(
                partner_id=partner_id,
                qty=qty,
                debit_value=debit_value,
                credit_value=credit_value,
                debit_account_id=debit_account_id,
                credit_account_id=credit_account_id,
                svl_id=svl_id,
                description=description,
            )

        line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
        }

        svl = self.env['stock.valuation.layer'].browse(svl_id)
        if svl.account_move_line_id.analytic_distribution:
            line_vals['analytic_distribution'] = svl.account_move_line_id.analytic_distribution

        product_storable = self.product_id.is_storable
        product_type = self.product_id.type
        product_expense_acc = self.product_id.property_account_expense_id
        product_categ_expense_acc = self.product_id.categ_id.property_account_expense_categ_id
        dest_location_parent = self.location_dest_id.location_id.name
        dest_location_type = self.location_dest_id.usage
        is_internal = self.picking_type_id.code
        accrued_account_id = self.purchase_line_id.order_id.accrued_account_id.id

        if dest_location_parent == 'Virtual Locations' and dest_location_type == 'inventory' and product_type == 'consu' and product_storable == True and is_internal == 'internal':
            _logger.info("Meets All Conditions")
            rslt = {
                'credit_line_vals': {
                    **line_vals,
                    'balance': -credit_value,
                    'account_id': credit_account_id,
                },
                'debit_line_vals': {
                    **line_vals,
                    'balance': debit_value,
                    'account_id': product_expense_acc.id if product_expense_acc else product_categ_expense_acc.id,
                },
            }

        elif product_type == 'consu' and self.purchase_line_id:
            rslt = {
                'credit_line_vals': {
                    **line_vals,
                    'balance': -credit_value,
                    'account_id': accrued_account_id,
                },
                'debit_line_vals': {
                    **line_vals,
                    'balance': debit_value,
                    'account_id': debit_account_id,
                },
            }

        else:
            _logger.info("Dose Not Meet Conditions")
            rslt = {
                'credit_line_vals': {
                    **line_vals,
                    'balance': -credit_value,
                    'account_id': credit_account_id,
                },
                'debit_line_vals': {
                    **line_vals,
                    'balance': debit_value,
                    'account_id': debit_account_id,
                },
            }

        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.env.context.get('price_diff_account')
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))

            rslt['price_diff_line_vals'] = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'balance': -diff_amount,
                'ref': description,
                'partner_id': partner_id,
                'account_id': price_diff_account.id,
            }
        return rslt

    def _create_service_account_move(self, partner_id, svl_id, description):
        """
        Create a separate journal entry for service-related lines.
        """
        self.ensure_one()
        service_lines = self._generate_service_valuation_lines(partner_id, svl_id, description)
        if not service_lines:
            return  # No services to process
        # Get the journal from the product category (similar to stock valuation for consumables)
        first_service = self.env['services.lines'].search([('picking_id', '=', self.picking_id.id)], limit=1)
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
            'ref': f"{self.picking_id.name} - {first_service.product_id.name}" if first_service else self.picking_id.name,
            'partner_id': partner_id,  # Use partner from delivery
            'line_ids': [(0, 0, line) for line in service_lines.values()],
        }
        # Create the separate journal entry
        service_move = self.env['account.move'].create(move_vals)
        service_move.action_post()  # Post the move automatically

        # for service in service_lines.values():
        #     if service.get('product_id'):
        #         product_id = self.env['product.product'].browse(service.get('product_id'))
        #     if product_id.type == 'service':
        #         po_line = service.get('po_line_id')
        #         if not po_line:
        #             continue
        #         po_line = self.env['purchase.order.line'].browse(po_line)

        #         # Update the service po line with the received quantity
        #         po_line.qty_service_received += service['quantity']
        #         # # Update the line with the account move reference
        #         # line.account_move_id = service_move.id

    def _generate_service_valuation_lines(self, partner_id, svl_id, description):
        """
        Generate account move lines for services in a separate journal entry.
        """
        self.ensure_one()
        service_lines = {}
        qty_service_received = {}
        service_lines_records = self.env['services.lines'].search([('picking_id', '=', self.picking_id.id)])
        for service in service_lines_records:
            debit_value = self.company_id.currency_id.round(service.price_unit * service.product_qty)
            credit_value = debit_value
            credit_account_id = self.purchase_line_id.order_id.accrued_account_id.id
            debit_account_id = service.product_id.property_account_expense_id.id or service.product_id.categ_id.property_account_expense_categ_id.id
            if not debit_account_id:
                raise UserError(_("Missing Debit account configuration for services."))

            if not credit_account_id:
                raise UserError(_("Missing Credit account configuration for services."))
            qty_for_entry = service.product_qty

            # Adjust the quantity if there are existing journal items for the same purchase line
            if service.po_line_id:
                po_line_id = service.po_line_id

                # qty_for_entry = po_line_id.qty_received - po_line_id.qty_service_received
                if po_line_id.qty_received > 0.0:
                    qty_for_entry = po_line_id.qty_received - po_line_id.qty_service_received
                else:
                    qty_for_entry = service.product_qty
                qty_service_received[po_line_id.id] = po_line_id.qty_service_received + qty_for_entry
                entry_value = self.company_id.currency_id.round(qty_for_entry * po_line_id.price_unit)
                debit_value = entry_value
                credit_value = entry_value

            service_lines[f'service_debit_{service.id}'] = {
                'name': service.product_id.display_name,
                'product_id': service.product_id.id,
                'quantity': qty_for_entry,
                'product_uom_id': service.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
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
                'ref': description,
                'partner_id': partner_id,
                'balance': -credit_value,
                'account_id': credit_account_id,
                'service_po_line_id': service.po_line_id.id if service.po_line_id else False,
                'analytic_distribution': service.analytic_distribution if hasattr(service, 'analytic_distribution') else False,
            }

        return service_lines

    def _create_non_storable_consumable_move(self, partner_id, description, svl_id=None):

        """
        Create a separate journal entry for consumables that are not storable and are not fixed assets.
        """

        self.ensure_one()

        consumable_lines = self._generate_consumable_valuation_lines(partner_id, description)

        if not consumable_lines:
            return  # No non-storable consumables to process

        first_consumable = self.env['stock.move'].search([
            ('picking_id', '=', self.picking_id.id),
            ('product_id.type', '=', 'consu'),
            ('product_id.is_fixed_asset_product', '=', False),
            ('product_id.is_storable', '=', False)
        ], limit=1)

        if not first_consumable:
            return  # No matching consumable lines found
        
        journal_id = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'general'),
            ('is_accrued_journal','=',True)
        ], limit=1) or first_consumable.product_id.categ_id.property_stock_journal

        if not journal_id:
            raise UserError(_("Please configure a Stock Journal in the product category."))

        move_vals = {
            "journal_id": journal_id.id,
            "date": fields.Date.context_today(self),
            "ref": (
                f"{self.picking_id.name} - {first_consumable.product_id.name}"
                if first_consumable
                else self.picking_id.name
            ),
            "partner_id": partner_id,  # Use partner from delivery
            "line_ids": [(0, 0, line) for line in consumable_lines.values()],
        }

        consumable_move = self.env['account.move'].create(move_vals)
        consumable_move.action_post()  # Post the move automatically

    def _generate_consumable_valuation_lines(self, partner_id, description, svl_id=None):
        """
        Generate account move lines for non-storable consumables in a separate journal entry.
        """
        if self.purchase_line_id:
            self.ensure_one()
            if self.purchase_line_id and self.purchase_line_id.order_id.po_type != 'non_tradable':
                return

            consumable_lines = {}
            consumables = self.env['stock.move'].search([
                ('picking_id', '=', self.picking_id.id),
                ('product_id.type', '=', 'consu'),
                ('product_id.is_fixed_asset_product', '=', False),
                ('product_id.is_storable', '=', False)
            ])

            for move in consumables:
                debit_value = self.company_id.currency_id.round(move.price_unit * move.quantity)
                credit_value = debit_value
                credit_account_id = self.purchase_line_id.order_id.accrued_account_id.id
                debit_account_id = move.product_id.property_account_expense_id.id or move.product_id.categ_id.property_account_expense_categ_id.id

                if not debit_account_id:
                    raise UserError(_("Missing Debit account configuration for services."))

                if not credit_account_id:
                    raise UserError(_("Missing Credit account configuration for services."))

                po_line = move.purchase_line_id or self.purchase_line_id

                consumable_lines[f'consumable_debit_{move.id}'] = {
                    'name': move.product_id.display_name,
                    'product_id': move.product_id.id,
                    'quantity': move.quantity,
                    'product_uom_id': move.product_id.uom_id.id,
                    'ref': description,
                    'partner_id': partner_id,
                    'balance': debit_value,
                    'account_id': debit_account_id,
                    'service_po_line_id': po_line.id,
                    'analytic_distribution': po_line.analytic_distribution if hasattr(po_line, 'analytic_distribution') else False,
                }

                consumable_lines[f'consumable_credit_{move.id}'] = {
                    'name': move.product_id.display_name,
                    'product_id': move.product_id.id,
                    'quantity': move.quantity,
                    'product_uom_id': move.product_id.uom_id.id,
                    'ref': description,
                    'partner_id': partner_id,
                    'balance': -credit_value,
                    'account_id': credit_account_id,
                    'service_po_line_id': po_line.id,
                    'analytic_distribution': po_line.analytic_distribution if hasattr(po_line, 'analytic_distribution') else False,
                }

            return consumable_lines
