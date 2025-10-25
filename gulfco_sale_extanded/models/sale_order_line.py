from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    item_code = fields.Char(string="Item Code", related='product_id.default_code', readonly=True)
    barcode = fields.Char(string="Barcode", related='product_id.barcode', readonly=True)
    # total_wh_sellable = fields.Float(string="Total WH Sellable", compute="_compute_total_wh_sellable", readonly=True)
    # reserved_qty = fields.Float(string="Reserved Qty", compute="_compute_reserved_qty", readonly=True)
    exercise_price = fields.Float(string="Excise price",compute="_compute_exercise_price",store=True,digits=(4,4))
    division = fields.Selection(string="Division", related='product_id.division', readonly=True)
    available_qty_selected = fields.Float(string="Available Qty (Selected Warehouse)", store=True)
    available_qty_other = fields.Json(string="Available Qty (Other Warehouses)", store=True)
    forecasted_qty = fields.Float(string="Forecasted Qty", store=True)

    discount_approval_state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Discount Approval State", default="approved")

    old_discount = fields.Float(string='Previous Discount', copy=False)
    line_sequence = fields.Integer(string="Line Sequence", compute="_compute_line_sequence", store=True)
    customer_article_code = fields.Char(
        string='Customer Article Code',
        compute='_compute_customer_article_code',
        store=False,
    )
    product_packaging_id = fields.Many2one(
        comodel_name='product.packaging',
        string="Packaging",
        compute='_compute_custom_product_packaging_id',
        store=True, readonly=False, precompute=True,
        domain="[('sales', '=', True), ('product_id','=',product_id)]",
        check_company=True)
    product_packaging_qty = fields.Float(
        string="Packaging Quantity",
        compute='_compute_custom_product_packaging_qty',
        store=True, readonly=False, precompute=True)


    packaging_barcode = fields.Char(
        string='Packaging Barcode',
        compute='_compute_packaging_barcode',
        inverse='_inverse_packaging_barcode',
        store=True
    )
    product_packaging_price = fields.Float(
        string="Packaging Price",
        compute='_compute_custom_product_packaging_price',
        store=True, readonly=False, precompute=True)



    @api.depends('price_unit','product_packaging_id')
    def _compute_custom_product_packaging_price(self):
        for line in self:

            product_packaging_price = 0

            if line.order_id.pricelist_id and line.product_id:
                pricelist_item = line.order_id.pricelist_id._get_product_rule(line.product_id, line.product_uom_qty,
                                                                              line.order_id.partner_id)
                if pricelist_item:
                    price_item = self.env['product.pricelist.item'].browse(pricelist_item).exists()
                    price_item = price_item[0] if price_item else None
                    if line.product_packaging_id.package_type_id.type in ['box'] and price_item.box_price:
                        product_packaging_price = price_item.box_price * line.product_packaging_qty
                    elif line.product_packaging_id.package_type_id.type in ['ctn'] and price_item.ctn_price:
                        product_packaging_price = price_item.ctn_price * line.product_packaging_qty
                    elif line.product_packaging_id.package_type_id.type in ['plt'] and price_item.plt_price:
                        product_packaging_price = price_item.plt_price * line.product_packaging_qty




                    line.product_packaging_price = product_packaging_price
                else:
                    line.product_packaging_price = line.price_unit * line.product_packaging_id.qty
            else:
                line.product_packaging_price = line.price_unit * line.product_packaging_id.qty

    invoice_name = fields.Char(related='order_id.invoice_ids.name', string='Invoice Number')
    gross_amount = fields.Float(compute='_compute_gross_amount', string='Gross Amount')
    discount_invoiced_amount = fields.Float(compute='_compute_gross_amount', string='Discount Invoiced Amount')
    net_amount_invoiced = fields.Float(compute='_compute_gross_amount', string='Net Amount Invoiced')
    product_category = fields.Many2one('product.category',related='product_id.categ_id', string='Product Category')
    brand = fields.Many2one('product.brand',related='product_id.brand_id', string='Brand')
    team_id = fields.Many2one('crm.team',related='order_id.team_id', string='Sales Team')

    order_creation_source = fields.Selection(
        [('vansales', 'Vansales'), ('presales', 'Presales'), ('back_office', 'Back Office')],
        string="Order Source", default="back_office", related='order_id.order_creation_source'
    )
    po_number = fields.Char(related='order_id.po_number', string='PO Number')
    channel = fields.Text(related='order_partner_id.partner_channel_id.channel_name', string='Channel')
    sub_channel = fields.Char(related='order_partner_id.customer_subdivision_id.display_name', string='Sub Channel')
    mars_team_channel = fields.Char(related='order_partner_id.external_ref', string='MARS Team Channel')
    customer_code = fields.Char(related='order_partner_id.customer_code', string='Customer Code')
    customer_name = fields.Char(related='order_partner_id.name', string='Customer name')
    delivery_address = fields.Many2one('res.partner',related='order_id.partner_shipping_id', string='Delivery Address')
    contact_address = fields.Char(related='order_partner_id.contact_address_complete', string='Contact Address')
    site_number = fields.Char(related='order_partner_id.child_ids.site_number', string='Contact Site #')
    product_code = fields.Char(related='product_id.default_code', string='Product Code')

    order_date = fields.Datetime(related='order_id.date_order', string='Order Date')
    invoice_date = fields.Date(related='order_id.invoice_ids.date', string='Invoice Date')
    invoice_number = fields.Char(related='order_id.invoice_ids.name', string='Invoice Number')





    @api.depends('price_unit', 'qty_invoiced', 'discount')
    def _compute_gross_amount(self):
        for rec in self:
            rec.gross_amount = rec.price_unit * rec.qty_invoiced
            rec.discount_invoiced_amount = (rec.price_unit * rec.qty_invoiced * rec.discount) / 100
            rec.net_amount_invoiced = (rec.price_unit * rec.qty_invoiced) - ((rec.price_unit * rec.qty_invoiced * rec.discount) / 100)


    @api.depends('price_unit','product_packaging_id')
    def _compute_custom_product_packaging_price(self):
        for line in self:
            line.product_packaging_price = line.price_unit * line.product_packaging_id.qty

    @api.depends('product_packaging_id')
    def _compute_packaging_barcode(self):
        for line in self:
            line.packaging_barcode = line.product_packaging_id.barcode if line.product_packaging_id else False

    def _inverse_packaging_barcode(self):
        for line in self:
            if line.packaging_barcode:
                packaging = self.env['product.packaging'].search([('barcode', '=', line.packaging_barcode)],
                                                                 limit=1)
                if packaging:
                    line.product_packaging_id = packaging.id

    @api.onchange('product_uom_qty','product_id')
    def custom_onchange_product_uom_qty(self):
        if self.product_id and self.product_id.min_invoiceable_qty and self.product_id.min_invoiceable_qty > 0  and not self.product_packaging_id:
            invoiceable_qty = self.product_uom_qty / self.product_id.min_invoiceable_qty
            self.product_uom_qty = self.product_id.min_invoiceable_qty * round(invoiceable_qty)
            
    @api.onchange('product_packaging_id','product_packaging_qty', 'product_id')
    def custom_onchange_product_packaging(self):
        if self.order_id.order_creation_source not in ['vansales','presales'] and self.product_id and self.product_id.min_invoiceable_qty and self.product_id.min_invoiceable_qty > 0  and self.product_packaging_id and self.product_packaging_id.package_type_id.is_each:
            invoiceable_qty = self.product_packaging_qty / self.product_id.min_invoiceable_qty
            self.product_packaging_qty = self.product_id.min_invoiceable_qty * round(invoiceable_qty)

    def _prepare_invoice_line(self, **optional_values):
        invoice_line = super()._prepare_invoice_line(**optional_values)
        invoice_line['exercise_price'] = self.exercise_price
        invoice_line['product_packaging_price'] = self.product_packaging_price
        if self.product_template_id and self.product_template_id.invoice_policy == 'delivery':
            if self.product_packaging_id:
                invoice_line['product_packaging_qty'] = self.qty_delivered / self.product_packaging_id.qty
            else:
                invoice_line['product_packaging_qty'] = self.qty_delivered
        else:
            invoice_line['product_packaging_qty'] = self.product_packaging_qty
        invoice_line['product_packaging_id'] = self.product_packaging_id.id
        return invoice_line


    @api.depends('product_id')
    def _compute_custom_product_packaging_id(self):
        for line in self:
            # remove packaging if not match the product
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False
            # suggest biggest suitable packaging matching the SO's company
            if line.product_id and line.product_uom_qty and line.product_uom:
                suggested_packaging = line.product_id.packaging_ids \
                    .filtered(lambda p: p.sales and (p.product_id.company_id <= p.company_id <= line.company_id)) \
                    ._find_suitable_product_packaging(line.product_uom_qty, line.product_uom)
                line.product_packaging_id = suggested_packaging or line.product_packaging_id

    @api.depends('product_packaging_id','product_uom_qty')
    def _compute_custom_product_packaging_qty(self):
        self.product_packaging_qty = 0
        for line in self:
            if not line.product_packaging_id:
                continue            
            if line.order_id.order_creation_source  not in ['vansales','presales'] and line.product_id and self.product_id.min_invoiceable_qty and self.product_id.min_invoiceable_qty > 0 and line.product_packaging_id and line.product_packaging_id.package_type_id.is_each:
                invoiceable_qty = line.product_packaging_qty / line.product_id.min_invoiceable_qty
                self.product_packaging_qty = self.product_id.min_invoiceable_qty * round(invoiceable_qty)
            else:
                line.product_packaging_qty = line.product_packaging_id._compute_qty(line.product_uom_qty, line.product_uom)

    @api.depends('product_id', 'order_id.partner_id')
    def _compute_customer_article_code(self):
        for line in self:
            code = False
            product = line.product_id.product_tmpl_id
            order_partner = line.order_id.partner_id
            if product and order_partner:
                article = product.customer_article_ids.filtered(lambda a: a.partner_id == order_partner)
                if article:
                    code = article[0].name
            line.customer_article_code = code

    @api.depends('order_id.partner_id', 'product_id','order_id.assign_to')
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
        if self.order_id.assign_to and self.order_id.assign_to.location_analytic_account_id:
            analytic_account_ids += self.order_id.assign_to.location_analytic_account_id
        return analytic_account_ids

    @api.depends('product_id','product_id.exercise_price')
    def _compute_exercise_price(self):
        for rec in self:
            exercise_price = 0
            if rec.product_id:
                exercise_price = rec.product_id.exercise_price
            rec.exercise_price = exercise_price

    @api.depends('order_id', 'create_date', 'sequence')
    def _compute_line_sequence(self):
        for order in self.mapped('order_id'):
            lines = order.order_line.sorted('sequence')
            for idx, line in enumerate(lines, start=1):
                line.line_sequence = idx

    def write(self, vals):
        for line in self:
            if 'discount' in vals:
                line.old_discount = line.discount
        res = super().write(vals)
        if 'discount' in vals:
            self._handle_discount_change()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for vals in vals_list:
            if vals.get("product_packaging_qty"):
                res._compute_product_uom_qty()
        return res

    def _handle_discount_change(self):
        group = self.env.ref('gulfco_sale_extanded.discount_approvel_group')
        if not group:
            raise UserError("Approval group not found.")
        group_users = group.users
        for order in self.mapped('order_id'):
            if self.env.context.get('from_reject'):
                order.state = 'rejected'
            else:
                order.state = 'pending'
                order.is_discount_panding = True
        for line in self:
            if self.env.context.get('from_reject'):
                line.discount_approval_state = 'rejected'
            else:
                line.discount_approval_state = 'pending'

            # Create a message for each user in the group

        # for user in group_users:
        #     line.order_id.activity_schedule(
        #         'mail.mail_activity_data_todo',
        #         summary='Discount Approval Needed',
        #         note=f'Please review the discount on line: {line.name}',
        #         user_id=user.id,
        #         date_deadline=fields.Date.today()
        #     )


    # @api.onchange('product_id', 'order_id.warehouse_id')
    # def _compute_available_qty_selected(self):
    #     for line in self:
    #         warehouse = line.order_id.warehouse_id
    #         if warehouse and line.product_id:
    #             stock_quant = self.env['stock.quant'].search([
    #                 ('product_id', '=', line.product_id.id),
    #                 ('location_id', '=', warehouse.view_location_id.id)
    #             ])
    #             line.available_qty_selected = sum(stock_quant.mapped('quantity'))
    #         else:
    #             line.available_qty_selected = False

    @api.onchange('product_id', 'order_id.warehouse_id', 'order_id.warehouse_id')
    def _compute_available_qty_other(self):
        if self.order_id:
            product_ids = [line.product_id.id for line in self.order_id.order_line if line != self]
            if self.product_id.id in product_ids:
                raise UserError(_("This product is already added in another line."))
        for line in self:
            if line.product_id:
                warehouse_selected = line.order_id.warehouse_id
                stock_data = {}
                # available_qty_selected = 0
                stock_quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id)
                ])
                for quant in stock_quants:
                    warehouse = quant.location_id.warehouse_id
                    if warehouse and warehouse.id != warehouse_selected.id:
                        stock_data[warehouse.name] = stock_data.get(warehouse.name, 0) + quant.quantity
                line.available_qty_other = stock_data
                line.available_qty_selected = line.product_id.with_context(warehouse_id=line.order_id.warehouse_id.id).read(['qty_available'])[0].get('qty_available') or 0
                line.forecasted_qty = line.product_id.with_context(warehouse_id=line.order_id.warehouse_id.id).read(['virtual_available'])[0].get('virtual_available') or 0
            else:
                line.available_qty_other = False
                line.available_qty_selected = False
                line.forecasted_qty = False

    @api.onchange('tax_id')
    def onchange_tax_id(self):
        for line in self:
            if line.order_id.fiscal_position_id and line.tax_id:
                fiscal_position_id = line.order_id.fiscal_position_id
                allowed_tax_ids = fiscal_position_id.tax_ids.mapped('tax_dest_id')
                not_allowed_tax_ids = line.tax_id.filtered(lambda tax:tax._origin.id not in allowed_tax_ids.ids)._origin
                if any(not_allowed_tax_ids):
                    line.tax_id = line.tax_id._origin - not_allowed_tax_ids
                    return {
                        'tax_id':line.tax_id - not_allowed_tax_ids,
                        'warning': {
                            'title': _("Warning"),
                            'message': _(
                            f"you can apply {'-'.join(not_allowed_tax_ids.mapped('name'))} tax because it's not exist in fiscal position tax mapping"
                            )
                        }
                    }