from odoo import _, api, fields, models
from datetime import datetime, date
from odoo.tools.misc import OrderedSet
from odoo.tools import html2plaintext, html_sanitize
from odoo.exceptions import UserError
import base64
import io
import xlsxwriter
import os


class StockInventoryAdjustment(models.Model):
    _name = "stock.inventory.adjustment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Stock Inventory Adjustment"
    _rec_name = 'inventory_ref'

    _sql_constraints = [('inventory_ref_unique', 'unique(inventory_ref, company_id)', 'Inventory Ref already Exist.')]

    type = fields.Selection(
        [('surprise', 'Surprise'), ('annual', 'Annual'), ('internal', 'Internal'), ('spot', 'Spot')], string="Type",
        default='surprise')
    # start_time = fields.Datetime(string="Start Time")
    # end_time = fields.Datetime(string="End Time")
    # duration = fields.Float(string="Duration")
    adjustment_criteria = fields.Selection([
        ('brand', 'Brand Wise'),
        ('principal', 'Principal Wise')
    ], string="Adjustment Criteria", tracking=True)
    brand_id = fields.Many2one('product.brand')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True)

    location_id = fields.Many2one('stock.location', 'WH Name & Locator',
                                  domain="[('company_id', '=', company_id), ('warehouse_id', '=', warehouse_id), ('usage', 'in', ['internal', 'transit'])]")
    sale_team_id = fields.Many2one('crm.team', string="Committee")
    performed_by = fields.Many2one('res.users', string="Stock Count Performed by", default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('counting_done', 'Counting Done'),
                              ('under_ssc_review', 'Under SSC Review'),
                              ('under_scm_review', 'Under SCM Review'),
                              ('director_approved', 'Director Approved'),
                              ('finance_approved', 'Finance Approved'), ('scd_approved', 'SCD Approved'),
                              ('validated', 'Validated')],
                             default='draft',tracking=True)
    inventory_ref = fields.Char(string="Inventory Ref",copy=False)
    inventory_date = fields.Datetime(string="Inventory Date", default=lambda self: fields.Datetime.now())
    custodian_details = fields.Text(string="Custodian Details")
    line_ids = fields.One2many('inventory.adjustment.line', 'inventory_adjustment_id', string="Inventory Line")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    scm_comments = fields.Text(string="SCM Comments")
    director_reject_reason = fields.Char(string='Director Reject Reason')
    finance_reject_reason = fields.Char(string='Finance Reject Reason')
    sdm_reject_reason = fields.Char(string='SDM Reject Reason')
    dest_location_id = fields.Many2one('stock.location',
                                       domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]")
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        domain="[('code', '=', 'internal'), ('company_id', '=', company_id)]")
    internal_picking_id = fields.Many2one('stock.picking', string="Internal Transfer")
    gl_journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('type', '=', 'general'),('company_id', '=', company_id)]"
    )

    # state = fields.Selection([('')])

    # def action_start_time(self):
    #     self.start_time = datetime.now()
    #
    # def action_end_time(self):
    #     self.end_time = datetime.now()
    #     if self.end_time and self.start_time:
    #         duration = (self.end_time - self.start_time).total_seconds() / 3600
    #         self.duration = round(duration, 2)

    @api.onchange('type', 'location_id')
    def _onchange_type_location(self):
        if self.line_ids and self.type == 'internal' and self.location_id:
            self.line_ids.location_id = self.location_id.id

    def action_start_inventory(self):
        self.state = 'in_progress'
        for inventory in self:
            vals = {
                'state': 'in_progress'
            }
            if inventory.line_ids:
                inventory.line_ids.unlink()  # remove previous lines

            inventory.line_ids = [(0, 0, val) for val in inventory._get_inventory_lines_values()]
            inventory.write(vals)


    def action_end_count(self):
        self.state = 'counting_done'

    def action_submit_report(self):
        self.state = 'under_ssc_review'
        # inventory_users = self.env.ref('stock.group_stock_user').users
        # for user in inventory_users:
        #     self.activity_schedule(
        #         'mail.mail_activity_data_todo',
        #         note='Please Check Inventory Adjustment it submitted',
        #         user_id=user.id)

    def action_confirm(self):
        self.state = 'under_scm_review'
        # inventory_users = self.env.ref('stock.group_stock_manager').users
        # for user in inventory_users:
        #     self.activity_schedule(
        #         'mail.mail_activity_data_todo',
        #         note='Please Check Inventory Adjustment Is Confimed and validate Validate',
        #         user_id=user.id)

    def action_validate(self):
        self.state = 'validated'
        if self.type != 'internal':
            for line in self.line_ids:
                if line.quant_id and line.counted_qty != 0.0:
                    line.quant_id.sudo().write({'inventory_quantity': line.counted_qty})
                    line.quant_id.sudo().action_apply_inventory()
            # director_approvals = self.env.ref('stock_inventory_adjustment.group_director_approval').users
            # for user in director_approvals:
            #     self.activity_schedule(
            #         'mail.mail_activity_data_todo',
            #         note='Inventory Adjustment is Validated Need to Director Approve',
            #         user_id=user.id)
        else:
            picking_vals = {
                'picking_type_id': self.picking_type_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.dest_location_id.id,
                'move_type': 'direct',
                'company_id': self.company_id.id,
                'gl_journal_id': self.gl_journal_id.id
            }
            picking = self.env['stock.picking'].create(picking_vals)
            for line in self.line_ids:
                move_vals = {
                    'picking_id': picking.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.counted_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.dest_location_id.id,
                    'name': 'Internal Transfer of {}'.format(line.product_id.name),
                    'company_id': self.company_id.id
                }
                move = self.env['stock.move'].create(move_vals)
            picking.action_confirm()
            picking.action_assign()
            picking.with_context(skip_backorder=True).button_validate()
            self.write({'internal_picking_id': picking.id})

    def action_view_internal_picking(self):
        if self.internal_picking_id:
            action = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_internal')
            action['context'] = {
                'search_default_picking_type_id': [self.id],
                'default_picking_type_id': self.id,
                'default_company_id': self.company_id.id,
            }
            action['domain'] = [('id', '=', self.internal_picking_id.id)]
            return action
        else:
            raise UserError('Internal Picking not created')

    def _get_inventory_lines_values(self):
        self.ensure_one()
        Product = self.env['product.product']

        vals = []

        # Required warehouse location
        warehouse_loc = self.warehouse_id.view_location_id
        location_domain = [('location_id', 'child_of', warehouse_loc.id)]

        if self.location_id:
            location_domain = [('location_id', 'child_of', self.location_id.id)]

        product_domain = [('product_tmpl_id.active', '=', True)]

        if self.adjustment_criteria == 'brand':
            product_domain += [('product_tmpl_id.brand_id', '=', self.brand_id.id)]

        elif self.adjustment_criteria == 'principal':
            principal_vendors = self.env['res.partner'].search([
                ('supplier_rank', '>', 0),
                ('contact_type', '=', 'supplier'),
                ('supplier_classification_id.is_filtered', '=', True)
            ])
            if not principal_vendors:
                return []

            product_domain += [('seller_ids.partner_id', 'in', principal_vendors.ids)]

        product_ids = Product.search(product_domain).ids
        location_ids = self.env['stock.location'].search(location_domain).ids

        if not product_ids or not location_ids:
            return []

        # Final SQL Query
        sql = """
            SELECT 
                sq.product_id,
                sq.location_id,
                sq.lot_id,
                SUM(sq.quantity) as quantity,
                sq.id as quant_id
            FROM stock_quant sq
            LEFT JOIN product_product pp ON pp.id = sq.product_id
            WHERE sq.location_id = ANY(%s)
              AND sq.product_id = ANY(%s)
              AND sq.quantity != 0
              AND pp.active
        """
        params = [location_ids, product_ids]

        if self.company_id:
            sql += " AND company_id = %s"
            params.append(self.company_id.id)

        sql += " GROUP BY product_id, location_id, lot_id,sq.id"

        self.env.cr.execute(sql, params)
        results = self.env.cr.dictfetchall()

        seen_keys = set()
        lot_list = []
        for rec in results:
            key = (rec['product_id'], rec['location_id'],
                   rec['lot_id'] or 0)  # or drop location if you don't want per-location
            if key in seen_keys:
                continue
            seen_keys.add(key)

            lot = self.env['stock.lot'].browse(rec['lot_id']) if rec['lot_id'] else False
            if lot in lot_list:
                pass
            else:
                vals.append({
                    'product_id': rec['product_id'],
                    'location_id': rec['location_id'],
                    'on_hand_qty': rec['quantity'],
                    'lot_id': rec['lot_id'],
                    'expiry_date': lot.expiration_date if lot and lot.expiration_date else False,
                    'inventory_adjustment_id': self.id,
                    'quant_id':rec['quant_id']
                })
                lot_list.append(lot)


        return vals

    # def _get_inventory_lines_values(self):
    #     locations = self.env['stock.location'].search([('id', 'child_of', self.location_id.ids)])
    #     domain = ' sq.location_id in %s AND sq.quantity != 0 AND pp.active'
    #     args = (tuple(locations.ids),)
    #     vals = []
    #     if self.company_id:
    #         domain += ' AND sq.company_id = %s'
    #         args += (self.company_id.id,)
    #     self.env.cr.execute("""SELECT sq.id as quant_id ,sq.product_id, sum(sq.quantity) as on_hand_qty, sq.location_id, sq.lot_id as lot_id
    #         FROM stock_quant sq
    #         LEFT JOIN product_product pp
    #         ON pp.id = sq.product_id
    #         WHERE %s
    #         GROUP BY sq.id,sq.product_id, sq.location_id, sq.lot_id, sq.package_id, sq.owner_id """ % domain, args)
    #     for product_data in self.env.cr.dictfetchall():
    #         if 'lot_id' in product_data and product_data.get('lot_id'):
    #             lot = self.env['stock.lot'].browse(product_data.get('lot_id'))
    #             if lot.expiration_date:
    #                 product_data['expiry_date'] = lot.expiration_date
    #         product_data['inventory_adjustment_id'] = self.id
    #         for void_field in [item[0] for item in product_data.items() if item[1] is None]:
    #             product_data[void_field] = False
    #         vals.append(product_data)
    #     return vals

    def action_director_approvals(self):
        self.state = 'director_approved'
        # director_approvals = self.env.ref('stock_inventory_adjustment.group_director_approval').users
        # for user in director_approvals:
        #     activity_id = self.env['mail.activity'].search([
        #         ('res_id', '=', self.id), ('user_id', '=', user.ids),
        #         ('res_model_id', '=',
        #          self.env.ref('stock_inventory_adjustment.model_stock_inventory_adjustment').id),
        #     ])
        #     activity_id.action_done()
        # finance_approvals = self.env.ref('account.group_account_manager').users
        # for user in finance_approvals:
        #     self.activity_schedule(
        #         'mail.mail_activity_data_todo',
        #         note='Inventory Adjustment is Director Approve Need to Finance Approve',
        #         user_id=user.id)

    def action_director_reject(self):
        return {
            'name': _('Rejection Reason'),
            'res_model': 'reject.reason',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_inventory_adjustment_id': self.id, 'from_director': 1}

        }

    def action_finance_approvals(self):
        self.state = 'finance_approved'
        # finance_approvals = self.env.ref('account.group_account_manager').users
        # for user in finance_approvals:
        #     activity_id = self.env['mail.activity'].search([
        #         ('res_id', '=', self.id), ('user_id', '=', user.ids),
        #         ('res_model_id', '=',
        #          self.env.ref('stock_inventory_adjustment.model_stock_inventory_adjustment').id),
        #     ])
        #     activity_id.action_done()
        # scd_approvals = self.env.ref('stock_inventory_adjustment.group_scd_approval').users
        # for user in scd_approvals:
        #     self.activity_schedule(
        #         'mail.mail_activity_data_todo',
        #         note='Inventory Adjustment is Finance Approved Need to SCD Approve',
        #         user_id=user.id)

    def action_finance_reject(self):
        return {
            'name': _('Rejection Reason'),
            'res_model': 'reject.reason',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_inventory_adjustment_id': self.id, 'from_finance': 1}

        }

    def action_scd_approvals(self):
        self.state = 'scd_approved'
        # scd_approvals = self.env.ref('stock_inventory_adjustment.group_scd_approval').users
        # for user in scd_approvals:
        #     activity_id = self.env['mail.activity'].search([
        #         ('res_id', '=', self.id), ('user_id', '=', user.ids),
        #         ('res_model_id', '=',
        #          self.env.ref('stock_inventory_adjustment.model_stock_inventory_adjustment').id),
        #     ])
        #     activity_id.action_done()

    def action_scd_reject(self):
        return {
            'name': _('Rejection Reason'),
            'res_model': 'reject.reason',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_inventory_adjustment_id': self.id, 'from_sdm': 1}

        }

    def action_discrepancy_report(self):
        return {
            'name': _('Discrepancy Report'),
            'view_mode': 'list',
            'domain': [('id', 'in', self.line_ids.ids)],
            'res_model': 'inventory.adjustment.line',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
        }


