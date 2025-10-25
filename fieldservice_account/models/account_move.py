# Copyright (C) 2018, Open Source Integrators
# Copyright 2019 Akretion <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from datetime import date


class AccountMove(models.Model):
    _inherit = "account.move"

    fsm_order_ids = fields.Many2many(
        "fsm.order",
        compute="_compute_fsm_order_ids",
        string="Field Service orders associated to this invoice",
        store=True
    )
    fsm_order_count = fields.Integer(
        string="FSM Orders", compute="_compute_fsm_order_ids"
    )
    supplier_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Supplier Currency',
        compute="_compute_bill_amount_currency", store=True)
    bill_amount_currency = fields.Monetary(string='Bill Amount Currency',
                            compute='_compute_bill_amount_currency',
                            store=True,
                            currency_field='supplier_currency_id',
                            )
    vendor_code = fields.Char(string='Vendor Code', related="partner_id.vendor_code", store=True)

    @api.depends('amount_residual_signed', 'partner_id', 'currency_id', 'company_currency_id', 'partner_id.property_purchase_currency_id')
    def _compute_bill_amount_currency(self):
        for rec in self:
            if rec.amount_residual_signed and rec.partner_id and rec.partner_id.property_purchase_currency_id:
                rec.supplier_currency_id = rec.partner_id.property_purchase_currency_id
                # currency = rec.partner_id.property_purchase_currency_id
                partner_currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=rec.company_currency_id,
                    to_currency=rec.supplier_currency_id,
                    company=rec.company_id,
                    date=rec._get_invoice_currency_rate_date(),
                )
                rec.bill_amount_currency = partner_currency_rate * rec.amount_residual_signed
                # rec.bill_amount_currency = rec.company_currency_id._convert(rec.amount_residual_signed, currency, rec.company_id, rec.date)
            else:
                rec.supplier_currency_id = False
                rec.bill_amount_currency = 0

    @api.depends("line_ids","fsm_order_ids","fsm_order_count")
    def _compute_fsm_order_ids(self):
        for record in self:
            orders = self.env["fsm.order"].search(
                [("invoice_lines", "in", record.line_ids.ids)]
            )
            record.fsm_order_ids = orders
            record.fsm_order_count = len(record.fsm_order_ids)

    def action_view_fsm_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "fieldservice.action_fsm_dash_order"
        )
        if self.fsm_order_count > 1:
            action["domain"] = [("id", "in", self.fsm_order_ids.ids)]
        elif self.fsm_order_ids:
            action["views"] = [(self.env.ref("fieldservice.fsm_order_form").id, "form")]
            action["res_id"] = self.fsm_order_ids[0].id
        return action
