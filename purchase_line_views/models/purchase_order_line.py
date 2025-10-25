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
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from pytz import UTC

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    """ For adding product image directly
    to purchase order line from product"""

    _inherit = 'purchase.order.line'

    po_type = fields.Selection(related='order_id.po_type', store=True)
    # Add PO line indexing fields and many more custom fields
    po_line_index = fields.Integer(string='#',
                                     compute='_compute_po_line_index',
                                     help='Line Numbers')

    vendor_item_code = fields.Char(string='Vendor Item Code', compute='_compute_vendor_item_code', store=True)
    asn_released_qty = fields.Float(string='ASN released Qty', compute='_compute_product_asn_qty')
    available_qty_to_release = fields.Float(string='Available QTY to Release', compute='_compute_product_asn_qty')

    rdd = fields.Datetime(string='RDD', compute="_compute_rdd_planned_from_supplier", readonly=False, store=True)
    is_excise = fields.Boolean(string='Is Excise')
    package_price = fields.Float('Package Price', compute="_compute_package_price",inverse="_inverse_package_price", store=True)
    exercise_price = fields.Float(string="Excise price (AED)",compute="_compute_exercise_price",store=True,digits=(4,4))
    excise_price_total  = fields.Float(string="Excise Total",compute="_compute_excise_price_total",store=True)
    is_existing_line = fields.Boolean(string="Is Existing Line",copy=False)


    crt_ctn_qty = fields.Float('CTN Qty', compute='_compute_due_qty', store=True)
    # crt_asn_released_qty = fields.Float('ASN Released Qty', compute='_compute_due_qty', store=True)
    # crt_available_qty_to_release = fields.Float('Available QTY to Release', compute='_compute_due_qty', store=True)
    # crt_due_qty = fields.Float('Due Qty', compute='_compute_due_qty', store=True)
    crt_asn_released_qty = fields.Float('ASN Released Qty (CTN)', compute='_compute_due_qty', store=True)
    crt_available_qty_to_release = fields.Float('Available Qty to Release (CTN)', compute='_compute_due_qty',store=True)
    crt_due_qty = fields.Float('Due Qty (CTN)', compute='_compute_due_qty', store=True)

    received_qty_ctn = fields.Float('Received Qty (CTN)', compute='_compute_due_qty', store=True)
    billing_qty_ctn = fields.Float('Billing Qty (CTN)', compute='_compute_due_qty', store=True)


    @api.depends('product_qty','order_id.asn_ids')
    def _compute_due_qty(self):
        crt_asn_released_qty = 0
        crt_ctn_qty = 0
        crt_available_qty_to_release = 0
        qty_in_invoice = 0.0

        received_qty_ctn = 0
        billing_qty_ctn = 0


        for rec in self:
            asn_ids = []
            asn_records = self.env['asn.request'].search([])
            for record in asn_records:
                if rec.order_id.id in record.line_ids.mapped('purchase_order_id').ids:
                    asn_ids.append(record.id)

            for record in self.env['asn.request'].sudo().search([('id', 'in', asn_ids)]):
                for rec_line in record.line_ids.filtered(lambda l: l.product_product_id.id == rec.product_id.id and l.purchase_order_line_id.id == rec.id):
                    qty_in_invoice += rec_line.qty_in_invoice
                    crt_available_qty_to_release = rec_line.available_qty_to_release_ctn

            ctn_package = rec.product_id.packaging_ids.filtered(
                lambda s: s.package_type_id.type == 'ctn')
            if rec.product_id and rec.product_qty and ctn_package:
                crt_ctn_qty = rec.product_qty / ctn_package[0].qty
            if rec.product_id and qty_in_invoice and ctn_package:
                crt_asn_released_qty = qty_in_invoice / ctn_package[0].qty
            if rec.product_id and rec.qty_received and ctn_package:
                received_qty_ctn = rec.qty_received / ctn_package[0].qty
            if rec.product_id and rec.qty_invoiced and ctn_package:
                billing_qty_ctn = rec.qty_invoiced / ctn_package[0].qty
            if rec.product_id and rec.available_qty_to_release and ctn_package:
                # crt_available_qty_to_release = rec.available_qty_to_release / ctn_package[0].qty
                crt_available_qty_to_release = crt_available_qty_to_release

            rec.crt_ctn_qty = crt_ctn_qty or 0.0
            rec.crt_asn_released_qty = crt_asn_released_qty or 0.0
            rec.crt_available_qty_to_release = crt_available_qty_to_release or 0.0

            rec.received_qty_ctn = received_qty_ctn
            rec.billing_qty_ctn = billing_qty_ctn

            crt_due_qty = rec.crt_ctn_qty - rec.received_qty_ctn
            rec.crt_due_qty = crt_due_qty


    @api.depends('product_id', 'product_qty', 'product_uom')
    def _compute_product_packaging_id(self):
        for line in self:
            # remove packaging if not match the product
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False
            # suggest biggest suitable packaging matching the PO's company
            if line.product_id and line.product_qty and line.product_uom:
                suggested_packaging = line.product_id.packaging_ids\
                        .filtered(lambda p: p.purchase and (p.product_id.company_id <= p.company_id <= line.company_id))\
                        ._find_suitable_product_packaging(line.product_qty, line.product_uom)
                if not line.product_packaging_id:
                    line.product_packaging_id = suggested_packaging or line.product_packaging_id

    @api.depends('exercise_price','product_qty')
    def _compute_excise_price_total(self):
        for record in self:
            record.excise_price_total = record.exercise_price * record.product_qty

    @api.depends('order_id.partner_id', 'product_id', 'order_id.picking_type_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            analytic_account_ids = line._dept_location_analytic_accounts()
            if analytic_account_ids:
                if line.analytic_distribution:
                    for ids, percentage in line.analytic_distribution.items():
                        account_ids  = [int(i) for i in ids.split(',')]
                        analytic_account_ids += self.env['account.analytic.account'].browse(account_ids)
                unique_ids = sorted(set(analytic_account_ids.ids))
                line.analytic_distribution = {','.join(str(i) for i in unique_ids): 100}
                # line.analytic_distribution = {','.join([str(i) for i in analytic_account_ids.ids]): 100}
                # final_dist = dict(line.analytic_distribution or {})
                # for acc_id in account_ids:
                #     final_dist[acc_id] = 100.0
                # line.analytic_distribution = final_dist

    def _dept_location_analytic_accounts(self):
        analytic_account_ids = self.env['account.analytic.account']
        if self.product_id.costing_dept_code_id:
            analytic_account_ids += self.product_id.costing_dept_code_id
        if self.order_id.picking_type_id and self.order_id.picking_type_id.warehouse_id and self.order_id.picking_type_id.warehouse_id.stock_analytic_account_id:
            analytic_account_ids += self.order_id.picking_type_id.warehouse_id.stock_analytic_account_id
        return analytic_account_ids

    # @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount')
    # def _compute_amount(self):
    #     for line in self:
    #         base_line = line._prepare_base_line_for_taxes_computation()
    #         self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
    #         line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
    #         line.price_total = base_line['tax_details']['raw_total_included_currency']
    #         line.price_tax = line.price_total - line.price_subtotal

    # @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount', 'exercise_price')
    # def _compute_amount(self):
    #     res = super(PurchaseOrderLine, self)._compute_amount()
    #     for line in self:
    #         line.price_subtotal += (line.exercise_price - ((line.exercise_price * line.discount) / 100))
    #         tax_amount = ((line.exercise_price - ((line.exercise_price * line.discount) / 100)) * sum(line.taxes_id.mapped('amount'))) / 100
    #         line.price_total += (line.exercise_price - ((line.exercise_price * line.discount) / 100)) + (tax_amount if tax_amount else 0)
    #     return res

    @api.depends('product_id','product_id.exercise_price')
    def _compute_exercise_price(self):
        for rec in self:
            exercise_price = 0
            if rec.product_id:
                exercise_price = rec.product_id.exercise_price
            if exercise_price > 0.0:
                rec.is_excise = True
            else:
                rec.is_excise = False
            rec.exercise_price = exercise_price

    @api.depends('product_qty', 'product_packaging_qty', 'product_packaging_id', 'price_unit')
    def _compute_package_price(self):
        for rec in self:
            rec.package_price = 0
            package_price = (rec.product_qty / rec.product_packaging_qty) * rec.price_unit if rec.product_packaging_qty else 0
            rec.package_price = package_price or 0

    @api.onchange('package_price', 'product_packaging_qty')
    def _inverse_package_price(self):
        for rec in self:
            if rec.package_price:
                rec.price_unit = rec.package_price / rec.product_packaging_id.qty if rec.product_packaging_id.qty else 0

    @api.model
    def _get_rdd_date_planned(self, seller, po=False):
        """Return the datetime value to use as Schedule Date (``date_planned``) for RDD Custom field
        """
        date_order = po.date_order if po else self.order_id.date_order
        if date_order:
            return date_order + relativedelta(days=seller.rdd if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.rdd if seller else 0)

    @api.depends('product_qty', 'product_uom', 'company_id', 'order_id.partner_id')
    def _compute_rdd_planned_from_supplier(self):
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id:
                continue
            params = line._get_select_sellers_params()
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(
                    line),
                uom_id=line.product_uom,
                params=params)

            if seller or not line.rdd:
                line.rdd = line._get_rdd_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)


    def _compute_product_asn_qty(self):
        for line in self:
            qty_in_invoice = 0.0
            available_qty_to_release = 0.0
            asn_ids = []
            asn_records = self.env['asn.request'].search([])
            for record in asn_records:
                if line.order_id.id in record.line_ids.mapped('purchase_order_id').ids:
                    asn_ids.append(record.id)

            for rec in self.env['asn.request'].sudo().search([('id','in',asn_ids)]):
                for rec_line in rec.line_ids.filtered(lambda l: l.product_product_id.id == line.product_id.id and l.purchase_order_line_id.id == line.id):
                    qty_in_invoice += rec_line.qty_in_invoice
                    available_qty_to_release += rec_line.available_qty_to_release
            line.asn_released_qty = qty_in_invoice
            line.available_qty_to_release = available_qty_to_release
            line._compute_due_qty()

            # line._compute_po_line_state()
            # line.order_id._onchange_po_line_state()

    @api.depends('product_id', 'partner_id')
    def _compute_vendor_item_code(self):
        for line in self:
            line.vendor_item_code = None
            for rec in line.product_id.seller_ids:
                if line.partner_id.id == rec.partner_id.id:
                    line.vendor_item_code = rec.product_code

    @api.depends('sequence', 'order_id')
    def _compute_po_line_index(self):
        """Function to compute line numbers"""
        for order in self.mapped('order_id'):
            po_line_index = 1
            for lines in order.order_line:
                if lines.display_type:
                    lines.po_line_index = po_line_index
                    po_line_index += 0
                else:
                    lines.po_line_index = po_line_index
                    po_line_index += 1

    product_image = fields.Binary(
        related="product_id.image_1920",
        string="Image",
        help='For getting product image '
             'to purchase order line')

    @api.onchange('order_id')
    def _onchange_order_id(self):
        """ Restrict creating purchase order line for purchase order
                in locked,cancel and purchase order states"""

        if self.order_id.state in ['cancel', 'done', 'purchase']:
            raise UserError(_("You cannot select purchase order in "
                              "cancel or locked or purchase order state"))

    is_received_less_than_ordered = fields.Boolean(
        string='Received < Ordered',
        compute='_compute_received_less_than_ordered',
        store=True
    )

    @api.depends('qty_received', 'product_qty')
    def _compute_received_less_than_ordered(self):
        for line in self:
            line.is_received_less_than_ordered = line.qty_received < line.product_qty



    def action_asn_create(self):
        print("h8ihi")
        asn_vals = {
            # 'bl_no_asn_no': 'ASN-NO-001',
            'supplier_id': self.partner_id[0].id,
            'responsible_id':self.env.user.id,
            'company_id': self.company_id[0].id,
            'line_ids': []

        }
        asn = self.env['asn.request'].create(asn_vals)
        for rec in self:
            if len(rec.mapped('partner_id')) > 1:
                raise UserError("kjjhgvbjkl....")
            else:
                print("perform login to create ASN",  rec.order_id)
                asn_lines = {
                    'partner_id': rec.partner_id.id,
                    'purchase_order_line_id': rec.id,
                    'purchase_order_id': rec.order_id.id,
                    'product_product_id': rec.product_id.id,
                    'product_description': rec.name,
                    'po_uom': rec.product_uom.id,
                    'po_qty': rec.product_qty,
                    'po_unit_price': rec.price_unit,
                    'hs_code': rec.product_id.product_tmpl_id.hs_code,
                    'asn_released_qty': rec.asn_released_qty
                }
                rec.order_id._onchange_po_line_state()
                asn.write({'line_ids':[(0,0, asn_lines)]})
        print("ans valsL", asn_vals)
        # asn = self.env['asn.request'].create(asn_vals)
        print("asn:", asn)
        if asn and len(asn) == 1:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('The following ASN Record Created'),
                    'message': '%s',
                    'links': [{
                        'label': asn.display_name,
                        'url': f'/odoo/action-purchase_line_views.action_asn_request_form/{asn.id}'
                    }],
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Something went wrong (ASN Request not created)'),
                    'sticky': False,
                    'type': 'success',
                },
            }

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for vals in vals_list:
            if vals.get("product_packaging_qty"):
                res._compute_product_qty()
        return res

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move=move)
        if 'quantity' in res and self.env.context.get('active_model') == 'purchase.bill.matching.report' and self.env.context.get('active_ids'):
            bill_matching_report_records = self.env['purchase.bill.matching.report'].browse(self.env.context.get('active_ids'))
            po_line_records = bill_matching_report_records.filtered(lambda s:s.purchase_line_id == self)
            if po_line_records:
                res['quantity'] = sum(po_line_records.mapped('received_qty'))
                res['bill_matching_picking_ids'] = po_line_records.mapped('picking_id').ids
        return res