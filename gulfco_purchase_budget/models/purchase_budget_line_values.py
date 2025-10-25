from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from datetime import datetime, timedelta, date
import calendar
from dateutil.relativedelta import relativedelta
from odoo.tools.date_utils import start_of, end_of, add, subtract
from odoo.tools.misc import format_date
from odoo.exceptions import UserError



class PurchaseBudgetLineValues(models.Model):
    _name = "purchase.budget.line.values"
    _description = "Purchase Budget Line Values"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id asc'
    _rec_name = 'name'

    name = fields.Char('Budget Name')
    purchase_budget_line_id = fields.Many2one('purchase.budget.line', string="Budget line", ondelete='cascade')

    partner_id = fields.Many2one(comodel_name='res.partner',related='purchase_budget_line_id.partner_id', store=True, string="Dep/Brand")
    # category_id = fields.Many2one(comodel_name='product.category',related='purchase_budget_line_id.category_id', store=True)
    lead_time_month = fields.Selection(related='purchase_budget_line_id.lead_time_month', store=True, string="Lead Time Month")
    inventory_cover = fields.Selection(related='purchase_budget_line_id.inventory_cover', store=True, string="Inventory Cover")

    # description = fields.Selection([
    #     ('opening_stock', 'Opening Stock'),
    #     ('order', 'Order'),
    #     ('arrival', 'Arrival'),
    #     ('sales', 'Sales'),
    #     ('closing_stock', 'Closing Stock'),
    #     ('mos', 'MOS')
    # ], string='Description')
    description = fields.Selection([
        ('A_opening_stock', 'Opening Stock'),
        ('B_order', 'Order'),
        ('C_arrival', 'Arrival'),
        ('D_sales', 'Sales'),
        ('E_closing_stock', 'Closing Stock'),
        ('F_mos', 'MOS')
    ], string='Description')
    # month = fields.Selection([
    #     ('jan', 'January'), ('feb', 'February'), ('mar', 'March'), ('apr', 'April'),
    #     ('may', 'May'), ('jun', 'June'), ('jul', 'July'), ('aug', 'August'),
    #     ('sep', 'September'), ('oct', 'October'), ('nov', 'November'), ('dec', 'December')
    # ], string='Month')
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Month')
    value = fields.Float(string='Value',)

    start_date = fields.Date(related='purchase_budget_line_id.start_date', store=True)
    end_date = fields.Date(related='purchase_budget_line_id.end_date', store=True)



    def get_opening_stock_on_month(self, month):
        # print("month:", month)
        opening_stock = self.filtered(lambda l: l.month == month and l.description == 'A_opening_stock')
        return opening_stock.value

    def get_sum_of_sales(self, month, inventory_cover=None):
        # print("month:", month)
        start_value = month
        list_of_month = [start_value]
        start_num = int(start_value)
        # if inventory_cover:
        #     month = inventory_cover
        for i in range(1, inventory_cover + 1):
            # Create the new value by incrementing the starting number
            new_value = f"{start_num + i:02}"
            list_of_month.append(new_value)
        # print("lsiyt of month:", list_of_month)
        average_month = self.filtered(lambda l: l.month in list_of_month and l.description == 'D_sales').mapped('value')
        return sum(average_month)

    def get_closting_stock_value(self, month=None):
        opening_stock = self.filtered(lambda l: l.month == month and l.description == 'A_opening_stock')
        arrival = self.filtered(lambda l: l.month == month and l.description == 'C_arrival')
        sales = self.filtered(lambda l: l.month == month and l.description == 'D_sales')
        closing_stock = opening_stock.value + arrival.value - sales.value
        return closing_stock

    def get_mos_value(self, month=None, inventory_cover=None):
        closing_stock = self.filtered(lambda l: l.month == month and l.description == 'E_closing_stock')

        list_od_month = []
        current_month = int(month)
        next_month = [f"{current_month + i + 1:02}" for i in range(inventory_cover)]
        record_month_sale = self.filtered(lambda l: l.month in next_month and l.description == 'D_sales')
        # print('record:', record_month_sale)
        # print('len:', len(record_month_sale))
        # print('sum:', sum(record_month_sale.mapped('value')))
        if record_month_sale:
            average_sale = sum(record_month_sale.mapped('value'))/len(record_month_sale)
        else:
            average_sale = 0
        if average_sale:
            mos = closing_stock.value / average_sale
        else:
            mos = 0
        return mos

    def _get_last_month_opening_stock(self, month):
        current_month = int(month) - 1

        current_month = str(current_month)
        last_month = 0
        if len(current_month) > 1:
            last_month = current_month
        else:
            last_month = '0' + current_month

        opening_stock = self.filtered(lambda l: l.month == last_month and l.description == 'E_closing_stock')
        return opening_stock.value or 0

    # def get_sum_of_sales_lead_time_four(self, month=None, lead_time_month=None, inventory_cover=None):
    def get_sum_of_sales_lead_time_month(self, month=None, lead_time_month=None, inventory_cover=None):
        # inventory_cover = inventory_cover
        # month_updated = int(month) + int(inventory_cover)
        # list_of_month = []
        # for i in range(0, lead_time_month):
        #     # Create the new value by incrementing the starting number
        #     new_value = f"{month_updated + i:02}"
        #     list_of_month.append(new_value)
        # print("lsiyt of month:", list_of_month)
        lead_time_month = lead_time_month - 1 + int(month)
        if len(str(lead_time_month)) > 1:
            actual_month = month + str(lead_time_month)
        else:
            actual_month = '0' + str(lead_time_month)

        # inventory_cover = inventory_cover
        # month_updated = int(actual_month) + int(inventory_cover)
        month_updated = int(actual_month)
        list_of_month = []
        for i in range(0, inventory_cover + 1):
            # Create the new value by incrementing the starting number
            new_value = f"{month_updated + i:02}"
            list_of_month.append(new_value)
        # print("lsiyt of month:", list_of_month)

        average_month = self.filtered(lambda l: l.month in list_of_month and l.description == 'D_sales').mapped('value')
        return sum(average_month)


    def get_arrival_values_on_month(self, month=None):
        year = datetime.now().year
        month = int(month)
        start_datetime = datetime(year, int(month), 1, 0, 0, 0)
        last_day = calendar.monthrange(year, int(month))[1]
        end_datetime = datetime(year, int(month), last_day, 23, 59, 59)

        po_line = self.env['purchase.order.line'].search([('date_planned', '>=', start_datetime),
                                                          ('date_planned', '<=', end_datetime),
                                                          ('partner_id', '=', self.partner_id.id),
                                                          ('state', 'in', ['purchase', 'done'])])
        total_arrival = 0
        for rec in po_line:
            total_arrival += (rec.product_qty - rec.qty_received) * rec.price_unit
        return total_arrival


    # def _compute_values_per_month(self):
    def _get_values_per_month(self):
        first_month = True
        for rec in self:

            # if rec.lead_time_month == '1':
            if rec.description in ['B_order']:
                month_count = int(rec.lead_time_month) + int(rec.month) -1
                # print("month_count:", month_count, str(month_count))
                actual_month = str(month_count)
                if len(actual_month) > 1:
                    actual_month = actual_month
                else:
                    actual_month = '0' + actual_month

                # opening_stock = self.get_opening_stock_on_month(rec.month)

                opening_stock = self.get_opening_stock_on_month(actual_month)
                # sum_of_sales = self.get_sum_of_sales(rec.month, int(rec.inventory_cover))
                sum_of_sales = self.get_sum_of_sales_lead_time_month(rec.month, int(rec.lead_time_month), int(rec.inventory_cover))
                rec.value = sum_of_sales - abs(opening_stock)

            elif rec.description in ['C_arrival']:
                arrival = self.get_arrival_values_on_month(month=rec.month)
                rec.value = arrival

            elif rec.description in ['E_closing_stock']:
                closing_stock = self.get_closting_stock_value(rec.month)
                rec.value = closing_stock

            elif rec.description in ['F_mos']:
                mos = self.get_mos_value(rec.month, int(rec.inventory_cover))
                rec.value = mos

            elif rec.description in ['A_opening_stock']:
                # print("If A _opeming stock ,month::", rec.month)
                # if rec.month == '01':
                if first_month:
                    first_month = False
                else:
                    rec.value = self._get_last_month_opening_stock(rec.month)

            # elif rec.lead_time_month == '4':
            #
            #     if rec.description in ['A_opening_stock']:
            #         print("If A _opeming stock ,month::", rec.month)
            #
            #     if rec.description in ['B_order']:
            #         month_count = int(rec.month) + int(rec.inventory_cover)
            #         print("month_count:", month_count, str(month_count))
            #         actual_month = str(month_count)
            #         if len(str(actual_month)) > 1:
            #             actual_month = actual_month
            #         else:
            #             actual_month = '0' + actual_month
            #
            #         opening_stock = self.get_opening_stock_on_month(actual_month)
            #         sum_of_sales = self.get_sum_of_sales_lead_time_four(rec.month, int(rec.lead_time_month), int(rec.inventory_cover))
            #         rec.value = sum_of_sales - opening_stock
            #
            #     elif rec.description in ['E_closing_stock']:
            #         closing_stock = self.get_closting_stock_value(rec.month)
            #         rec.value = closing_stock
            #
            #     elif rec.description in ['F_mos']:
            #         mos = self.get_mos_value(rec.month, int(rec.inventory_cover))
            #         rec.value = mos
            #
            #     elif rec.description in ['A_opening_stock']:
            #         print("If A _opeming stock ,month::", rec.month)
            #         if rec.month != '01':
            #             rec.value = self._get_last_month_opening_stock(rec.month)





            # else:
            #     rec.value = rec.value
        # for rec in self.purchase_budget_line_id.budget_line_values:

    #         print("rec:", rec)
            # if rec.lead_time_month == 1:
            #     if rec.description in ['A_opening_stock']:
            #         rec.value = rec.value
            #     elif rec.description in ['B_order', 'C_arrival']:
            #         order = 0
            #         # for budget_line in rec.purchase_budget_line_id.budget_line_values:
            #             if budget_line.month == '01':
            #                 opening_stock = budget_line.value
            #             if budget_line.month in ['01', '02', '03']:
            #                 avg_sale = budget_line.value
            #
            #
            #         rec.value = order
            # else:
            #     if rec.description in ['A_opening_stock']:
            #         rec.value = rec.value
            #     elif rec.description in ['B_order', 'C_arrival']:
            #         rec.value = rec.value
            #     else:
            #         rec.value = rec.value
            #


    @api.onchange('value')
    def onchange_values_recalculate(self):
        data = self.purchase_budget_line_id.budget_line_values
        data._get_values_per_month()


    # # ----------------List /Kanban View Data-----------------
    # # JAN-------------
    # jan_opening_stock = fields.Float('Opening Stock')
    # jan_order = fields.Float('Order')
    # jan_arrival = fields.Float('Arrival')
    # jan_sales = fields.Float('Sales')
    # jan_closing_stock = fields.Float('Closing Stock')
    # jan_mos = fields.Float('MOS')
    #
    # # feb-------------
    # feb_opening_stock = fields.Float('Opening Stock')
    # feb_order = fields.Float('Order')
    # feb_arrival = fields.Float('Arrival')
    # feb_sales = fields.Float('Sales')
    # feb_closing_stock = fields.Float('Closing Stock')
    # feb_mos = fields.Float('MOS')
    #
    # # march-------------
    # march_opening_stock = fields.Float('Opening Stock')
    # march_order = fields.Float('Order')
    # march_arrival = fields.Float('Arrival')
    # march_sales = fields.Float('Sales')
    # march_closing_stock = fields.Float('Closing Stock')
    # march_mos = fields.Float('MOS')
    #
    # # april-------------
    # april_opening_stock = fields.Float('Opening Stock')
    # april_order = fields.Float('Order')
    # april_arrival = fields.Float('Arrival')
    # april_sales = fields.Float('Sales')
    # april_closing_stock = fields.Float('Closing Stock')
    # april_mos = fields.Float('MOS')
    #
    # # may------------
    # may_opening_stock = fields.Float('Opening Stock')
    # may_order = fields.Float('Order')
    # may_arrival = fields.Float('Arrival')
    # may_sales = fields.Float('Sales')
    # may_closing_stock = fields.Float('Closing Stock')
    # may_mos = fields.Float('MOS')
    #
    # # june-------------
    # june_opening_stock = fields.Float('Opening Stock')
    # june_order = fields.Float('Order')
    # june_arrival = fields.Float('Arrival')
    # june_sales = fields.Float('Sales')
    # june_closing_stock = fields.Float('Closing Stock')
    # june_mos = fields.Float('MOS')
    #
    # # july-------------
    # july_opening_stock = fields.Float('Opening Stock')
    # july_order = fields.Float('Order')
    # july_arrival = fields.Float('Arrival')
    # july_sales = fields.Float('Sales')
    # july_closing_stock = fields.Float('Closing Stock')
    # july_mos = fields.Float('MOS')
    #
    # # aug-------------
    # aug_opening_stock = fields.Float('Opening Stock')
    # aug_order = fields.Float('Order')
    # aug_arrival = fields.Float('Arrival')
    # aug_sales = fields.Float('Sales')
    # aug_closing_stock = fields.Float('Closing Stock')
    # aug_mos = fields.Float('MOS')
    #
    # # sep_-------------
    # sep_opening_stock = fields.Float('Opening Stock')
    # sep_order = fields.Float('Order')
    # sep_arrival = fields.Float('Arrival')
    # sep_sales = fields.Float('Sales')
    # sep_closing_stock = fields.Float('Closing Stock')
    # sep_mos = fields.Float('MOS')
    #
    # # oct_-------------
    # oct_opening_stock = fields.Float('Opening Stock')
    # oct_order = fields.Float('Order')
    # oct_arrival = fields.Float('Arrival')
    # oct_sales = fields.Float('Sales')
    # oct_closing_stock = fields.Float('Closing Stock')
    # oct_mos = fields.Float('MOS')
    #
    # # nov_-------------
    # nov_opening_stock = fields.Float('Opening Stock')
    # nov_order = fields.Float('Order')
    # nov_arrival = fields.Float('Arrival')
    # nov_sales = fields.Float('Sales')
    # nov_closing_stock = fields.Float('Closing Stock')
    # nov_mos = fields.Float('MOS')
    #
    # # dec_-------------
    # dec_opening_stock = fields.Float('Opening Stock')
    # dec_order = fields.Float('Order')
    # dec_arrival = fields.Float('Arrival')
    # dec_sales = fields.Float('Sales')
    # dec_closing_stock = fields.Float('Closing Stock')
    # dec_mos = fields.Float('MOS')

    # #
    # opening_stock = fields.Float('Opening Stock')
    # order = fields.Float('Order')
    # arrival = fields.Float('Arrival')
    # sales = fields.Float('Sales')
    # closing_stock = fields.Float('Closing Stock')
    # mos = fields.Float('MOS')

