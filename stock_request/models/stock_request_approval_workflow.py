from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from odoo.exceptions import UserError


class StockRequestOrder(models.Model):
    _inherit = 'stock.request.order'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),

        # Approval flow steps
        ('division_head_approved', 'Division Head Approved'),
        ('scm_approved', 'SCM Approved'),
        ('finance_approved', 'Finance Approved'),
        ('director_approved', 'Director Approved'),
        ('scd_approved', 'SCD Approved'),
        ('scd_manager_approved', 'SCD Manager Approved'),
        ('warehouse_manager_approved', 'Warehouse Manager Approved'),
        ('line_manager_approved', 'Line Manager Approved'),

        # Terminal states
        ('nsm_approved', 'NSM Approved'),
        ('approved_done', 'Approved Done'),
        ('open', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('delivery_recycle', 'Delivered for recycling')
    ], default='draft', tracking=True, string='Status')




    def action_approve(self):
        for rec in self:
            direction = rec.direction
            user = self.env.user

            if direction in ['sample_issue_out']:
                if rec.state == 'submitted':
                    if not user.has_group('gulfco_contact_registration_custom.group_div_head_approval'):
                        raise AccessError(_("Only Division Head can approve this request at this stage."))
                    rec.state = 'division_head_approved'
                    continue

                if rec.state == 'division_head_approved':
                    if not user.has_group('account.group_account_manager'):
                        raise AccessError(_("Only Finance can approve this request at this stage."))
                    rec.state = 'finance_approved'
                    continue

                if rec.state == 'finance_approved':
                    if not user.has_group('stock_inventory_adjustment.group_director_approval'):
                        raise AccessError(_("Only Director can approve this request at this stage."))
                    rec.state = 'director_approved'
                    if rec.state == 'director_approved':
                        rec.state = 'approved_done'
                        rec.action_confirm()
                    continue


            if direction in ['damage_expiry_issue_out']:
                if rec.state == 'submitted':
                    if not user.has_group('gulfco_contact_registration_custom.group_div_head_approval'):
                        raise AccessError(_("Only Division Head can approve this request at this stage."))
                    rec.state = 'division_head_approved'
                    continue

                if rec.state == 'division_head_approved':
                    if not user.has_group('gulfco_contact_registration_custom.group_scm_approval'):
                        raise AccessError(_("Only SCM can approve this request at this stage."))
                    rec.state = 'scm_approved'
                    continue

                if rec.state == 'scm_approved':
                    if not user.has_group('account.group_account_manager'):
                        raise AccessError(_("Only Finance can approve this request at this stage."))
                    rec.state = 'finance_approved'
                    continue

                if rec.state == 'finance_approved':
                    if not user.has_group('stock_inventory_adjustment.group_director_approval'):
                        raise AccessError(_("Only Director can approve this request at this stage."))
                    rec.state = 'director_approved'
                    if rec.state == 'director_approved':
                        rec.state = 'approved_done'
                        rec.action_confirm()
                    continue

            # سلسلة الموافقات لـ FOC Receiving
            if direction in ['foc_receiving']:
                if rec.state == 'submitted':

                    if rec.state == 'submitted':
                        if not user.has_group('gulfco_contact_registration_custom.group_div_head_approval'):
                            raise AccessError(_("Only Division Head can approve this request at this stage."))
                        rec.state = 'division_head_approved'
                        continue
                if rec.state == 'division_head_approved':
                    if not user.has_group('gulfco_contact_registration_custom.group_scm_approval'):
                        raise AccessError(_("Only SCM can approve this request at this stage."))
                    rec.state = 'scm_approved'
                    continue

                if rec.state == 'scm_approved':
                    if not user.has_group('account.group_account_manager'):
                        raise AccessError(_("Only Finance can approve this request at this stage."))
                    rec.state = 'finance_approved'
                    continue

                # if rec.state == 'finance_approved':
                #     if not user.has_group('stock_inventory_adjustment.group_director_approval'):
                #         raise AccessError(_("Only Director can approve this request at this stage."))
                #     rec.state = 'director_approved'
                #     continue

                if rec.state == 'finance_approved':
                    if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                        raise AccessError(_("Only SCD can approve this request at this stage."))
                    rec.state = 'scd_approved'
                    continue


                if rec.state == 'scd_approved':
                    if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                        raise AccessError(_("Only SCD Manager can approve this request at this stage."))
                    rec.state = 'approved_done'
                    rec.last_approved_by = self.env.user
                    if rec.state == 'approved_done':
                        rec.action_confirm()
                    continue


                # if rec.state == 'scd_approved':
                #     if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                #         raise AccessError(_("Only SCD Manager can approve this request at this stage."))
                #     rec.state = 'approved_done'
                #     rec.last_approved_by = self.env.user
                #     continue

            # سلسلة الموافقات لـ Consumable Issuance
            if direction == 'consumable_issuance':
                if rec.state == 'submitted':
                    if not user.has_group('gulfco_contact_registration_custom.group_line_manager'):
                        raise AccessError(_("Only Line Manager can approve this request at this stage."))
                    rec.state = 'line_manager_approved'
                    continue
                if rec.state == 'line_manager_approved':
                    if not user.has_group('gulfco_contact_registration_custom.group_scm_approval'):
                        raise AccessError(_("Only SCM can approve this request at this stage."))
                    rec.state = 'scm_approved'
                    # rec.state = 'approved_done'
                    continue

                if rec.state == 'scm_approved':
                    if not user.has_group('account.group_account_manager'):
                        raise AccessError(_("Only Finance can approve this request at this stage."))
                    rec.state = 'finance_approved'
                    if rec.state == 'finance_approved':
                        rec.state = 'approved_done'
                        rec.action_confirm()
                    continue


            # Stock Takeover
            if direction == 'stock_takeover':
                location_group = rec.location_id.location_group
                if location_group == 'van':
                    if 'mars' in rec.new_stockkeeper.partner_id.division_ids.mapped('type'):
                        if rec.state == 'submitted':
                            if not user.has_group('gulfco_contact_registration_custom.group_line_manager'):
                                raise AccessError(_("Only Line Manager can approve this request at this stage."))
                            rec.state = 'line_manager_approved'
                            continue
                        if rec.state == 'line_manager_approved':
                            if not user.has_group('stock_request.stock_group_nsm_mars_approval'):
                                raise AccessError(_("Only NSM Mars can approve this request at this stage."))
                            rec.state = 'nsm_approved'
                            continue

                        if rec.state == 'nsm_approved':
                            if not user.has_group('account.group_account_manager'):
                                raise AccessError(_("Only Finance can approve this request at this stage."))
                            rec.state = 'finance_approved'
                            continue

                        if rec.state == 'finance_approved':
                            if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                                raise AccessError(_("Only SCD can approve this request at this stage."))
                            rec.state = 'scd_approved'
                            if rec.state == 'scd_approved':
                                rec.state = 'approved_done'
                                rec.action_confirm()
                            continue

                        # if rec.state == 'scd_approved':
                        #     if not user.has_group('stock_inventory_adjustment.group_scd_manager_approval'):
                        #         raise AccessError(_("Only SCD can approve this request at this stage."))
                        #     rec.state = 'approved_done'
                        #     rec.last_approved_by = self.env.user
                        #     continue
                    elif 'mars' not in rec.new_stockkeeper.partner_id.division_ids.mapped('type'):
                        if rec.state == 'submitted':
                            if not user.has_group('gulfco_contact_registration_custom.group_line_manager'):
                                raise AccessError(_("Only Line Manager can approve this request at this stage."))
                            rec.state = 'line_manager_approved'
                            continue
                        if rec.state == 'line_manager_approved':
                            if not user.has_group('stock_request.stock_group_nsm_f_nf_approval'):
                                raise AccessError(_("Only NSM F/NF can approve this request at this stage."))
                            rec.state = 'nsm_approved'
                            continue

                        if rec.state == 'nsm_approved':
                            if not user.has_group('account.group_account_manager'):
                                raise AccessError(_("Only Finance can approve this request at this stage."))
                            rec.state = 'finance_approved'
                            continue

                        if rec.state == 'finance_approved':
                            if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                                raise AccessError(_("Only SCD can approve this request at this stage."))
                            rec.state = 'scd_approved'
                            if rec.state == 'scd_approved':
                                rec.state = 'approved_done'
                                rec.action_confirm()
                            continue
                        # if rec.state == 'scd_approved':
                        #     if not user.has_group('stock_inventory_adjustment.group_scd_manager_approval'):
                        #         raise AccessError(_("Only SCD can approve this request at this stage."))
                        #     rec.state = 'approved_done'
                        #     rec.last_approved_by = self.env.user
                        #     continue

                elif location_group == 'wh':
                    if rec.state == 'submitted':
                        if self.env.user.id not in rec.warehouse_id.wh_manager.ids:
                            raise AccessError(_("Only Warehouse Manager can approve this request at this stage."))
                        rec.state = 'warehouse_manager_approved'
                        continue
                        # if not user.has_group('gulfco_contact_registration_custom.group_scm_approval'):
                        #     raise AccessError(_("Only SCM can approve this request at this stage."))
                        # rec.state = 'scm_approved'
                        # continue
                    if rec.state == 'warehouse_manager_approved':
                        if not user.has_group('gulfco_contact_registration_custom.group_scm_approval'):
                            raise AccessError(_("Only SCM can approve this request at this stage."))
                        rec.state = 'scm_approved'
                        continue

                    if rec.state == 'scm_approved':
                        if not user.has_group('account.group_account_manager'):
                            raise AccessError(_("Only Finance can approve this request at this stage."))
                        rec.state = 'finance_approved'
                        continue

                    if rec.state == 'finance_approved':
                        if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                            raise AccessError(_("Only SCD can approve this request at this stage."))
                        rec.state = 'scd_approved'
                        if rec.state == 'scd_approved':
                            rec.state = 'approved_done'
                            rec.action_confirm()
                        continue

                    # if rec.state == 'scd_approved':
                    #     if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                    #         raise AccessError(_("Only SCD Manager can approve this request at this stage."))
                    #     rec.state = 'approved_done'
                    #     rec.last_approved_by = self.env.user
                    #     continue


            if direction == 'scrap_issuance':
                if rec.state == 'submitted':
                    if not user.has_group('gulfco_contact_registration_custom.group_scm_approval'):
                        raise AccessError(_("Only SCM can approve this request at this stage."))
                    rec.state = 'scm_approved'
                    continue

                if rec.state == 'scm_approved':
                    if not user.has_group('account.group_account_manager'):
                        raise AccessError(_("Only Finance can approve this request at this stage."))
                    rec.state = 'finance_approved'
                    continue

                if rec.state == 'finance_approved':
                    if not user.has_group('stock_inventory_adjustment.group_director_approval'):
                        raise AccessError(_("Only Director can approve this request at this stage."))
                    rec.state = 'director_approved'
                    continue

                if rec.state == 'director_approved':
                    if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                        raise AccessError(_("Only SCD can approve this request at this stage."))
                    rec.state = 'scd_approved'
                    rec.last_approved_by = self.env.user
                    continue

                if rec.state == 'scd_approved':
                    if not user.has_group('stock_inventory_adjustment.group_scd_approval'):
                        raise AccessError(_("Only SCD Manager can approve this request at this stage."))
                    rec.state = 'approved_done'
                    rec.last_approved_by = self.env.user
                    if rec.state == 'approved_done':
                        rec.action_confirm()
                    continue

    last_approved_by = fields.Many2one('res.users', string='Last Approved By', readonly=True)

    def action_confirm(self):
        for rec in self:
            is_admin = self.env.user.has_group('base.group_system')
            if rec.state != 'approved_done':
                if not (
                        rec.state in ['submitted'] and
                        rec.direction in ('miscellaneous_issue_out', 'miscellaneous_receiving', 'internal_transfer',
                                          'van_load', 'branch_transfer', 'van_off_load', 'stock_takeover')
                ):
                    raise UserError(_("Only fully approved requests can be confirmed."))

            if rec.direction in ['foc_receiving', 'scrap_issuance',]: # 'stock_takeover']:
                if rec.state == 'approved_done':
                    last_approver = rec.last_approved_by

                    if last_approver and last_approver.employee_id and last_approver.employee_id.parent_id:
                        manager_user = last_approver.employee_id.parent_id.user_id
                    else:
                        raise UserError(_("No manager found."))

                    if manager_user != self.env.user:
                        raise AccessError("Only the manager of the previous confirmer can confirm this request.")


            if rec.direction == 'internal_transfer':
                if self.env.user.id not in rec.warehouse_id.wh_manager.ids and not is_admin:
                    raise AccessError("Only Warehouse Manager can confirm.")


            elif rec.direction == 'branch_transfer':
                if self.env.user.id not in rec.to_warehouse_id.wh_manager.ids and not is_admin:
                    raise AccessError("Only To Warehouse Manager can confirm.")


            elif rec.direction in ['sample_issue_out', 'damage_expiry_issue_out']:
                if not self.env.user.has_group('stock_inventory_adjustment.group_director_approval'):
                    raise AccessError("Only Director can confirm.")

            elif rec.direction == 'consumable_issuance':
                if not self.env.user.has_group('account.group_account_manager'):
                    raise AccessError("Only Finance can confirm.")

        # if rec.state != 'approved_done':
        #     if not (rec.state == 'submitted' and rec.direction in (
        #     'internal_transfer', 'van_load', 'branch_transfer', 'van_off_load', 'stock_takeover')):
        #         raise UserError(_("Only fully approved requests can be confirmed."))

        return super(StockRequestOrder, self).action_confirm()
