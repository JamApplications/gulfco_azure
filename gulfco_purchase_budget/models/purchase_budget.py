from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools.date_utils import start_of, end_of, add, subtract
from odoo.tools.misc import format_date
from odoo.exceptions import UserError



class PurchaseBudget(models.Model):
    _name = "purchase.budget"
    _description = "Purchase Budget"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'name'

    name = fields.Char('Budget Name',  required=True)
    responsible = fields.Many2one(
        comodel_name='res.users',
        string="Responsible",
        tracking=1,
        check_company=True,  required=True)
        # domain="[('contact_type','=','customer')]")
    # start_date = fields.Date()
    # end_date = fields.Date()
    start_date = fields.Date(string='Start Date', default=lambda self: self._get_default_start_date(),  required=True)
    end_date = fields.Date(string='End Date', default=lambda self: self._get_default_end_date(),  required=True)

    def _get_default_start_date(self):
        # Get the first day of the current year
        current_year = date.today().year
        return f'{current_year}-01-01'

    def _get_default_end_date(self):
        # Get the last day of the current year
        current_year = date.today().year
        return f'{current_year}-12-31'

    @api.constrains('start_date', 'end_date')
    def _check_dates_same_year(self):
        for record in self:
            if record.start_date and record.end_date:
                start_year = record.start_date.year
                end_year = record.end_date.year
                if start_year != end_year:
                    raise UserError("Period (Start Date & End Date) must be in the same year.")

    state = fields.Selection([('draft','Draft'), ('approved', 'Approved'),
                              ('done', 'Done'), ('cancel', 'Cancelled')], default='draft', string="status")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, string="Company")

    def button_confirm(self):
        self.state = 'approved'

    def button_cancel(self):
        self.state = 'cancel'


    def button_approve(self):
        self.state = 'done'

    def button_reset_draft(self):
        self.state = 'draft'


    line_ids = fields.One2many('purchase.budget.line', 'purchase_budget_id', string="Budget Lines")
    #
    def open_action_view_purchase_budget_line(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_purchase_budget.purchase_budget_line_values_action")
        # action = self.env["ir.actions.actions"]._for_xml_id("gulfco_purchase_budget.purchase_budget_line_action")
        action['domain'] = [('purchase_budget_line_id', 'in', self.line_ids.ids)]
        return action

class SalesBudgetLine(models.Model):
    _name = 'purchase.budget.line'
    _description = 'Purchase Budget Line'
    _rac_name = 'partner_id'

    purchase_budget_id = fields.Many2one('purchase.budget', string="Budget", ondelete='cascade')
    budget_line_values = fields.One2many('purchase.budget.line.values', 'purchase_budget_line_id', string="Budget Lines Values")

    start_date = fields.Date(related='purchase_budget_id.start_date', store=True)
    end_date = fields.Date(related='purchase_budget_id.end_date', store=True)

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Dep/Brand",
        required=True, change_default=True, index=True,
        tracking=1,
        check_company=True,
        domain="[('contact_type','=','supplier')]")

    # category_id = fields.Many2one('product.category')
    # lead_time_month = fields.Integer('Lead Time Month')
    lead_time_month = fields.Selection([('1','1'), ('2','2'), ('3','3'), ('4','4'), ('5','5'), ('6','6'),
                                        ('7','7'), ('8','8'), ('9','9'), ('10','10'), ('11','12'), ('11','12')],
                                       string='Lead Time Month')
    inventory_cover = fields.Selection([('1','1'), ('2','2'), ('3','3'), ('4','4'), ('5','5'), ('6','6'),
                                        ('7','7'), ('8','8'), ('9','9'), ('10','10'), ('11','12'), ('11','12')],
                                       string='Inventory Cover')
    # inventory_cover = fields.Integer('Inventory Cover')



    def get_inventory_valuation(self, inventory_date=None, product_vendor=None):
        # Get the inventory valuation as of January 1st
        # inventory_valuation = self.env['stock.quant'].open_at_date('2025-01-01')

        # action['domain'] = [('create_date', '<=', self.inventory_datetime), ('product_id.is_storable', '=', True)]
        vendor_pricelist = self.env['product.supplierinfo'].search([('partner_id', '=', product_vendor.id)])

        product_list = []
        for rec in vendor_pricelist:
            if rec.product_id:
                product_list.append(rec.product_id.id)
            else:
                product_list.append(rec.product_tmpl_id.product_variant_id.id)

        # inventory_valuation = self.env['stock.quantity.history'].with_context(self.env.context, to_date=inventory_date).open_at_date()
        inventory_valuation = self.env['stock.valuation.layer'].search([
            ('create_date', '<=', inventory_date),
            ('product_id', 'in', product_list),
            ('product_id.is_storable', '=', True)
        ])
        # return sum(valuation_records.mapped('value'))
        # print("inventory_valuation", inventory_valuation)
        # print("inventory_valuation: mapped", inventory_valuation.mapped('value'))
        # print("inventory_valuation: mapped SUM:", sum(inventory_valuation.mapped('value')))
        # total_value = [quant.quantity * quant.unit_cost for quant in inventory_valuation]
        total_value = [quant.value for quant in inventory_valuation]
        print("total_value:", total_value)
        total_value = sum(total_value)
        print("total_value sum:",total_value)

        return total_value