class InventoryAdjustmentLine(models.Model):
    _name = "inventory.adjustment.line"
    _description = 'Inventory Adjustment Line'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Item Name")
    location_id = fields.Many2one('stock.location', 'Location')
    product_default_code = fields.Char(related="product_id.default_code", store=True, string="Item Code")
    on_hand_qty = fields.Float('On-Hand Qty', default=0.0, digits="Product Unit of Measure",
                               related=False)
    lot_id = fields.Many2one('stock.lot', string="Lot Number")
    internal_ref_lot = fields.Char(related="lot_id.ref", store=True, string="Internal Ref (Lot)")
    expiry_date = fields.Date(string="Expiry Date")
    product_uom_id = fields.Many2one('uom.uom', string='UOM', related='product_id.uom_id')
    counted_qty = fields.Float(default=0.0, digits="Product Unit of Measure", string="Counted Qty")
    difference_qty = fields.Float(string="Difference", digits="Product Unit of Measure", compute="_compute_difference")
    inventory_adjustment_id = fields.Many2one('stock.inventory.adjustment', string="Inventory Adjustment")
    company_id = fields.Many2one('res.company', related="inventory_adjustment_id.company_id", store=True)
    quant_id = fields.Many2one('stock.quant', string="Quant")

    @api.depends('counted_qty', 'on_hand_qty')
    def _compute_difference(self):
        for line in self:
            line.difference_qty = line.counted_qty - line.on_hand_qty

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id and self.inventory_adjustment_id.location_id:
            product_list = self.product_id.with_context(to_date=date.today()).read(
                [
                    'qty_available',
                ])
            if len(product_list) > 0:
                self.on_hand_qty = product_list[0]['qty_available']

    @api.onchange('lot_id')
    def onchange_lot_id(self):
        if self.lot_id and self.lot_id.expiration_date:
            if self.lot_id.expiration_date:
                self.expiry_date = self.lot_id.expiration_date
            else:
                self.expiry_date = False

    @api.model_create_multi
    def create(self, vals_list):
        res = super(InventoryAdjustmentLine, self).create(vals_list)
        for line in res:
            if line.inventory_adjustment_id.type == 'internal':
                if line.inventory_adjustment_id.location_id:
                    line.location_id = line.inventory_adjustment_id.location_id.id
        return res

    def action_print_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        worksheet = workbook.add_worksheet("Discrepancy Report")

        bold = workbook.add_format({'bold': True})
        border = workbook.add_format({'border': 1})
        center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        text_format = workbook.add_format({
            'font_name': 'Calibri',
            'font_size': 11,
            'align': 'left',
            'valign': 'top'
        })
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        inventory = self.mapped('inventory_adjustment_id')
        inventory_date = ''
        if inventory[0].inventory_date:
            inventory_date = inventory[0].inventory_date.strftime("%Y-%m-%d")

        worksheet.merge_range('A1:H1', "Discrepancy Report", header_format)
        worksheet.write('A2', "Inventory Adjustment Name", bold)
        worksheet.write('B2', inventory[0].inventory_ref)
        worksheet.write('A3', "Inventory Date", bold)
        worksheet.write('B3', inventory_date)
        worksheet.write('A4', "Inventory Type", bold)
        worksheet.write('B4', inventory[0].type)
        worksheet.write('A5', "Condition End Time & Date", bold)
        worksheet.write('B5', inventory_date)
        worksheet.write('A6', "Inventory Location", bold)
        worksheet.write('B6', inventory[0].location_id.name)
        worksheet.write('A7', "User", bold)
        worksheet.write('B7', inventory[0].performed_by.name)
        headers = [
            "Item Code", "Item Name", "Lot Number", "Internal Lot Ref",
            "Expiry Date", "On-Hand Quantity", "Counted Quantity", "Difference"
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(8, col_num, header, header_format)
        data = []
        for record in self:
            expiry_date = ''
            if record.expiry_date:
                expiry_date = record.expiry_date.strftime("%Y-%m-%d")
            data.append({'product_default_code': record.product_default_code, 'product_id': record.product_id.name,
                         'lot_id': record.lot_id.name, 'internal_ref_lot': record.internal_ref_lot,
                         'expiry_date': expiry_date, 'on_hand_qty': record.on_hand_qty,
                         'counted_qty': record.counted_qty, 'difference_qty': record.difference_qty})
        row = 9
        for record in data:
            for col, key in enumerate(record):
                if isinstance(record.get(key), (int, float)):
                    worksheet.write(row, col, record.get(key) or '', number_format)
                else:
                    worksheet.write(row, col, record.get(key) or '')
            row += 1
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:H', 15)
        workbook.close()
        output.seek(0)
        # generated_file = output.read()
        xlsx_data = base64.b64encode(output.read())
        output.close()
        # return {
        #     'file_name': 'profit_loss_comparison.xlsx',
        #     'file_content': generated_file,
        #     'file_type': 'xlsx',
        # }
        attachment = self.env['ir.attachment'].create({
            'name': 'Discrepancy_Report.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': 'inventory.adjustment.line',
            'res_id': self.inventory_adjustment_id.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
