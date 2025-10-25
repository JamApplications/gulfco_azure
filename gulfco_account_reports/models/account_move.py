# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api
from lxml import etree
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order', related='purchase_line_id.order_id',
                                            readonly=True, store=True)

    distribution_analytic_account_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        compute='_compute_distribution_analytic_account_ids',
        search='_search_distribution_analytic_account_ids',
        required=True,
        string="JOO"
    )

    cost_center_name = fields.Char(compute="compute_cost_center_name", store=True)
    ass_value = fields.Float("Ass. Value", compute="_compute_ass_value", store=True)
    
    @api.depends('move_id.ass_value', 'price_subtotal', 'move_id.invoice_line_ids.price_subtotal')
    def _compute_ass_value(self):
        for line in self:
            move = line.move_id
            if not move.ass_value or not line.price_subtotal or move.move_type != 'in_invoice':
                line.ass_value = 0.0
                continue

            # Total price of all lines in that bill
            total_subtotal = sum(l.price_subtotal for l in move.invoice_line_ids if l.price_subtotal)
            if not total_subtotal:
                line.ass_value = 0.0
            else:
                line.ass_value = (line.price_subtotal / total_subtotal) * move.ass_value


    @api.depends('analytic_distribution')
    def compute_cost_center_name(self):
        # try:
        for record in self:
            cost_center_name = ''
            if record.analytic_distribution:
                for account_ids, distribution in record.analytic_distribution.items():
                    analytic_account_ids = self.env['account.analytic.account'].browse(
                        map(int, account_ids.split(","))).exists().filtered(lambda s:s.plan_id.is_department_plan)
                    cost_center_name += ','.join(analytic_account_ids.mapped('display_name')) + ','
            elif record.account_type in ['asset_receivable','liability_payable']:
                other_lines = record.move_id.line_ids.filtered(lambda s: s != record)
                analytic_distribution_list = other_lines.mapped('analytic_distribution')
                existing_analytic_account_ids = self.env['account.analytic.account']
                for analytic_distribution in analytic_distribution_list:
                    if analytic_distribution:
                        for account_ids, distribution in analytic_distribution.items():
                            analytic_account_ids = self.env['account.analytic.account'].browse(
                                map(int, account_ids.split(","))).exists().filtered(lambda s:s.plan_id.is_department_plan)
                            if analytic_account_ids:
                                analytic_account_ids = analytic_account_ids - existing_analytic_account_ids
                                existing_analytic_account_ids += analytic_account_ids
                                cost_center_name += ','.join(analytic_account_ids.mapped('display_name')) + ','
            record.cost_center_name = cost_center_name
        # except Exception as e:
        #     print(e)
    
    @api.model
    def _get_view(self, view_id=None, view_type='tree', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        # Restrict only in the deferred entries view
        if view_type == "list" and view and view.xml_id == "account_accountant.view_deferred_entries_tree":
            # Check if current user is NOT in accounting admin group
            for node in arch.xpath("//field[@name='account_id']"):
                if not self.env.user.has_group("account.group_account_manager"):
                    node.set("readonly", "1")
                elif node.attrib.get('readonly'):
                    node.set("readonly", "0")
                    # node.set("modifiers", '{"readonly": true}')

        return arch, view
    
    

class AccountMove(models.Model):
    _inherit = "account.move"
    custom_authority = fields.Char(
        string='Custom Authority',
    )
    boe_number = fields.Char(
        string='BOE Number',
    )
    purchase_order_ref = fields.Char('Purchase Order', compute="_get_po_number",
                                         store=True)

    ass_value = fields.Float("Ass. Value")

    prepaid_account = fields.Char(string="Prepaid Account")
    original_value = fields.Char(string="Original Value")
    asset_number = fields.Char(string="Asset Number")
    ytd_amortization = fields.Char(string="YTD Amortization")
    prepaid_account_2 = fields.Char(string="Prepaid Account (Duplicate Field)")  # Rename if needed
    previous_bill_no_ref = fields.Char(string="Previous Bill No Ref.")
    payment_terms_ref = fields.Char(string="Payment Terms")  # Avoid conflict with original field
    property_type = fields.Char(string="Property Type")
    contract_no = fields.Char(string="Contract No")
    lessor_name_contract = fields.Char(string="Lessor Name as per Contract")
    lessee_name_contract = fields.Char(string="Lessee Name as per Contract")
    property_location = fields.Char(string="Property Location")
    unit_details = fields.Char(string="Unit No/Details")
    other_details = fields.Char(string="Other Details")
    contract_start_date = fields.Char(string="Contract Start Date")
    contract_end_date = fields.Char(string="Contract End Date")
    lessor_type = fields.Char(string="Lessor Type (AMP/3rd party)")
    due_date_upload = fields.Date(string="Due Date Upload")

    @api.depends('line_ids', 'invoice_line_ids', 'partner_id')
    def _get_po_number(self):
        for rec in self:
            rec.purchase_order_ref = ''
            if rec.line_ids.filtered(lambda l: l.purchase_line_id):
                unique_po_names = sorted(set(po.name for po in rec.line_ids.purchase_line_id.order_id if rec.line_ids.purchase_line_id))
                if len(unique_po_names) == 1:
                    rec.purchase_order_ref = unique_po_names[0]
                elif unique_po_names:
                    rec.purchase_order_ref = ', '.join(unique_po_names)
                else:
                    rec.purchase_order_ref = ''
                    
    def write(self, vals):
        res = super().write(vals)
        if 'ass_value' in vals and vals.get('ass_value') > 0:
            vendor_bills = self.filtered(lambda m: m.move_type == 'in_invoice')
            for bill in vendor_bills:
                for line in bill.invoice_line_ids:
                    if line.ass_value:
                        # Store current taxes
                        current_taxes = line.tax_ids
                        # First, remove taxes
                        line.tax_ids = [(5, 0, 0)]  # Remove all
                        # Then re-assign the same taxes (triggers tax recompute)
                        line.tax_ids = [(6, 0, current_taxes.ids)]
        return res

    def action_post(self):
        try:
            for move in self.filtered(lambda move: move.move_type in ['out_invoice', 'out_invoice', 'out_refund', 'in_refund'] ):
                # Ensure all move lines have at least one analytic account selected
                for line in move.invoice_line_ids:
                    if not line.distribution_analytic_account_ids and line.product_id:
                        raise ValidationError(
                            "You cannot post this journal entry because at least one line is missing an Analytic Account."
                        )

        except:
            pass

        # Call the original action_post method
        return super(AccountMove, self).action_post()

    uncovered_balance = fields.Monetary(
        string='Uncovered Balance',
        compute='_compute_uncovered_balance', store=True,
        currency_field='company_currency_id',
        help="Uncovered Balance of Invoice.",
    )

    @api.depends('line_ids.amount_residual','matched_payment_ids','matched_payment_ids.state','matched_payment_ids.pdc_state','matched_payment_ids.cdc_state','matched_payment_ids.amount')
    def _compute_uncovered_balance(self):
        for record in self:
            company = record.company_id
            currency = record.currency_id
            company_currency = company.currency_id
            invoice_date = record.invoice_date or fields.Date.today()
            uncovered_balance = record.amount_residual_signed
            matched_payment_ids = record.matched_payment_ids
            if record.payment_state in ['not_paid','partial'] and record.move_type != 'entry':
                reconciled_partials = record.sudo()._get_all_reconciled_invoice_partials()
                if reconciled_partials:
                    apply_balance = 0.0
                    applied_balance = 0.0
                    for reconciled_partial in reconciled_partials:
                        if 'aml' in reconciled_partial and reconciled_partial.get('aml'):
                            move_id = reconciled_partial.get('aml').move_id
                            if matched_payment_ids and move_id.payment_ids:
                                matched_payment_ids -= move_id.payment_ids
                        reconciled_partial_amount_signed = currency._convert(
                            reconciled_partial['amount'], company_currency, company, invoice_date
                        )
                        apply_balance += reconciled_partial_amount_signed
                    if matched_payment_ids:
                        cheque_state_list = ['registered', 're_cheque', 'deposit', 'collected']
                        applied_payments = matched_payment_ids.filtered(lambda s: s.state != 'paid' and (
                                    s.pdc_state in cheque_state_list or s.cdc_state in cheque_state_list))
                        applied_balance = sum(applied_payments.mapped('amount_company_currency_signed'))
                    uncovered_balance = record.amount_total_signed - apply_balance - applied_balance
                elif record.matched_payment_ids:
                    cheque_state_list = ['registered','re_cheque','deposit','collected']
                    applied_payments = record.matched_payment_ids.filtered(lambda s:s.state != 'paid' and (s.pdc_state in cheque_state_list or s.cdc_state in cheque_state_list))
                    applied_balance = sum(applied_payments.mapped('amount_company_currency_signed'))
                    uncovered_balance = record.amount_total_signed - applied_balance
            record.uncovered_balance = uncovered_balance