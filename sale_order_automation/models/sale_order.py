from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from odoo.addons.account.models.account_move import BYPASS_LOCK_CHECK

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_automate_sale_workflow(self):
        """
        Server action to automate complete sale order workflow
        """
        for order in self:
            try:
                # Step 1: Confirm Sale Order
                if order.state in ['draft', 'sent']:
                    order.action_confirm()
                    _logger.info(f"Sale Order {order.name} confirmed successfully")

                # Step 2: Validate Delivery Orders (Pickings)
                if order.state == 'sale':
                    self._validate_delivery_orders(order)

                # Step 3: Create Invoice
                if order.state == 'sale' and not order.invoice_ids:
                    invoice = self._create_invoices(order)
                    # invoice_vals = order._prepare_invoice()
                    # invoice = self.env['account.move'].create(invoice_vals)
                    # invoice.write({'invoice_date':fields.Date.today()})
                    #
                    # # Link invoice lines
                    # for line in order.order_line:
                    #     if line.qty_to_invoice > 0:
                    #         invoice_line_vals = line._prepare_invoice_line(
                    #             qty=line.product_uom_qty,
                    #             move=invoice
                    #         )
                    #         self.env['account.move.line'].create(invoice_line_vals)

                    _logger.info(f"Invoice {invoice.name} created for Sale Order {order.name}")

                # Get the invoice (either just created or existing)
                invoice = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')[:1]

                if not invoice:
                    invoice = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')[:1]

                if invoice and invoice.state == 'draft':
                    # Step 4: Post Invoice
                    invoice.with_context(bypass_lock_check=BYPASS_LOCK_CHECK).action_post()
                    _logger.info(f"Invoice {invoice.name} posted successfully")

                if invoice and invoice.state == 'posted':
                    # Step 5: Create and Post Payment
                    payment = self._create_automatic_payment(invoice)

                    # sale_create_uid = order.create_uid.id
                    # sale_create_date_str = order.create_date.strftime('%Y-%m-%d %H:%M:%S.%f')

                    # ids_tuple = tuple(invoice.ids)
                    # if len(ids_tuple) == 1:
                    #     ids_tuple = f"({ids_tuple[0]})"  # single ID without trailing comma
                    # else:
                    #     ids_tuple = sids_tuple
                    #
                    # query = f"""
                    #        UPDATE account_move
                    #        SET create_uid = {sale_create_uid},
                    #            create_date = '{sale_create_date_str}'::timestamp
                    #        WHERE id IN {ids_tuple}
                    #    """
                    # self.env.cr.commit()
                    # invoice.write({'create_date':order.create_date,'create_uid':order.create_uid.id})
                    # self.env.cr.execute(query)
                    #
                    # # Update payment create_uid & create_date
                    # if payment:
                    #
                    #     ids_tuple = tuple(payment.ids)
                    #     if len(ids_tuple) == 1:
                    #         ids_tuple = f"({ids_tuple[0]})"  # single ID without trailing comma
                    #     else:
                    #         ids_tuple = str(ids_tuple)
                    #
                    #     query = f"""
                    #                              UPDATE account_payment
                    #                              SET create_uid = {sale_create_uid},
                    #                                  create_date = '{sale_create_date_str}'::timestamp
                    #                              WHERE id IN {ids_tuple}
                    #                          """
                    #     self.env.cr.execute(query)


                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Sale order workflow completed successfully!'),
                        'type': 'success',
                    }
                }

            except Exception as e:
                _logger.error(f"Error in sale order automation for {order.name}: {str(e)}")
                # raise UserError(_(
                #     "Error in automating sale order workflow for %s: %s"
                # ) % (order.name, str(e)))

    def _validate_delivery_orders(self, order):
        """
        Validate all delivery orders (pickings) for the sales order
        """
        _logger.info(f"Starting delivery validation for Sale Order {order.name}")

        pickings = order.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])

        if not pickings:
            _logger.warning(f"No delivery orders found for Sale Order {order.name}")
            return

        for picking in pickings:
            _logger.info(f"Processing picking {picking.name} with state: {picking.state}")

            # Check if picking is ready to be validated
            if picking.state not in ['assigned', 'partially_available']:
                # Try to check availability first
                picking.action_assign()
                _logger.info(f"Assigned availability for picking {picking.name}")

            # Validate the picking if it's ready
            if picking.state in ['assigned', 'partially_available']:
                package_rec = self.env['stock.quant.package'].create({})
                # Set done quantities equal to demand quantities
                for move in picking.move_ids_without_package:
                    for move_line in move.move_line_ids:
                        if move_line.quantity > 0:
                            move_line.result_package_id = package_rec.id
                            move_line.qty_done = move_line.quantity
                            _logger.info(f"Set qty_done: {move_line.qty_done} for product {move_line.product_id.name}")

                # Validate the picking
                try:
                    picking.button_validate()
                    _logger.info(f"Successfully validated picking {picking.name}")

                    # Handle backorder confirmation if wizard appears
                    if picking.state != 'done':
                        # Check if there's a backorder wizard
                        ctx = self.env.context.copy()
                        ctx.update({
                            'button_validate_picking_ids': [picking.id],
                            'skip_backorder': True,
                        })

                        # Try to process the backorder automatically
                        backorder_wizard = self.env['stock.backorder.confirmation'].search([
                            ('pick_ids', 'in', picking.ids)
                        ], limit=1)

                        if backorder_wizard:
                            backorder_wizard.process()
                            _logger.info(f"Processed backorder for picking {picking.name}")

                except Exception as e:
                    _logger.error(f"Error validating picking {picking.name}: {str(e)}")
                    # Try alternative validation method
                    try:
                        picking.with_context(skip_backorder=True).button_validate()
                        _logger.info(f"Successfully validated picking {picking.name} with alternative method")
                    except Exception as alt_e:
                        _logger.error(f"Alternative validation also failed for {picking.name}: {str(alt_e)}")
                        # raise UserError(_(
                        #     "Cannot validate picking %s. Error: %s"
                        # ) % (picking.name, str(alt_e)))

            elif picking.state == 'waiting':
                _logger.warning(f"Picking {picking.name} is waiting for another operation")
                # Try to force availability check
                picking.action_assign()
                if picking.state == 'assigned':
                    # Retry validation after assignment
                    for move in picking.move_ids_without_package:
                        for move_line in move.move_line_ids:
                            if move_line.product_uom_qty > 0:
                                move_line.qty_done = move_line.product_uom_qty
                    picking.button_validate()
                    _logger.info(f"Successfully validated waiting picking {picking.name}")

            else:
                _logger.warning(f"Cannot validate picking {picking.name}. Current state: {picking.state}")
                # Don't raise error, just log warning and continue

        _logger.info(f"Completed delivery validation for Sale Order {order.name}")

    def _create_automatic_payment(self, invoice):
        """
        Automatically register and post payment for the invoice using Register Payment wizard
        """
        if invoice.state != 'posted':
            raise UserError(_("Invoice must be posted before registering payment."))

        # Ensure the invoice is open
        if invoice.payment_state in ['paid', 'in_payment']:
            _logger.info(f"Invoice {invoice.name} is already paid or in payment.")
            return

        # Get default journal
        journal = self.env['account.journal'].search([
            ('type', 'in', ['bank']),
            ('company_id', '=', invoice.company_id.id)
        ], limit=1)

        if not journal:
            raise UserError(_("No suitable journal (bank or cash) found for payments."))

        if invoice.partner_id and invoice.partner_id.customer_type == 'cash':
            journal = self.env['account.journal'].search([
                ('type', 'in', ['cash']),
                ('company_id', '=', invoice.company_id.id)
            ], limit=1)

        if invoice.partner_id and invoice.partner_id.customer_type == 'credit':
            return False


        # Build context as if opening the wizard from UI
        ctx = {
            'active_model': 'account.move',
            'active_ids': invoice.ids,
            'default_journal_id': journal.id,
        }

        # Create the payment wizard
        register_payment = self.env['account.payment.register'].with_context(ctx).create({
            'amount': invoice.amount_residual,
            'payment_date': fields.Date.today(),
            'journal_id': journal.id,
            'payment_method_line_id': journal.inbound_payment_method_line_ids[
                0].id if journal.inbound_payment_method_line_ids else False,
        })

        # Execute the payment registration (creates and posts payment)
        register_payment.action_create_payments()

        if invoice.matched_payment_ids:
            payment = invoice.matched_payment_ids[0]
            # Post payment
            payment.with_context(bypass_lock_check=BYPASS_LOCK_CHECK).action_post()

            if invoice.invoice_outstanding_credits_debits_widget and 'content' in invoice.invoice_outstanding_credits_debits_widget and invoice.invoice_outstanding_credits_debits_widget.get(
                    'content'):
                for x in invoice.invoice_outstanding_credits_debits_widget.get('content'):
                    line = self.env['account.move.line'].browse(x['id'])
                    invoice.js_assign_outstanding_line(line.id)

        # # Reconcile payment with invoice
        # invoice_receivable_line = invoice.line_ids.filtered(
        #     lambda l: l.account_id.account_type == 'asset_receivable'
        # )
        # payment_receivable_line = payment.line_ids.filtered(
        #     lambda l: l.account_id.account_type == 'asset_receivable'
        # )
        #
        # if invoice_receivable_line and payment_receivable_line:
        #     (invoice_receivable_line + payment_receivable_line).reconcile()
        #
        # _logger.info(f"Payment {payment.name} created and posted for invoice {invoice.name}")

        return payment