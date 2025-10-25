from odoo import models, fields, api, _

from odoo.exceptions import ValidationError,UserError

import logging

_logger = logging.getLogger("============API Authenticate========")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):

        for pick in self:
            if pick.partner_id and pick.partner_id.van_location and pick.partner_id.fsm_person and pick.picking_type_code == 'outgoing':
                pick.location_dest_id = pick.partner_id.van_location.id
                pick.move_line_ids.write({'location_dest_id': pick.partner_id.van_location.id})

        # Call the original method to validate the delivery
        res = super(StockPicking, self).button_validate()
        
        immediate_payment_term_line = self.env['account.payment.term.line'].sudo().search(
                                    [("nb_days", "=", 0)], limit=1)
        # Create an invoice after the delivery is validated
        for picking in self:
            if picking.state == 'done' and picking.picking_type_code == 'outgoing':
                _logger.info("GULFCO_SALE_EXTANDED outgoing onlye inside click validate")
                sale_order = picking.sale_id
                is_credit_customer = False
                if sale_order:
                    _logger.info(sale_order.order_creation_source == "vansales" and sale_order.partner_id and sale_order.partner_id.customer_type == 'credit' and not sale_order.partner_id.is_credit_hold)
                    # if sale_order.order_creation_source == "vansales" and sale_order.partner_id and sale_order.partner_id.customer_type == 'credit' and not sale_order.partner_id.is_credit_hold:
                    #     _logger.info("Correct Conditon")
                    #     is_credit_customer = True
                    _logger.info("inside sale")
                    if not is_credit_customer:
                        # full_qty_delivered = True
                        # product_id = False
                        # for line in sale_order.order_line:
                        #     if line.product_uom_qty != line.qty_delivered and line.product_id.type == 'consu':
                        #         full_qty_delivered = False
                        #         product_id = line.product_id
                        #         break
                        # if not full_qty_delivered:
                        #     return {
                        #         'success': False,
                        #         'message': "Not full quantity delivered some products need to be checked like %s" % product_id.name,
                        #         'sale_order': {
                        #             'id': sale_order.id,
                        #             'name': sale_order.name,
                        #         },
                        #     }

                        invoice = sale_order._create_invoices()
                        _logger.info("invoice created")
                        if sale_order.order_creation_source in ['vansales','presales'] and sale_order.sale_journal:
                            invoice.journal_id = sale_order.sale_journal.id
                            invoice.write({'journal_id': sale_order.sale_journal.id})
                            _logger.info("invoice assigned")
                            _logger.info("invoice journal %s sale journal %s" %(invoice.journal_id, sale_order.sale_journal))

                            if not (sale_order.partner_id.customer_type == 'credit' and sale_order.partner_id.is_credit_hold):
                                if immediate_payment_term_line:
                                    payment_term_id = immediate_payment_term_line.payment_id
                                    if payment_term_id:
                                        _logger.info("select immedite")
                                        invoice.write({'invoice_payment_term_id': payment_term_id.id})
                        # Optionally, you can post the invoice
                        try:
                            if invoice.state not in ['posted', 'cancel']:
                                invoice.action_post()
                        except:
                            for line in invoice.invoice_line_ids:
                                analytic_distribution = {
                                     line.product_id.costing_dept_code_id.id: 100,
                                }
                                line.write({'analytic_distribution': analytic_distribution or None})
                            if invoice.state not in ['posted', 'cancel']:
                                invoice.action_post()

        return res
