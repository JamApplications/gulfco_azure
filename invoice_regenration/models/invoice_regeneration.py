from odoo import models, api, _
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)


class InvoiceRegenerationService(models.AbstractModel):
    _name = 'invoice.regeneration.service'
    _description = 'Invoice Regeneration Service'

    def regenerate_invoices(self, sale_orders):
        """
        Main method to regenerate invoices by adding missing product lines
        """
        processed_invoices = []
        errors = []

        for sale_order in sale_orders:
            try:
                result = self._process_sale_order(sale_order)
                processed_invoices.extend(result.get('processed', []))
                errors.extend(result.get('errors', []))
            except Exception as e:
                _logger.error(f"Error processing sale order {sale_order.name}: {str(e)}")
                errors.append(f"Sale Order {sale_order.name}: {str(e)}")

        return self._show_results(processed_invoices, errors)

    def _process_sale_order(self, sale_order):
        """
        Process a single sale order and its related invoices
        """
        processed_invoices = []
        errors = []

        # Get all customer invoices related to this sale order
        invoices = sale_order.invoice_ids.filtered(
            lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel'
        )

        if not invoices:
            errors.append(f"Sale Order {sale_order.name}: No invoices found")
            return {'processed': processed_invoices, 'errors': errors}

        for invoice in invoices:
            try:
                if self._process_invoice(sale_order, invoice):
                    processed_invoices.append(invoice.name)
            except Exception as e:
                errors.append(f"Invoice {invoice.name}: {str(e)}")

        return {'processed': processed_invoices, 'errors': errors}

    def _process_invoice(self, sale_order, invoice):
        """
        Process a single invoice
        """
        # Step 1: Set invoice to draft if needed
        if not self._set_invoice_to_draft(invoice):
            return False

        # Step 2: Compare products and find missing lines
        missing_lines = self._compare_and_find_missing_lines(sale_order, invoice)

        if not missing_lines:
            # If no missing lines and invoice was already posted, no need to process
            if invoice.state == 'posted':
                return False
        else:
            # Step 3: Add missing lines to invoice
            self._add_missing_lines_to_invoice(invoice, missing_lines)

        # # Step 4: Post the invoice
        invoice._onchange_quick_edit_line_ids()
        if invoice.state == 'draft':
            invoice.action_post()

        if invoice.matched_payment_ids:
            payment = invoice.matched_payment_ids[0]

            payment.action_draft()

            payment.write({'amount': invoice.amount_total})

            payment.action_post()

            if invoice.invoice_outstanding_credits_debits_widget and 'content' in invoice.invoice_outstanding_credits_debits_widget and invoice.invoice_outstanding_credits_debits_widget.get(
                    'content'):
                for x in invoice.invoice_outstanding_credits_debits_widget.get('content'):
                    line = self.env['account.move.line'].browse(x['id'])
                    invoice.js_assign_outstanding_line(line.id)


        # return self._post_invoice(invoice)

    def _set_invoice_to_draft(self, invoice):
        """
        Set invoice to draft state
        """
        if invoice.state == 'draft':
            return True

        try:
            invoice.button_draft()
            return True
        except Exception as e:
            _logger.error(f"Cannot set invoice {invoice.name} to draft: {str(e)}")
            raise UserError(f"Cannot set invoice {invoice.name} to draft: {str(e)}")

    def _compare_and_find_missing_lines(self, sale_order, invoice):
        """
        Compare sale order lines with invoice lines and return missing lines
        """
        missing_lines = []

        # Get all deliverable products from sale order lines
        so_products = self._get_sale_order_products(sale_order)

        # Get all products from invoice lines
        inv_products = self._get_invoice_products(invoice)

        # Find missing products/quantities
        for key, so_data in so_products.items():
            invoiced_qty = inv_products.get(key, 0)
            missing_qty = so_data['qty_to_invoice'] - invoiced_qty

            if missing_qty > 0:
                missing_lines.append(self._prepare_missing_line_data(so_data, missing_qty))

        return missing_lines

    def _get_sale_order_products(self, sale_order):
        """
        Get products from sale order lines that need to be invoiced
        """
        so_products = {}

        for line in sale_order.order_line:
            line._compute_qty_to_invoice()
            if (line.product_id and
                    line.qty_to_invoice > 0 and
                    not line.display_type):

                # Create a unique key for the product line
                key = self._create_product_key(line)

                if key in so_products:
                    so_products[key]['qty_to_invoice'] += line.qty_to_invoice
                    so_products[key]['lines'].append(line)
                else:
                    line.write({'product_uom':line.product_id.product_tmpl_id.uom_id.id})
                    so_products[key] = {
                        'qty_to_invoice': line.qty_to_invoice,
                        'lines': [line],
                        'product_id': line.product_id,
                        'price_unit': line.price_unit,
                        'tax_ids': line.tax_id,
                        'name': line.name,
                        'product_uom': line.product_id.product_tmpl_id.uom_id ,
                        'analytic_distribution': line.analytic_distribution,
                        'discount': line.discount,
                    }

        return so_products

    def _get_invoice_products(self, invoice):
        """
        Get products from invoice lines
        """
        inv_products = {}

        for line in invoice.invoice_line_ids:
            if line.product_id and not line.display_type:
                key = self._create_invoice_line_key(line)
                if key in inv_products:
                    inv_products[key] += line.quantity
                else:
                    inv_products[key] = line.quantity

        return inv_products

    def _create_product_key(self, sale_line):
        """
        Create a unique key for sale order line
        """
        return (
            sale_line.product_id.id,
            round(sale_line.price_unit, 2),
            tuple(sorted(sale_line.tax_id.ids)),
            round(sale_line.discount, 2)
        )

    def _create_invoice_line_key(self, invoice_line):
        """
        Create a unique key for invoice line
        """
        return (
            invoice_line.product_id.id,
            round(invoice_line.price_unit, 2),
            tuple(sorted(invoice_line.tax_ids.ids)),
            round(invoice_line.discount, 2)
        )

    def _prepare_missing_line_data(self, so_data, missing_qty):
        """
        Prepare data for missing invoice line
        """
        return {
            'product_id': so_data['product_id'].id,
            'name': so_data['name'],
            'quantity': missing_qty,
            'price_unit': so_data['price_unit'],
            'tax_ids': [(6, 0, so_data['tax_ids'].ids)],
            'product_uom_id': so_data['product_uom'].id,
            'analytic_distribution': so_data['analytic_distribution'],
            'discount': so_data['discount'],
            'sale_line_ids': [(6, 0, [line.id for line in so_data['lines']])],
        }

    def _add_missing_lines_to_invoice(self, invoice, missing_lines):
        """
        Add missing lines to the invoice
        """
        for line_data in missing_lines:
            # Prepare the line values
            line_vals = {
                'move_id': invoice.id,
                'product_id': line_data['product_id'],
                'name': line_data['name'],
                'quantity': line_data['quantity'],
                'price_unit': line_data['price_unit'],
                'tax_ids': line_data['tax_ids'],
                'product_uom_id': line_data['product_uom_id'],
                'analytic_distribution': line_data['analytic_distribution'],
                'discount': line_data['discount'],
                'sale_line_ids': line_data.get('sale_line_ids', []),
            }

            # Create the invoice line
            invoice_line = self.env['account.move.line'].create(line_vals)

            # Trigger onchange methods to compute taxes and other fields
            # invoice_line._onchange_product_id()

    def _post_invoice(self, invoice):
        """
        Post the invoice
        """
        try:
            if invoice.state == 'draft':
                invoice.action_post()
            return True
        except Exception as e:
            _logger.error(f"Cannot post invoice {invoice.name}: {str(e)}")
            raise UserError(f"Cannot post invoice {invoice.name}: {str(e)}")

    def _show_results(self, processed_invoices, errors):
        """
        Display results to the user
        """
        message = ""
        notification_type = 'success'

        if processed_invoices:
            message += _("Successfully processed %d invoices:\n") % len(processed_invoices)
            for invoice_name in processed_invoices[:10]:  # Show max 10 invoices
                message += f"• {invoice_name}\n"
            if len(processed_invoices) > 10:
                message += f"• ... and {len(processed_invoices) - 10} more\n"

        if errors:
            message += f"\n{_('Errors encountered')}:\n"
            for error in errors[:10]:  # Show max 10 errors
                message += f"• {error}\n"
            if len(errors) > 10:
                message += f"• ... and {len(errors) - 10} more errors\n"
            notification_type = 'warning'

        if not processed_invoices and not errors:
            message = _("No missing lines found in the selected sales orders' invoices.")
            notification_type = 'info'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoice Regeneration Results'),
                'message': message,
                'sticky': True,
                'type': notification_type,
            }
        }