#

    def generate_first_day_of_month(self,  month):
        # Create a datetime object for the first day of the specified month and year
        year = datetime.now().year
        return datetime(year, month,  day=1)

    def action_show_details(self):
        self.ensure_one()

        print("Start Date and month :", self, self.start_date, self.start_date.month)

        # month_list = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
        # month_list = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        start_month = self.start_date.month
        end_month = self.end_date.month

        # List to store the result
        result_months = []

        # If the year is the same
        if self.start_date.year == self.end_date.year:
            for month in range(start_month, end_month + 1):
                result_months.append(str(month).zfill(2))  # Add leading zero if necessary

        # If the years are different, you'll need to include months from the start year to the end year
        else:
            for month in range(start_month, 13):  # Months from start month to December
                result_months.append(str(month).zfill(2))
            for month in range(1, end_month + 1):  # Months from January to the end month
                result_months.append(str(month).zfill(2))

        # month_list = result_months
        # description_list = ['opening_stock', 'order', 'arrival', 'sales', 'closing_stock', 'mos']
        description_list = ['A_opening_stock', 'B_order', 'C_arrival', 'D_sales', 'E_closing_stock', 'F_mos']
        budget_line_list = []
        if not self.budget_line_values:
            # for month in month_list:
            for month in result_months:

                # if len(self.lead_time_month) > 1:
                #     lead_month = self.lead_time_month
                # else:
                #     lead_month = '0' + self.lead_time_month
                inventory_date = self.generate_first_day_of_month(int(start_month))
                # inventory_date = self.generate_first_day_of_month(int(lead_month))
                print("inventory_date:", inventory_date, type(inventory_date))
                # product_category = self.category_id.id
                product_vendor = self.partner_id
                value_at_date = self.get_inventory_valuation(inventory_date, product_vendor)

                print("value_at_date:", value_at_date)
                # raise ValidationError("kjhg:%s",value_at_date)
                for desc in description_list:
                    vals  = {
                        'name': self.purchase_budget_id.name,
                        'purchase_budget_line_id': self.id,
                        'description': desc,
                        'month': month,
                        'value': 0
                    }
                    if desc == 'A_opening_stock': # and month in result_months:
                        vals['value'] = value_at_date if value_at_date else 0.0
                    # if month not in result_months:
                    #     vals['value'] = 0.0

                    line_vals = self.env['purchase.budget.line.values'].sudo().create(vals)
                    budget_line_list.append(line_vals.id)
            self.budget_line_values = [(6,0, budget_line_list)]
        self.budget_line_values._get_values_per_month()

        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_purchase_budget.purchase_budget_line_values_action")
        # action = self.env["ir.actions.actions"]._for_xml_id("gulfco_purchase_budget.purchase_budget_line_action")
        # action['domain'] = [('id', 'in', self.ids)]
        action['domain'] = [('purchase_budget_line_id', 'in', self.ids)]
        return action
#
#
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
