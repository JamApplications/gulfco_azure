from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import math
import io
import zipfile
import base64
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    status_label = fields.Char(string="Status", compute="_compute_status_label", store=True)
    reserved_quantity = fields.Float(string="Reserved Quantity")
    product_packaging_qty = fields.Float('Packaging Quantity')


    @api.depends('state', 'picking_id', 'picking_id.picking_type_id')
    def _compute_status_label(self):
        for move in self:
            label = dict(self._fields['state'].selection).get(move.state, move.state)
            if move.state == 'assigned':
                if 'Pick' in (move.picking_id.picking_type_id.name or ''):
                    label = 'Ready to Pick'
                elif 'Pack' in (move.picking_type_id.name or ''):
                    label = 'Ready to Pack'
                elif 'Delivery' in (move.picking_id.picking_type_id.name or ''):
                    label = 'Loaded & dispatched & Ready to deliver'
            elif move.state == 'done':
                if 'Pick' in (move.picking_id.picking_type_id.name or ''):
                    label = 'Picked'
                elif 'Pack' in (move.picking_id.picking_type_id.name or ''):
                    label = 'Packed'
                elif 'Delivery' in (move.picking_id.picking_type_id.name or ''):
                    label = 'Delivery Done'
            elif move.state not in ['done', 'assigned']:
                label = move.state
            if move.state == 'confirmed':
                label = 'Awaiting planning'
            move.status_label = label

    is_pick_type = fields.Boolean(related='picking_id.is_pick_type', store=True)
    forklift_partner_id = fields.Many2one('res.partner', string="Forklift", ) #related='picking_id.forklift_partner_id')
    picker_partner_id = fields.Many2one('res.partner', string="Picker",) #related='picking_id.picker_partner_id'
    picking_driver_id = fields.Many2one('res.partner', string="Driver", related='picking_id.picker_partner_id',
                                        store=True)
    picking_type_code = fields.Selection(string="Operation Type Code", related="picking_id.picking_type_code", store=True)

    brand_id = fields.Many2one('product.brand', string="Brand", related='product_id.brand_id', store=True)
    asn_request_id = fields.Many2one(
        comodel_name='asn.request',
        string='',
        related="asn_line_id.asn_request_id")
    division = fields.Selection(related="product_id.division",store=True)
    move_remark = fields.Text("Remark")
    trx_type = fields.Selection(related="picking_id.trx_type",store=True)
    # state = fields.Selection(related="picking_id.state",store=True)
    # channel = fields.Selection(related="partner_id.channel",store=True)
    partner_channel_id = fields.Many2one('channel.channel', related="partner_id.partner_channel_id", string="Channel")
    emirates_id = fields.Many2one(related="picking_id.emirates_id",store=True)
    picking_driver_id = fields.Many2one(related="picking_id.picking_driver_id",store=True)
    qty_in_case = fields.Float(string='QTY in Case', compute='_compute_qty_in_case', store=True)
    qty_in_pallet_case = fields.Float(string='Qty in Pallet', related="picking_id.qty_in_pallet_case",store=True)
    is_readonly_picker = fields.Boolean(string="Is Readonly Picker")
    is_readonly_forklift = fields.Boolean(string="Is Readonly forklift")

    @api.depends('product_uom_qty', 'product_id')
    def _compute_qty_in_case(self):
        for move in self:
            move.qty_in_case = 0.0
            if move.product_id and move.product_id.packaging_ids:
                # Get the first packaging with qty > 1 (i.e., a case)
                packaging = move.product_id.packaging_ids.filtered(lambda p: p.qty > 1)
                if packaging:
                    units_per_case = packaging[0].qty
                    move.qty_in_case = move.product_uom_qty / units_per_case if units_per_case else 0.0


    # @api.model
    # def _search(self, domain, offset=0, limit=None, order=None):
    #     if self._context.get('from_operation_details'):
    #         domain = domain.copy()
    #         domain.append((('picker_partner_id', '=', self.env.user.partner_id.id)))
    #     return super()._search(domain, offset, limit, order)

    def _update_reserved_quantity(self, need, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        if self.partner_id and self.sale_line_id:
            if self.partner_id and self.partner_id.parent_id:
                partner = self.partner_id.parent_id
            else:
                partner = self.partner_id
            return super(StockMove, self.with_context(product_shelf_partner=partner))._update_reserved_quantity(need, location_id, lot_id, package_id, owner_id, strict)
        if self.request_order_id and self.request_order_id.direction in ['van_load','branch_transfer']:
            return super(StockMove, self.with_context(stock_request_reserve_saleable=True,custom_request_order_id= self.request_order_id.id))._update_reserved_quantity(need, location_id, lot_id, package_id, owner_id, strict)
        return super()._update_reserved_quantity(need, location_id, lot_id, package_id, owner_id, strict)

    def _action_assign(self, force_qty=False):
        res = super(StockMove, self)._action_assign(force_qty=force_qty)
        for move in self:
            move.reserved_quantity = move.quantity
        return res

    def send_notification_to_picker(self):
        for record in self:
            if record.picking_id.is_pick_type and record.picking_id.delivery_required and not record.planning_status_show:
                raise ValidationError(_('This picking need to be planned first'))
            record.is_readonly_picker = True

            def assign_picker_recursive(move, picker_id):
                for dest_move in move.move_dest_ids:
                    if dest_move.picker_partner_id != picker_id:
                        dest_move.picker_partner_id = picker_id
                        assign_picker_recursive(dest_move, picker_id)

            assign_picker_recursive(record, record.picker_partner_id)


            template = self.env.ref('stock_outbouding_operation.email_template_picker_parsion_assigned')
            if template:
                template.with_context(partner=record.picker_partner_id).send_mail(record.id,
                                                                                 force_send=True,
                                                                                 email_values={'model': False,
                                                                                               'email_to': record.picker_partner_id.email,
                                                                                               'res_id': False},
                                                                                 email_layout_xmlid='mail.mail_notification_light')

    def unassigned_picker(self):
        for record in self:
            record.is_readonly_picker = False
            record.picker_partner_id = False

    def send_notification_to_forklift(self):
        for rec in self:
            if rec.picking_id.is_pick_type and rec.picking_id.delivery_required and not rec.planning_status_show:
                raise ValidationError(_('This picking need to be planned first'))

            rec.is_readonly_forklift = True
            template = self.env.ref('stock_outbouding_operation.email_template_forklift_parsion_assigned')
            if template:
                template.with_context(partner=rec.forklift_partner_id).send_mail(rec.id,
                                                                                   force_send=True,
                                                                                   email_values={'model': False,
                                                                                   'email_to': rec.forklift_partner_id.email or (
                                                                                           rec.forklift_partner_id.email or ''),
                                                                                   'res_id': False},
                                                                     email_layout_xmlid='mail.mail_notification_light')

    def unassigned_forklift(self):
        for rec in self:
            rec.is_readonly_forklift = False
            rec.forklift_partner_id = False


    def check_availability_move_wise(self):
        moves = self.filtered(lambda move: move.state not in ('draft', 'cancel', 'done')).sorted(
            key=lambda move: (-int(move.priority), not bool(move.date_deadline), move.date_deadline, move.date, move.id)
        )
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        moves._action_assign()

    def action_put_in_pack_stock_move(self):
        out_stock_move = self.filtered(lambda s: s.picking_type_code == 'outgoing' and s.state not in ('draft','done', 'cancel'))
        if out_stock_move:
            out_move_line_ids = out_stock_move.mapped('move_line_ids').filtered(lambda ml: ml.state != 'done')
            for move_line in out_move_line_ids:
                if not move_line.location_dest_id:
                    product = move_line.product_id
                    quantity = move_line.qty_done or move_line.product_uom_qty or 1.0
                    default_dest_location = move_line._get_default_dest_location()
                    if default_dest_location:
                        location = default_dest_location._get_putaway_strategy(
                            product=product,
                            quantity=quantity,
                            package=False
                        )
                        if location:
                            move_line.location_dest_id = location.id
            pallete_package_type = self.env['stock.package.type'].search(
                [('is_pallete_package', '=', True)], limit=1
            )
            if not pallete_package_type:
                raise UserError("No pallet package type found. Please define one with 'Is Pallet Package' enabled.")
            grouped_by_location = {}
            for move_line in out_move_line_ids:
                key = move_line.location_dest_id.id
                grouped_by_location[key] = grouped_by_location.get(key, self.env['stock.move.line']) | move_line
            for location_dest_id, move_lines in grouped_by_location.items():
                package = self.env['stock.quant.package'].create({
                    'package_type_id': pallete_package_type.id,
                })
                move_lines.write({
                    'result_package_id': package.id,
                })
                for picking in move_lines.mapped('picking_id'):
                    picking_lines = move_lines.filtered(lambda ml: ml.picking_id == picking)
                    self.env['stock.package_level'].with_context(from_put_in_pack=True).create({
                        'package_id': package.id,
                        'picking_id': picking.id,
                        'location_id': picking_lines[0].location_id.id,
                        'location_dest_id': picking_lines[0].location_dest_id.id,
                        'move_line_ids': [(6, 0, picking_lines.ids)],
                        'company_id': picking.company_id.id,
                    })
            # out_product_package_types = out_move_line_ids.mapped('move_id.product_packaging_id.package_type_id')
            # for out_product_package_type in out_product_package_types:
            #     out_move_line_package_type_wise_ids = out_move_line_ids.filtered(
            #         lambda s: s.move_id.product_packaging_id.package_type_id == out_product_package_type
            #     )
            #     grouped_by_location = {}
            #     for move_line in out_move_line_package_type_wise_ids:
            #         key = move_line.location_dest_id.id
            #         # grouped_by_location.setdefault(key, self.env['stock.move.line']).add(move_line)
            #         grouped_by_location[key] = grouped_by_location.get(key, self.env['stock.move.line']) | move_line
            #
            #
            #     for location_dest_id, move_lines in grouped_by_location.items():
            #         package = self.env['stock.quant.package'].create({})
            #         if out_product_package_type:
            #             package.package_type_id = out_product_package_type
            #         move_lines.write({
            #             'result_package_id': package.id,
            #         })
            #         for picking in move_lines.mapped('picking_id'):
            #             picking_lines = move_lines.filtered(lambda ml: ml.picking_id == picking)
            #             self.env['stock.package_level'].with_context(from_put_in_pack=True).create({
            #                 'package_id': package.id,
            #                 'picking_id': picking.id,
            #                 'location_id': picking_lines[0].location_id.id,
            #                 'location_dest_id': picking_lines[0].location_dest_id.id,
            #                 'move_line_ids': [(6, 0, picking_lines.ids)],
            #                 'company_id': picking.company_id.id,
            #             })
            in_stock_moves = self.filtered(lambda s:s.picking_type_code == 'incoming' and s.state not in ('draft','done', 'cancel'))
        if in_stock_moves:
            invalid_moves = in_stock_moves.filtered(
                lambda m: not m.product_id.packaging_ids.filtered(lambda p: p.package_type_id.is_pallete_package)
            )
            if invalid_moves:
                raise UserError('Please Configure the pallete package in product master data')
            good_tag_id = self.env['stock.location.tag'].search([('is_inbound','=',True)],limit=1)
            # good_tag_id = self.env.ref('stock_3dbase.stock_location_tag_good')
            for in_stock_move in in_stock_moves:
                pallete_packages = in_stock_move.product_id.packaging_ids.filtered(lambda s:s.package_type_id.is_pallete_package)
                no_creating_package = 0
                for pallete_package in pallete_packages:
                     move_quantity = sum(in_stock_move.filtered(lambda s: pallete_package in s.product_id.packaging_ids).mapped('quantity'))
                     if pallete_package.qty > 0.0:
                         no_creating_package += math.ceil(move_quantity / pallete_package.qty)
                in_move_line_ids = in_stock_move.mapped('move_line_ids').filtered(lambda ml: ml.state != 'done')
                package_ids = []
                for i in range(no_creating_package):
                    package = self.env['stock.quant.package'].create({'stock_move_id': in_stock_move.id})
                    if pallete_packages:
                        package.package_type_id = pallete_packages[0].package_type_id.id
                    if good_tag_id:
                        package.tag_id = good_tag_id.id
                    # package_type = in_stock_move.product_packaging_id.package_type_id
                    # if len(package_type) == 1:
                    #     package.package_type_id = package_type
                    package_ids.append(package.id)
                in_move_line_ids.write({
                    'result_package_id': package_ids[0] if len(package_ids) > 0 else False,
                })
                for picking in in_move_line_ids.mapped('picking_id'):
                    picking_lines = in_move_line_ids.filtered(lambda ml: ml.picking_id == picking)
                    self.env['stock.package_level'].with_context(from_put_in_pack=True).create({
                        'package_id': package_ids[0] if len(package_ids) > 0 else False,
                        'picking_id': picking.id,
                        'location_id': picking_lines[0].location_id.id,
                        'location_dest_id': picking_lines[0].location_dest_id.id,
                        'move_line_ids': [(6, 0, picking_lines.ids)],
                        'company_id': picking.company_id.id,
                    })
        other_move = self - out_stock_move - in_stock_moves
        for record in other_move.filtered(lambda s:s.state not in ('draft','done', 'cancel')):
            record.picking_id.action_put_in_pack(move_lines_to_pack=record.move_line_ids)


    planning_status_show = fields.Boolean(
        string="Planning Status",
        related="picking_id.planning_status",
        store=True,
        readonly=True
    )

    pack_reference = fields.Text(string="Pack Reference", compute="_compute_pack_reference", store=True)

    @api.depends('origin', 'move_line_ids.result_package_id.name')
    def _compute_pack_reference(self):
        """Compute pack reference from the first package in move lines."""
        # Clear pack_reference for records without origin
        records_without_origin = self.filtered(lambda m: not m.origin)
        records_without_origin.pack_reference = False
        
        records_with_origin = self - records_without_origin
        if not records_with_origin:
            return
        
        # Batch fetch: get first package name per origin in a single query
        origins = tuple(records_with_origin.mapped('origin'))
        
        self.env.cr.execute("""
            SELECT DISTINCT ON (sm.origin)
                sm.origin,
                sp.name
            FROM stock_move_line sml
            INNER JOIN stock_move sm ON sm.id = sml.move_id
            INNER JOIN stock_quant_package sp ON sp.id = sml.result_package_id
            WHERE sm.origin IN %s
            AND sp.name IS NOT NULL 
            AND sp.name != ''
            ORDER BY sm.origin, sml.id
        """, (origins,))
        
        pack_by_origin = dict(self.env.cr.fetchall())
        
        # Assign pack references in batch
        for record in records_with_origin:
            record.pack_reference = pack_by_origin.get(record.origin, False)


    def ship_confirm_button_validate(self):
        pickings = self.mapped('picking_id').filtered(lambda p: p.state not in ('done', 'cancel'))
        pickings.button_validate()


    def _open_batch_wizard_from_move(self):
        pickings = self.mapped('picking_id').filtered(lambda p: p.state not in ['cancel'])
        if not pickings:
            raise UserError("No valid pickings found to add to batch.")

        return {
            'name': 'Add to Batch',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.to.batch',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': pickings.ids,
            }
        }

    batch_ref = fields.Char(
        string='Batch Ref',
        compute='_compute_batch_ref',
        store=True,
    )

    @api.depends('picking_id.batch_id.name')
    def _compute_batch_ref(self):
        for move in self:
            move.batch_ref = move.picking_id.batch_id.name if move.picking_id and move.picking_id.batch_id else ''
            move.move_dest_ids.previous_batch_ref = move.batch_ref

    previous_batch_ref = fields.Char(
        string='Previous Batch Ref',
        compute='_compute_previous_batch_ref',
        store=True,
    )

    @api.depends('picking_id.batch_id', 'batch_ref', 'picking_id.date_done', 'picking_id.origin')
    def _compute_previous_batch_ref(self):
        for move in self:
            prev_batch_name = ''
            picking = move.picking_id

            if move.move_orig_ids:
                prev_batch_name = move.move_orig_ids[0].batch_ref if move.move_orig_ids else ''

            # if picking and picking.batch_id and picking.date_done:
            #     prev_picking = self.env['stock.picking'].search([
            #         ('origin', '=', picking.origin),
            #         ('batch_id', '!=', False),
            #         ('date_done', '<', picking.date_done),
            #     ], order='date_done desc', limit=1)
            #
            #     if prev_picking:
            #         prev_batch_name = prev_picking.batch_id.name

            move.previous_batch_ref = prev_batch_name


    # def action_print_related_so_invoices(self):
    #     invoice_ids = self.env['account.move']
    #     for move in self:
    #         if move.picking_id and move.picking_id.origin:
    #             # Find SO using origin (assuming origin holds SO name)
    #
    #             sale_order = self.env['sale.order'].search([('id', '=', move.picking_id.sale_id.id)], limit=1)
    #             invoice_ids = sale_order.mapped('invoice_ids').filtered(
    #                 lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel'
    #             )
    #
    #     if not invoice_ids:
    #         raise UserError(_("No related invoices found to print."))
    #
    #     return self.env.ref('account.account_invoices').report_action(invoice_ids)

    def action_print_related_so_invoices(self):
        IrActionsReport = self.env['ir.actions.report']
        invoice_ids = self.env['account.move']

        for move in self:
            if move.picking_id and move.picking_id.sale_id:
                sale_order = move.picking_id.sale_id
                related_invoices = sale_order.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel'
                )
                invoice_ids |= related_invoices

        if not invoice_ids:
            raise UserError("No related invoices found to print.")

        # Prepare zip in memory
        zip_buffer = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)


        for invoice in invoice_ids:
            pdf_content, _= self.env["ir.actions.report"].sudo()._render_qweb_pdf(
                'stock_outbouding_operation.tax_account_invoices',
                invoice.id,

            )
            filename = f"invoice_{invoice.name.replace('/', '_')}.pdf"
            zip_file.writestr(filename, pdf_content)

        zip_file.close()
        zip_buffer.seek(0)

        # Create and return attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'Invoices.zip',
            'type': 'binary',
            'datas': base64.b64encode(zip_buffer.read()),
            'mimetype': 'application/zip',
            'res_model': 'stock.picking' if self.mapped('picking_id') else self._name,
            'res_id': self.mapped('picking_id')[0].id if self.mapped('picking_id') else self[0].id,
        })

        download_url = f'/web/content/{attachment.id}?download=true'
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'new',
        }