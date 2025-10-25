from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    cheque_book_line_id = fields.Many2one(
        "cheque.book.line",
        string="Cheque Book Line",
        help="Related cheque for Payable payments",
        domain="[('state', '=', 'available'), ('journal_id', '=', journal_id), '|', ('payment_id', '=', False), ('payment_id', '=', id), '|', ('partner_id', '=', partner_id), ('partner_id', '=', False)]",
        copy=False
    )
    
    # cheque_book_line_id_readonly = fields.Boolean(
    #     compute='_compute_cheque_book_line_id_readonly'
    # )
    
    # @api.depends('payment_type', 'payment_type_selection', 'custom_workflow_state')
    # def _compute_cheque_book_line_id_readonly(self):
    #     for rec in self:
    #         cheque_book_line_id_readonly = False
    #         if rec.payment_type == 'outbound':
    #             if rec.payment_type_selection != 'quick_payment':
    #                 cheque_book_line_id_readonly = True
    #             elif rec.payment_type_selection == 'quick_payment' and \
    #                     rec.custom_workflow_state in ['approved', 'rejected']:
    #                 cheque_book_line_id_readonly = True
    #         rec.cheque_book_line_id_readonly = cheque_book_line_id_readonly

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.cheque_book_line_id:
                if rec.payment_mode == 'pdc' and not rec.pdc_ref:
                    # For backward compatibility: Auto set the Cheque No. if not already set for PDC Payable payments
                    # This way, all downstream code and reports that rely on pdc_ref will continue to work, even if the new field is used
                    rec.pdc_ref = rec.cheque_book_line_id.cheque_number                
                elif rec.payment_mode == 'cdc' and not rec.cdc_ref:
                    rec.cdc_ref = rec.cheque_book_line_id.cheque_number
                if (
                    rec.cheque_book_line_id.payment_id
                    and rec.cheque_book_line_id.payment_id != rec
                ):
                    rec.cheque_book_line_id.payment_id = rec.id
                elif not rec.cheque_book_line_id.payment_id:
                    rec.cheque_book_line_id.payment_id = rec.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.cheque_book_line_id:
                if rec.payment_mode == 'pdc' and not rec.pdc_ref:
                    # For backward compatibility: Auto. set the Cheque No. if not already set for PDC Payable payments
                    # This way, all downstream code and reports that rely on pdc_ref will continue to work, even if the new field is used
                    rec.pdc_ref = rec.cheque_book_line_id.cheque_number
                elif rec.payment_mode == 'cdc' and not rec.cdc_ref:
                    rec.cdc_ref = rec.cheque_book_line_id.cheque_number
                if (
                    rec.cheque_book_line_id.payment_id
                    and rec.cheque_book_line_id.payment_id != rec
                ):
                    rec.cheque_book_line_id.payment_id = rec.id
                elif not rec.cheque_book_line_id.payment_id:
                    rec.cheque_book_line_id.payment_id = rec.id
        return records

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for rec in records:
            if rec.cheque_book_line_id:
                if rec.payment_mode == 'pdc' and not rec.pdc_ref:
                    rec.pdc_ref = rec.cheque_book_line_id.cheque_number
                elif rec.payment_mode == 'cdc' and not rec.cdc_ref:
                    rec.cdc_ref = rec.cheque_book_line_id.cheque_number

                if not rec.cheque_book_line_id.payment_id or rec.cheque_book_line_id.payment_id != rec:
                    rec.cheque_book_line_id.payment_id = rec.id

        return records

    def action_post(self):
        res = super().action_post()

        for payment in self:
            if (
                    (payment.is_pdc_payable or payment.is_cdc_payable)
                    and payment.payment_mode in ["pdc", "cdc"]
                    and payment.cheque_book_line_id
            ):
                cheque = payment.cheque_book_line_id
                if cheque.state not in ["available", "issued"]:
                    raise ValidationError("Selected cheque is not available or not yet issued.")
                if cheque.amount and cheque.amount != payment.amount:
                    raise ValidationError("Cheque amount and payment amount must match.")
                if cheque.due_date and cheque.due_date != payment.due_date:
                    raise ValidationError("Cheque due date and payment due date must match.")
                if cheque.partner_id and cheque.partner_id != payment.partner_id:
                    raise ValidationError("Cheque partner and payment partner must match.")

                cheque.write({
                    "partner_id": payment.partner_id.id,
                    "amount": payment.amount,
                    "currency_id": payment.currency_id.id,
                    "due_date": payment.due_date,
                    "issue_date": payment.date or fields.Date.today(),
                    "payment_id": payment.id,
                    "state": "issued",
                })

        return res

    @api.constrains("cheque_book_line_id", "amount", "due_date", "partner_id")
    def _check_cheque_book_line_consistency(self):
        for rec in self:
            cheque = rec.cheque_book_line_id
            if cheque:
                if cheque.amount and cheque.amount != rec.amount:
                    raise ValidationError(
                        "Cheque amount and payment amount must match."
                    )
                if cheque.due_date and cheque.due_date != rec.due_date:
                    raise ValidationError(
                        "Cheque due date and payment due date must match."
                    )
                if cheque.partner_id and cheque.partner_id != rec.partner_id:
                    raise ValidationError(
                        "Cheque partner and payment partner must match."
                    )

    def action_pdc_payable_bounce_cancel(self):
        if self.payment_mode == 'pdc':
            res = super().action_pdc_payable_bounce_cancel()
        elif self.payment_mode == 'cdc':
            res = super().action_cdc_payable_bounce_cancel()
        for payment in self:
            if payment.cheque_book_line_id and not self.env.context.get(
                "bounced_from_cheque", False
            ):
                payment.cheque_book_line_id.with_context(
                    action_from_payment=True
                ).action_set_bounced()
        return res

    def action_clear_pdc_payable(self, clear_date=None):
        """Clear PDC Payable payments by setting their state to 'cleared'"""
        if self.payment_mode == 'pdc':
            res = super().action_clear_pdc_payable(clear_date=clear_date)
        elif self.payment_mode == 'cdc':
            res = super().action_clear_cdc_payable(clear_date=clear_date)
        for payment in self:
            if payment.cheque_book_line_id and not self.env.context.get(
                "action_from_cheque", False
            ):
                payment.cheque_book_line_id.with_context(
                    cleared_from_payment=True
                ).action_set_cleared()
        return res
    
    @api.model
    def _cron_auto_clear_pdc_cdc_payables(self):
        today = fields.Date.today()

        # Auto-clear eligible PDC payments
        pdc_payments = self.search([
            ('payment_mode', '=', 'pdc'),
            ('due_date', '=', today),
            ('pdc_state', 'not in', ['bounced', 'returned', 'cancel', 'collected']),
            ('pdc_payable_state', 'not in', ['bounced', 'cancel', 'cleared']),
            ('payment_type', '=', 'outbound'),
        ])
        for payment in pdc_payments:
            try:
                if payment.pdc_state in ['draft', 'registered']:
                    try:
                        payment.action_post()
                    except Exception as e:
                        _logger.error(f"Auto Clear PDC Payment action_post failed: {payment.id}{payment.name}: Error: {e}")
                if payment.cheque_book_line_id.state in ['draft','available']:
                    payment.cheque_book_line_id.action_set_issued()
                payment.action_clear_pdc_payable(clear_date=today)
                if payment.cheque_book_line_id.state == 'issued':
                    payment.cheque_book_line_id.with_context(cleared_from_payment=True).action_set_cleared()
            except Exception as e:
                _logger.error(f"Auto Clear PDC Cheuqe Failed for: {payment.id}{payment.name}: Error: {e}")
        
        _logger.info(f"\nAuto Clear Cheuqe Processed {len(pdc_payments)} PDC Payable Payments:  {pdc_payments.ids}")

        # Auto-clear eligible CDC payments
        # cdc_payments = self.search([
        #     ('payment_mode', '=', 'cdc'),
        #     ('due_date', '=', today),
        #     ('cdc_state', 'not in', ['bounced', 'returned', 'cancel', 'collected']),
        #     ('cdc_payable_state', 'not in', ['bounced', 'cancel', 'cleared']),
        #     ('payment_type', '=', 'outbound'),
        # ])
        # for payment in cdc_payments:
        #     try:
        #         if payment.cdc_state in ['draft', 'registered']:
        #             try:
        #                 payment.action_post()
        #             except Exception as e:
        #                 _logger.error(f"Auto Clear CDC Payment action_post failed: {payment.id}{payment.name}: Error: {e}")
        #         if payment.cheque_book_line_id.state in ['draft','available']:
        #             payment.cheque_book_line_id.action_set_issued()
        #         payment.action_clear_cdc_payable(clear_date=today)
        #         if payment.cheque_book_line_id.state == 'issued':
        #             payment.cheque_book_line_id.with_context(cleared_from_payment=True).action_set_cleared()
        #     except Exception as e:
        #         _logger.error(f"Auto Clear CDC Cheuqe Failed for: {payment.id}{payment.name}: Error: {e}")
        
        # _logger.info(f"\nAuto Clear Cheuqe Processed {len(cdc_payments)} CDC Payable Payments:  {cdc_payments.ids}")

    def action_draft(self):
        res = super().action_draft()
        for payment in self:
            payment.cheque_book_line_id = False
        return res
