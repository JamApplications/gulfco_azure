# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import formatLang


class PurchaseOrder(models.Model):
    """ to add custom fields in purchase order"""

    _inherit = 'purchase.order'

    po_category = fields.Selection([('foreign', 'FPO'), ('local', 'LPO')], string='PO Category')
    po_type = fields.Selection([('non_tradable', 'Non Tradable'), ('tradable', 'Tradable')],
                               default='tradable', string='PO Type')
    shipment_mode = fields.Selection([('land', 'Land'), ('ocean', 'Ocean'), ('air', 'Air')], string='Shipment Mode')
    payment_type= fields.Many2one('account.payment.method.line', string='Payment Type')

    revision = fields.Integer('Revision', readonly=True, copy=False)
    po_remarks = fields.Char('PO Remarks')
    shipping_remarks = fields.Char('Shipping Remarks')
    packaging_remarks = fields.Char('Packaging Remarks')
    insurance_detail = fields.Char('Insurance Detail')
    special_condition = fields.Char('Special Condition')
    vendor_trn = fields.Char('Vendor TRN',compute="compute_vendor_trn",store=True,readonly=False)
    supplier_contact = fields.Many2one('res.partner', string='Supplier Contact Person', domain="[('parent_id', '=', partner_id), ('type', '=', 'contact')]")

    asn_count = fields.Integer(compute='_compute_asn_count')
    asn_ids = fields.Many2many('asn.request', 'purchase_asn_relation_ref')
    order_analysis = fields.Char('Order Analysis#')
    delivery_to_contact = fields.Many2one('res.partner', 'Delivery To Contact')
    has_service_products = fields.Boolean(
        string='Has Service/Consumable Products',
        compute='_compute_has_service_consumable_products',
        store=True
    )
    is_full_received = fields.Boolean(string="Is Fully Received",compute="compute_is_full_received",store=False)

    def action_view_bill_matching(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Bill Matching Report',
            'res_model': 'purchase.bill.matching.report',
            'view_mode': 'list,form',
            'domain': [('purchase_line_id', 'in', self.order_line.ids)],
        }

    def action_view_multiple_bill_matching(self):
        order_line = self.mapped('order_line')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Bill Matching Report',
            'res_model': 'purchase.bill.matching.report',
            'view_mode': 'list,form',
            'domain': [('purchase_line_id', 'in', order_line.ids)],
        }

    def action_po_amendment(self):
        for order in self:
            if order.state == 'purchase' and order.picking_ids:
                # Cancel backorders
                for picking in order.picking_ids.filtered(
                        lambda p: p.backorder_id and p.state not in ('done', 'cancel')):
                    picking.action_cancel()
                order.button_draft()
                new_lines = []
                for line in order.order_line:
                    if line.qty_received < line.product_qty:
                        received_qty = line.qty_received
                        original_qty = line.product_qty
                        remaining_qty = original_qty - received_qty
                        line.write({'product_qty': received_qty,'is_existing_line':True})
                        new_line_vals = line.copy_data()[0]
                        new_line_vals['order_id'] = order.id
                        new_line_vals['is_existing_line'] = False
                        new_line = self.env['purchase.order.line'].new(new_line_vals)
                        new_line.onchange_product_id()
                        # new_line._onchange_product_packaging_id()
                        final_vals = new_line._convert_to_write(new_line._cache)
                        final_vals['product_qty'] = remaining_qty
                        if line.product_packaging_id and line.product_uom:
                            product_packaging_qty = line.product_packaging_id._compute_qty(remaining_qty, line.product_uom)
                            final_vals['product_packaging_qty'] = product_packaging_qty
                        new_lines.append((0, 0, final_vals))
                if new_lines:
                    order.write({'order_line': new_lines})
                    new_order_lines = order.order_line.filtered(lambda s: not s.is_existing_line)
                    # new_order_lines._compute_product_packaging_id()
                    new_order_lines._compute_price_unit_and_date_planned_and_name()
                    # new_order_lines._compute_product_packaging_qty()
                    new_order_lines._compute_package_price()


    # @api.depends('order_line.qty_received', 'order_line.product_qty')
    def compute_is_full_received(self):
        for order in self:
            is_full_received = True
            if any(line.qty_received and line.qty_received < line.product_qty for line in order.order_line.filtered(lambda s:not s.is_existing_line)):
                is_full_received = False
            order.is_full_received = is_full_received


    @api.depends("order_line.product_id", "order_line.product_id.type")
    def _compute_has_service_consumable_products(self):
        for order in self:
            order.has_service_products = any(
                line.product_id.type in ["service", "consu"]
                and not line.product_id.is_storable
                for line in order.order_line
            )

    @api.depends('partner_id')
    def compute_vendor_trn(self):
        for record in self:
            if record.partner_id and record.partner_id.vat_trn:
                record.vendor_trn = record.partner_id.vat_trn
            else:
                record.vendor_trn = False

    def print_quotation(self):
        """Override Base prin quotation with new printout"""
        self.write({'state': "sent"})
        return self.env.ref('purchase_line_views.action_report_rfq_purchase_order').report_action(self)

    def amount_to_text(self, amount):
        """Convert Amount in local currency world"""
        convert_amount_in_words = self.currency_id.amount_to_text(amount)
        return convert_amount_in_words

    def _compute_asn_count(self):
        """Count linked ASn order with purchase order"""
        for po in self:
            po.asn_count = 0
            po.asn_ids = None
            asn_records = po.asn_ids.search([])
            for rec in asn_records:
                if po.id in rec.line_ids.mapped('purchase_order_id').ids:
                    po.asn_count +=1
                    po.asn_ids = [(4,rec.id)]

    def open_asn_link(self):
        action = self.env['ir.actions.act_window']._for_xml_id('asn_request.action_asn_request')
        action['context'] = {}
        if len(self.asn_ids) > 1:
            action['domain'] = [('id', 'in', self.asn_ids.ids)]
        elif len(self.asn_ids) == 1:
            res = self.env.ref('asn_request.view_asn_request_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = self.asn_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    @api.onchange('partner_id')
    def _onchange_payment_type_from_vandore(self):
        """get vendor trn no and payment type from partner"""
        self.vendor_trn = self.partner_id.vat_trn
        if self.partner_id.property_outbound_payment_method_line_id:
            self.payment_type = self.partner_id.property_outbound_payment_method_line_id.id
        """ Warning when supplier is on hold"""
        if self.partner_id and self.partner_id.supplier_hold:
            self.partner_id = None
            return {
                'warning': {
                    'title': _("Supplier on Hold"),
                    'message': _("This Supplier is on Hold"),
                }
            }

    # @api.depends_context('lang')
    # @api.depends('order_line.price_subtotal', 'currency_id', 'company_id')
    # def _compute_tax_totals(self):
    #     AccountTax = self.env['account.tax']
    #     for order in self:
    #         if not order.company_id:
    #             order.tax_totals = False
    #             continue
    #         order_lines = order.order_line.filtered(lambda x: not x.display_type)
    #         base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
    #         AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
    #         AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
    #         order.tax_totals = AccountTax.with_context(from_purchase_order=True,po_id=order)._get_tax_totals_summary(
    #             base_lines=base_lines,
    #             currency=order.currency_id or order.company_id.currency_id,
    #             company=order.company_id,
    #         )
    #         if order.currency_id != order.company_currency_id:
    #             order.tax_totals['amount_total_cc'] = f"({formatLang(self.env, order.amount_total_cc, currency_obj=self.company_currency_id)})"


class AccountTaxInh(models.Model):
    _inherit = 'account.tax'

    # @api.model
    # def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
    #     res = super(AccountTaxInh, self)._get_tax_totals_summary(base_lines, currency, company, cash_rounding)
    #     if self.env.context.get('from_purchase_order'):
    #         po_order = self.env.context.get('po_id')
    #         if po_order.order_line:
    #             amount = sum(po_order.order_line.mapped('price_subtotal'))
    #             total_amount = sum(po_order.order_line.mapped('price_total'))
    #             for po_line in res.get('subtotals'):
    #                 po_line.update({
    #                     'base_amount': amount,
    #                     'base_amount_currency': amount,
    #                 })
    #             res.update({
    #                 'total_amount_currency': total_amount,
    #                 'total_amount': total_amount,
    #             })
    #     return res

    # def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
    #     # EXTENDS 'account'
    #     results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
    #     if record._name == 'purchase.order.line':
    #         if 'price_unit' and results:
    #             results['price_unit'] = results['price_unit'] + record.exercise_price
    #     return results
