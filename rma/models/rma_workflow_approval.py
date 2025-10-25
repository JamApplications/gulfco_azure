from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class CustomRma(models.Model):
    _inherit = "rma"


    state = fields.Selection(selection_add=[
        ('product_under_inspection', 'Product Under Inspection'),
    ])

    wh_manager = fields.Many2many(
        'res.users',
        string="WH Manager",
        help="Warehouse Managers responsible for approving Base on Delivery RMAs.",
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help="Warehouse related to this RMA."
    )

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        for record in self:
            if record.warehouse_id:
                record.wh_manager = record.warehouse_id.wh_manager
            else:
                record.wh_manager = False


    def action_confirm(self):
        for record in self:

            # self.ensure_one()
            record._ensure_required_fields()
            if record.state == "draft" or record.env.context.get('from_rma_extended'):
                if record.picking_id and record.line_ids:
                    reception_move = record._create_receptions_from_picking()
                else:
                    reception_move = record._create_receptions_from_product()
                reception_move.picked = True
                record.write({"reception_move_ids": reception_move.ids, 'reception_move_id': reception_move[0].id,
                            "state": "confirmed", "approved_by": record.env.user.id})
                record._add_message_subscribe_partner()
                record._send_confirmation_email()


            team_type = getattr(record.crm_team_id, 'team_type', False)
            is_pre_sale = team_type == 'pre_sale'
            is_van_sales = team_type == 'van_sale'

            is_base_on_product = record.rma_type == 'base_on_product'
            is_base_on_delivery = record.rma_type == 'base_on_delivery'
            is_mt_channel = record.partner_channel_id.channel_name == 'MT'
            is_gt_channel = record.partner_channel_id.channel_name == 'GT'

            is_amount_under_200 = record.grv_amount <= 200
            is_amount_between_200_500 = 200 < record.grv_amount <= 500
            is_amount_under_500 = record.grv_amount <= 500
            is_amount_between_500_5000 = 500 < record.grv_amount <= 5000

            creator_user = record.create_uid
            is_admin = self.env.user.has_group('base.group_system')
            # creator_user = record.responsible_worker_id

            creator_user = self.create_uid
            creator_manager_user = creator_user.employee_id.parent_id.user_id if (
                    creator_user and creator_user.employee_id and creator_user.employee_id.parent_id
            ) else self.env['res.users']  # empty recordset instead of False

            team_leader_with_uid = (
                    record.crm_team_id.user_id
                    | creator_user
                    | creator_manager_user
            )

            if is_pre_sale and is_base_on_product and is_mt_channel:
                if is_amount_under_500:
                    if (self.env.uid not in team_leader_with_uid.ids) and not is_admin:
                    # if self.env.uid != record.responsible_worker_id.id:
                        raise UserError(_("Only the RMA creator (%s) can confirm this record. You are (%s).") % (
                            creator_user.name, self.env.user.name))
                    record.state = 'confirmed'
                elif is_amount_between_500_5000:
                    team_leader = record.crm_team_id.user_id
                    if self.env.uid not in [team_leader.id, creator_manager_user.id] and not is_admin:
                        raise UserError(_("Only the Team Leader can confirm this RMA (Pre-Sale, MT, 500 < amount <= 5000)."))
                    record.state = 'confirmed'
                else:
                    creator_user = self.create_uid
                    creator_manager_user = False

                    if creator_user and creator_user.employee_id and creator_user.employee_id.parent_id:
                        creator_manager_user = creator_user.employee_id.parent_id.user_id

                    if (not creator_manager_user or not creator_manager_user.employee_id or not creator_manager_user.employee_id.parent_id) and not is_admin:
                        raise UserError(_("No manager defined for creator (%s).") % creator_user.name)

                    grand_manager_user = creator_manager_user.employee_id.parent_id.user_id if creator_manager_user and creator_manager_user.employee_id else None

                    if self.env.user != grand_manager_user and not is_admin:
                        raise UserError(
                            _("Only the manager (%s) can confirm this record (Pre-Sale, MT, > 5000). You are (%s).") % (
                                grand_manager_user.name if grand_manager_user else "N/A",
                                self.env.user.name))

                    record.state = 'confirmed'


            # 2. Pre-Sale - GT
            elif is_pre_sale and is_base_on_product and is_gt_channel:
                if is_amount_under_200:
                    if (self.env.uid not in team_leader_with_uid.ids) and not is_admin:
                    # if self.env.uid != record.responsible_worker_id.id:
                        raise UserError(_("Only the RMA creator (%s) can confirm this record. You are (%s).") % (
                            creator_user.name, self.env.user.name))
                    record.state = 'confirmed'

                elif is_amount_between_200_500:
                    team_leader = record.crm_team_id.user_id
                    if self.env.uid not in [team_leader.id, creator_manager_user.id] and not is_admin:
                        raise UserError(_("Only the Team Leader can confirm this RMA (Pre-Sale, MT, 200 < amount <= 500)."))
                    record.state = 'confirmed'

                else:
                    creator_user = self.create_uid
                    creator_manager_user = False

                    if creator_user and creator_user.employee_id and creator_user.employee_id.parent_id:
                        creator_manager_user = creator_user.employee_id.parent_id.user_id

                    if (not creator_manager_user or not creator_manager_user.employee_id or not creator_manager_user.employee_id.parent_id) and not is_admin:
                        raise UserError(_("No manager defined for creator (%s).") % creator_user.name)

                    grand_manager_user = creator_manager_user.employee_id.parent_id.user_id if creator_manager_user and creator_manager_user.employee_id else None

                    if self.env.user != grand_manager_user and not is_admin:
                        raise UserError(
                            _("Only the manager (%s) can confirm this record (Pre-Sale, MT, > 500). You are (%s).") % (
                                grand_manager_user.name if grand_manager_user else "N/A",
                                self.env.user.name))

                    record.state = 'confirmed'


            # 3. Base on Delivery
            elif is_pre_sale and is_base_on_delivery:
                picking = record.picking_id
                picking_type = picking.picking_type_id

                if not picking_type:
                    raise UserError(_("No Picking Type defined on the selected Picking."))

                warehouse = picking_type.warehouse_id
                if not warehouse:
                    raise UserError(_("No Warehouse defined for the Picking Type (%s).") % picking_type.name)

                wh_manager_user = warehouse.wh_manager
                if not wh_manager_user:
                    raise UserError(_("No Warehouse Manager assigned to Warehouse (%s).") % warehouse.name)

                if self.env.user.id not in wh_manager_user.ids and not is_admin:
                    raise UserError(
                        _("Only the Warehouse Manager (%s) of Warehouse (%s) can confirm this RMA. You are (%s).") % (
                            ', '.join(wh_manager_user.mapped('name')),
                            warehouse.name,
                            self.env.user.name))

                record.state = 'confirmed'

            # 4. Van Sales
            elif is_van_sales:
                icp = self.env['ir.config_parameter'].sudo()
                limit = float(icp.get_param('plnx_rma_extended.grv_amount', '0') or 0.0)
                if limit and limit > 0 and record.grv_amount <= limit:
                    pass
                elif not self.env.user.has_group('gulfco_contact_registration_custom.group_line_manager') and not is_admin:
                    raise UserError(
                        _("Only users with Line Manager access rights can confirm this record (Van Sales). You are (%s).") % self.env.user.name)

                record.state = 'confirmed'


            # 5. Default
            else:
                super(CustomRma, record).action_confirm()

    def write(self, vals):
        for record in self:
            old_state = record.state  # احفظ الحالة القديمة قبل الكتابة

        res = super(CustomRma, self).write(vals)

        for record in self:
            new_state = vals.get('state')
            if new_state and new_state != old_state:
                state_template_map = {
                    'draft': 'rma.rma_draft_template',
                    'confirmed': 'rma.mail_template_rma_confirmed_notification',
                    'received': 'rma.mail_template_rma_received_notification',
                    'waiting_return': 'rma.mail_template_rma_waiting_return_notification',
                    'waiting_replacement': 'rma.mail_template_rma_waiting_replacement_notification',
                    'refunded': 'rma.mail_template_rma_refunded_notification',
                    'returned': 'rma.mail_template_rma_returned_notification',
                    'replaced': 'rma.mail_template_rma_replaced_notification',
                    'finished': 'rma.mail_template_rma_finished_notification',
                    'locked': 'rma.mail_template_rma_locked_notification',
                    'cancelled': 'rma.mail_template_rma_cancelled_notification',
                    'product_under_inspection': 'rma.mail_template_rma_product_under_inspection_notification',
                }

                template_xml_id = state_template_map.get(new_state)
                email_sent = False

                if template_xml_id and record.partner_id.email:
                    template = self.env.ref(template_xml_id, raise_if_not_found=False)
                    if template:
                        template.send_mail(record.id, force_send=True)
                        email_sent = True

                state_label = dict(record._fields['state'].selection).get(new_state, new_state)
                record.message_post(
                    body=f"تم تغيير الحالة إلى <b>{state_label}</b>. "
                         f"{'تم إرسال إشعار عبر البريد الإلكتروني.' if email_sent else 'لم يتم إرسال إشعار عبر البريد الإلكتروني.'}",
                    message_type='notification',
                    subtype_xmlid='mail.mt_note'
                )

                if new_state == 'refunded' and record.partner_id.email:
                    refund_invoices = self.env['account.move'].search([
                        ('move_type', '=', 'out_refund'),
                        ('invoice_line_ids.rma_id', 'in', record.ids),
                        ('state', '=', 'draft'),
                    ])
                    for invoice in refund_invoices:
                        credit_note_template = self.env.ref('rma.mail_template_credit_note_draft',
                                                            raise_if_not_found=False)
                        if credit_note_template:
                            credit_note_template.send_mail(invoice.id, force_send=True)


        return res

    def update_state_received(self):

        self.write({"state": "refunded"})


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # def _action_done(self):
    #     super(StockPicking, self)._action_done()
    #
    #     for picking in self:
    #         if picking.picking_type_id.code == "internal":
    #             receipt = self.env['stock.picking'].sudo().search([
    #                 ('group_id', '=', picking.group_id.id),
    #                 ('picking_type_id.code', '=', 'incoming'),
    #                 ('state', '=', 'done'),
    #             ], order='id desc', limit=1)
    #
    #             if receipt:
    #                 rmas = self.env['rma'].sudo().search([
    #                     ('reception_move_id.picking_id', '=', receipt.id)
    #                 ])
    #                 for rma in rmas:
    #                     rma.update_state_received()

    def _action_done(self):
        super(StockPicking, self)._action_done()

        for picking in self:
            if picking.picking_type_id.code == "internal" and picking.location_dest_id:
                warehouse_id = self.env['stock.warehouse'].sudo().search(
                    [('lot_stock_id', '=', picking.location_dest_id.id)], limit=1)

                if warehouse_id:
                    receipt = self.env['stock.picking'].sudo().search([
                        ('group_id', '=', picking.group_id.id),
                        ('picking_type_id.code', '=', 'incoming'),
                        ('state', '=', 'done'),
                    ], order='id desc', limit=1)

                    if receipt:
                        rmas = self.env['rma'].sudo().search([
                            ('reception_move_id.picking_id', '=', receipt.id)
                        ])
                        for rma in rmas:
                            rma.update_state_received()
