from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools.date_utils import start_of, end_of, add, subtract
from odoo.tools.misc import format_date
from odoo.exceptions import UserError


class SalesBudget(models.Model):
    _name = "sales.budget"
    _description = "Sales Budget"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Principle",
        required=True, change_default=True, index=True,
        tracking=1,
        check_company=True,
        domain="[('contact_type','=','customer')]")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, string="Company")
    division = fields.Selection([('food', 'Food'), ('non_food', 'Non Food')], string="Division", required=True)
    # channel = fields.Selection(related="partner_id.channel", store=True)
    partner_channel_id = fields.Many2one('channel.channel', related="partner_id.partner_channel_id", string="Channel")
    # channel_mt = fields.Selection(related="partner_id.channel_mt", store=True)
    outlet_id = fields.Many2one('outlet.channel', related="partner_id.outlet_id", string="Outlet Classification")

    # customer_group = fields.Char(related="partner_id.customer_group", store=True)
    customer_group_id = fields.Many2one('customer.group', string="Customer Group",related="partner_id.customer_group_id",store=True)
    line_ids = fields.One2many('sales.budget.line', 'sale_budget_id', string="Budget Lines")

    def open_action_view_budget_line(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_sales_budget.sales_budget_line_action")
        action['domain'] = [('id', 'in', self.line_ids.ids)]
        return action
    
    def open_action_view_budget_line_pivot(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_sales_budget.action_sale_budget_report")
        action['domain'] = [('sales_budget_line_id', 'in', self.line_ids.ids)]
        return action

class SalesBudgetLine(models.Model):
    _name = 'sales.budget.line'
    _description = 'Sales Budget Line'

    sale_budget_id = fields.Many2one('sales.budget', string="Budget")
    product_id = fields.Many2one('product.product', string="Product Code")
    product_name = fields.Char(related='product_id.name', store=True, string="SKU/Product Description", index='trigram',
                               translate=True)
    product_type = fields.Selection([('regular', 'Regular'), ('promotion', 'Promotion')],
                                    compute="compute_product_type", store=True, string="Product Type")
    brand_id = fields.Many2one('product.brand', string="Brand", related='product_id.brand_id', store=True)
    price_to_trade = fields.Float(string="Price to Trade")
    item_landed_cost = fields.Float(string="Item Landed Cost")
    gp_percentage = fields.Float(string="GP%", compute="compute_gp_percentage", store=True)

    jan_sales_volume = fields.Float()
    jan_sales_value = fields.Float(compute="compute_value",store=True)
    jan_cogs = fields.Float(compute="compute_value",store=True)
    jan_gross_margin = fields.Float(compute="compute_value",store=True)
    jan_gp = fields.Float(compute="compute_value",store=True)

    feb_sales_volume = fields.Float()
    feb_sales_value = fields.Float(compute="compute_value",store=True)
    feb_cogs = fields.Float(compute="compute_value",store=True)
    feb_gross_margin = fields.Float(compute="compute_value",store=True)
    feb_gp = fields.Float(compute="compute_value",store=True)

    march_sales_volume = fields.Float()
    march_sales_value = fields.Float(compute="compute_value",store=True)
    march_cogs = fields.Float(compute="compute_value",store=True)
    march_gross_margin = fields.Float(compute="compute_value",store=True)
    march_gp = fields.Float(compute="compute_value",store=True)

    april_sales_volume = fields.Float()
    april_sales_value = fields.Float(compute="compute_value",store=True)
    april_cogs = fields.Float(compute="compute_value",store=True)
    april_gross_margin = fields.Float(compute="compute_value",store=True)
    april_gp = fields.Float(compute="compute_value",store=True)

    may_sales_volume = fields.Float()
    may_sales_value = fields.Float(compute="compute_value",store=True)
    may_cogs = fields.Float(compute="compute_value",store=True)
    may_gross_margin = fields.Float(compute="compute_value",store=True)
    may_gp = fields.Float(compute="compute_value",store=True)

    june_sales_volume = fields.Float()
    june_sales_value = fields.Float(compute="compute_value",store=True)
    june_cogs = fields.Float(compute="compute_value",store=True)
    june_gross_margin = fields.Float(compute="compute_value",store=True)
    june_gp = fields.Float(compute="compute_value",store=True)

    july_sales_volume = fields.Float()
    july_sales_value = fields.Float(compute="compute_value",store=True)
    july_cogs = fields.Float(compute="compute_value",store=True)
    july_gross_margin = fields.Float(compute="compute_value",store=True)
    july_gp = fields.Float(compute="compute_value",store=True)

    aug_sales_volume = fields.Float()
    aug_sales_value = fields.Float(compute="compute_value",store=True)
    aug_cogs = fields.Float(compute="compute_value",store=True)
    aug_gross_margin = fields.Float(compute="compute_value",store=True)
    aug_gp = fields.Float(compute="compute_value",store=True)

    sep_sales_volume = fields.Float()
    sep_sales_value = fields.Float(compute="compute_value",store=True)
    sep_cogs = fields.Float(compute="compute_value",store=True)
    sep_gross_margin = fields.Float(compute="compute_value",store=True)
    sep_gp = fields.Float(compute="compute_value",store=True)

    oct_sales_volume = fields.Float()
    oct_sales_value = fields.Float(compute="compute_value",store=True)
    oct_cogs = fields.Float(compute="compute_value",store=True)
    oct_gross_margin = fields.Float(compute="compute_value",store=True)
    oct_gp = fields.Float(compute="compute_value",store=True)

    nov_sales_volume = fields.Float()
    nov_sales_value = fields.Float(compute="compute_value",store=True)
    nov_cogs = fields.Float(compute="compute_value",store=True)
    nov_gross_margin = fields.Float(compute="compute_value",store=True)
    nov_gp = fields.Float(compute="compute_value",store=True)

    dec_sales_volume = fields.Float()
    dec_sales_value = fields.Float(compute="compute_value",store=True)
    dec_cogs = fields.Float(compute="compute_value",store=True)
    dec_gross_margin = fields.Float(compute="compute_value",store=True)
    dec_gp = fields.Float(compute="compute_value",store=True)

    total_sales_volume = fields.Float(compute="compute_value",store=True)
    total_sales_value = fields.Float(compute="compute_value",store=True)
    total_cogs = fields.Float(compute="compute_value",store=True)
    total_gross_margin = fields.Float(compute="compute_value",store=True)
    total_gp = fields.Float(compute="compute_value",store=True)

    @api.depends('jan_sales_volume', 'feb_sales_volume', 'march_sales_volume', 'april_sales_volume', 'may_sales_volume',
                 'june_sales_volume', 'july_sales_volume', 'aug_sales_volume', 'sep_sales_volume', 'price_to_trade',
                 'oct_sales_volume', 'nov_sales_volume', 'dec_sales_volume', 'item_landed_cost')
    def compute_value(self):
        for record in self:
            record.jan_sales_value = record.jan_sales_volume * record.price_to_trade
            record.jan_cogs = record.jan_sales_volume * record.item_landed_cost
            record.jan_gross_margin = record.jan_sales_value - record.jan_cogs
            if record.jan_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.jan_gp = (record.jan_gross_margin / (record.jan_sales_volume * record.price_to_trade)) * 100
            else:
                record.jan_gp = 0.0
            record.feb_sales_value = record.feb_sales_volume * record.price_to_trade
            record.feb_cogs = record.feb_sales_volume * record.item_landed_cost
            record.feb_gross_margin = record.feb_sales_value - record.feb_cogs
            if record.feb_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.feb_gp = (record.feb_gross_margin / (record.feb_sales_volume * record.price_to_trade)) * 100
            else:
                record.feb_gp = 0.0
            record.march_sales_value = record.march_sales_volume * record.price_to_trade
            record.march_cogs = record.march_sales_volume * record.item_landed_cost
            record.march_gross_margin = record.march_sales_value - record.march_cogs
            if record.march_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.march_gp = (record.march_gross_margin / (record.march_sales_volume * record.price_to_trade)) * 100
            else:
                record.march_gp = 0.0
            record.april_sales_value = record.april_sales_volume * record.price_to_trade
            record.april_cogs = record.april_sales_volume * record.item_landed_cost
            record.april_gross_margin = record.april_sales_value - record.april_cogs
            if record.april_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.april_gp = (record.april_gross_margin / (record.april_sales_volume * record.price_to_trade)) * 100
            else:
                record.april_gp = 0.0
            record.may_sales_value = record.may_sales_volume * record.price_to_trade
            record.may_cogs = record.may_sales_volume * record.item_landed_cost
            record.may_gross_margin = record.may_sales_value - record.may_cogs
            if record.may_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.may_gp = (record.may_gross_margin / (record.may_sales_volume * record.price_to_trade)) * 100
            else:
                record.may_gp = 0.0
            record.june_sales_value = record.june_sales_volume * record.price_to_trade
            record.june_cogs = record.june_sales_volume * record.item_landed_cost
            record.june_gross_margin = record.june_sales_value - record.june_cogs
            if record.june_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.june_gp = (record.june_gross_margin / (record.june_sales_volume * record.price_to_trade)) * 100
            else:
                record.june_gp = 0.0
            record.july_sales_value = record.july_sales_volume * record.price_to_trade
            record.july_cogs = record.july_sales_volume * record.item_landed_cost
            record.july_gross_margin = record.july_sales_value - record.july_cogs
            if record.july_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.july_gp = (record.july_gross_margin / (record.july_sales_volume * record.price_to_trade)) * 100
            else:
                record.july_gp = 0.0
            record.aug_sales_value = record.aug_sales_volume * record.price_to_trade
            record.aug_cogs = record.aug_sales_volume * record.item_landed_cost
            record.aug_gross_margin = record.aug_sales_value - record.aug_cogs
            if record.aug_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.aug_gp = (record.aug_gross_margin / (record.aug_sales_volume * record.price_to_trade)) * 100
            else:
                record.aug_gp = 0.0
            record.sep_sales_value = record.sep_sales_volume * record.price_to_trade
            record.sep_cogs = record.sep_sales_volume * record.item_landed_cost
            record.sep_gross_margin = record.sep_sales_value - record.sep_cogs
            if record.sep_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.sep_gp = (record.sep_gross_margin / (record.sep_sales_volume * record.price_to_trade)) * 100
            else:
                record.sep_gp = 0.0
            record.oct_sales_value = record.oct_sales_volume * record.price_to_trade
            record.oct_cogs = record.oct_sales_volume * record.item_landed_cost
            record.oct_gross_margin = record.oct_sales_value - record.oct_cogs
            if record.oct_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.oct_gp = (record.oct_gross_margin / (record.oct_sales_volume * record.price_to_trade)) * 100
            else:
                record.oct_gp = 0.0
            record.nov_sales_value = record.nov_sales_volume * record.price_to_trade
            record.nov_cogs = record.nov_sales_volume * record.item_landed_cost
            record.nov_gross_margin = record.nov_sales_value - record.nov_cogs
            if record.nov_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.nov_gp = (record.nov_gross_margin / (record.nov_sales_volume * record.price_to_trade)) * 100
            else:
                record.nov_gp = 0.0
            record.dec_sales_value = record.dec_sales_volume * record.price_to_trade
            record.dec_cogs = record.dec_sales_volume * record.item_landed_cost
            record.dec_gross_margin = record.dec_sales_value - record.dec_cogs
            if record.dec_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.dec_gp = (record.dec_gross_margin / (record.dec_sales_volume * record.price_to_trade)) * 100
            else:
                record.dec_gp = 0.0
            record.total_sales_volume = record.jan_sales_volume + record.feb_sales_volume + record.march_sales_volume + record.april_sales_volume + record.may_sales_volume + record.june_sales_volume + record.july_sales_volume + record.aug_sales_volume + record.sep_sales_volume + record.oct_sales_volume + record.nov_sales_volume + record.dec_sales_volume
            record.total_sales_value = record.total_sales_volume * record.price_to_trade
            record.total_cogs = record.total_sales_volume * record.item_landed_cost
            record.total_gross_margin = record.total_sales_value - record.total_cogs
            if record.total_sales_volume > 0.0 and record.price_to_trade > 0.0:
                record.total_gp = (record.total_gross_margin / (record.total_sales_volume * record.price_to_trade)) * 100
            else:
                record.total_gp = 0.0

    @api.depends('price_to_trade', 'item_landed_cost')
    def compute_gp_percentage(self):
        for record in self:
            gp_percentage = 0.0
            if record.price_to_trade > 0.0:
                gp_percentage = (record.price_to_trade - record.item_landed_cost) / record.price_to_trade * 100
            record.gp_percentage = gp_percentage

    @api.depends("product_id")
    def compute_product_type(self):
        for record in self:
            product_type = False
            if record.product_id and record.product_id.route_ids:
                if record.product_id.route_ids.filtered(lambda s: s.is_buy_route):
                    product_type = 'regular'
                elif record.product_id.route_ids.filtered(lambda s: s.is_manufacture_route):
                    product_type = 'promotion'
            record.product_type = product_type

    def action_show_details(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_sales_budget.sales_budget_line_action")
        action['domain'] = [('id', 'in', self.ids)]
        return action

    def action_pivot_details(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_sales_budget.action_sale_budget_report")
        action['domain'] = [('sales_budget_line_id', 'in', self.ids)]
        return action


# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     @api.depends_context('from_sales_budget')
#     def _compute_display_name(self):
#         if self.env.context.get('from_sales_budget'):
#             for product in self:
#                 if product.default_code:
#                     product.display_name = product.default_code
#                 else:
#                     super(ProductProduct,product)._compute_display_name()
#         else:
#             super()._compute_display_name()
#
