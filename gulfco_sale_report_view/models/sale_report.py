# -*- coding: utf-8 -*-
#############################################################################
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
from odoo import api, fields, models, tools




class SaleReportView(models.Model):
    _name = "sale.report.view"
    _description = "Sale Report View"
    _auto = False

    line_id = fields.Many2one('sale.order.line', string='Order Line')
    ############################################(Sale Order)########################################
    name = fields.Char("Order No")
    partner_id = fields.Many2one("res.partner", "Customer")
    partner_shipping_id = fields.Many2one("res.partner", "Delivery Address")
    assign_to = fields.Many2one("res.partner", "Salesman")
    date_order = fields.Date("Order Date")
    state = fields.Selection([('draft','Draft'),
                                    ('sent','Sent'),
                                    ('pending','Waiting Approval'),
                                    ('approved','Approved'),
                                    ('rejected','Rejected'),
                                    ('sale','Sale Order'),
                                    ('cancel','Cancelled'),
                                    ('waiting_for_release','Request to Release'),
                                    ('awaiting_credit_approval','Waiting Credit Approval'),], "Order Status")
    delivery_status = fields.Selection([('pending','Not Delivered'),
                                    ('started','Started'),
                                    ('partial','Partially Delivered'),
                                    ('full','Fully Delivered')], "Delivery Status")
    invoice_status = fields.Selection([('upselling','Upselling Opportunity'),
                                    ('invoiced','Fully Invoiced'),
                                    ('to invoice','To Invoice'),
                                    ('no','Nothing To Invoice')], "Invoice Status")
    #########################################(Sale Order Line)######################################
    product_id = fields.Many2one("product.product", "Product")
    product_packaging_id = fields.Many2one("product.packaging", "SO Packaging")
    product_packaging_qty = fields.Float("SO Packaging QTY")
    product_packaging_price = fields.Float("SO Packaging Price")
    product_uom_qty = fields.Float("SO Unit QTY")
    price_unit = fields.Float("SO Unit Price")
    qty_delivered = fields.Float("Delivered QTY")
    qty_invoiced = fields.Float("Invoiced QTY")
    exercise_price = fields.Float("SO Excise Tax")
    discount_amount = fields.Float("SO Discount Amount")
    discount = fields.Float("SO Discount Percentage")
    price_subtotal = fields.Float("SO Total Before VAT")
    price_tax = fields.Float("SO VAT Amount")
    #price_total = fields.Float("SO Total After VAT")
    #############################################(Customer)#########################################
    customer_code = fields.Char("Customer Code")
    partner_channel_id = fields.Many2one("channel.channel", "Channel")
    outlet_id = fields.Many2one("outlet.channel", "Outlet")
    sub_outlet_id = fields.Many2one("sub.outlet.channel", "SubOutlet")
    customer_type = fields.Selection([('cash','Cash'),
                                     ('credit','Credit')], "Customer Type")
    customer_group_id = fields.Many2one("customer.group", "Customer Group")
    customer_subdivision_id = fields.Many2one("customer.subdivision", "Customer Division")
    ##############################################(Product)#########################################
    default_code = fields.Char("Internal Reference")
    categ_id = fields.Many2one("product.category", "Product Category")
    brand_id = fields.Many2one("product.brand", "Brand")
    division = fields.Selection([('food','Food'),
                                         ('non_food','Non Food'),
                                         ('3pl','3PL'),
                                         ('local','Local'),
                                         ('posm','POSM'),
                                         ('mars','Mars')], "Product Division")
    ##############################################(Invoice)#########################################
    invoice_date = fields.Date("Invoice Date")
    inv_name = fields.Char("Invoice No")
    inv_product_packaging_id = fields.Many2one("product.packaging", "INV Packaging")
    inv_product_packaging_qty = fields.Float("INV Packaging QTY")
    inv_product_packaging_price = fields.Float("INV Packaging Price")
    inv_price_unit = fields.Float("INV Unit Price")
    quantity = fields.Float("INV Unit QTY")
    inv_exercise_price = fields.Float("INV Excise Tax")
    inv_state = fields.Selection([('draft','Draft'),
                                  ('posted','Posted'),
                                  ('cancel','Canceled'),
                                  ('waiting_for_release','Request to Release'),
                                  ('awaiting_credit_approval','Waiting Credit Approval')],"INV Status")
    inv_discount_amount = fields.Float("INV VAT Amount")
    inv_price_subtotal = fields.Float("INV Total Before VAT")
    #inv_price_total = fields.Float("INV Total After VAT")





    purchase_price = fields.Float("Cost")



    def _init_report_view(self):
        tools.drop_view_if_exists(self._cr, 'sale_report_view')
        self._cr.execute("""CREATE OR REPLACE VIEW sale_report_view AS
                (SELECT
                    sol.id AS id,  -- Use the actual line ID as the primary ID
                    sol.id AS line_id,
                    sol.product_id,
                    sol.product_packaging_id,
                    sol.product_packaging_qty,
                    sol.product_packaging_price,
                    sol.product_uom_qty,
                    sol.price_unit,
                    sol.qty_delivered,
                    sol.qty_invoiced,
                    sol.exercise_price,
                    sol.discount_amount,
                    sol.discount,
                    sol.price_subtotal,
                    sol.price_tax,
                    sol.price_total,
                    so.name,
                    so.partner_id,
                    so.partner_shipping_id,
                    so.assign_to,
                    so.date_order,
                    so.state,
                    so.delivery_status,
                    so.invoice_status,
                    pp.default_code,
                    pp.categ_id,
                    pp.brand_id,
                    pp.division,
                    rp.customer_code,
                    rp.partner_channel_id,
                    rp.outlet_id,
                    rp.sub_outlet_id,
                    rp.customer_type,
                    rp.customer_group_id,
                    rp.customer_subdivision_id

                FROM sale_order_line sol
                JOIN sale_order so ON sol.order_id = so.id
                JOIN product_template pp ON sol.product_id = pp.id
                JOIN res_partner rp ON so.partner_id = rp.id
                AND so.state = 'sale'
                );
        """)

    def init(self):
        """Model initialization - creates the view when module is installed/updated"""
        self._init_report_view()

