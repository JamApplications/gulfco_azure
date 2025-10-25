from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta



class TLLicenceExpiryReport(models.Model):
    _name = 'tl.expiry.report'
    _description = 'TL Expiry Customer Report'
    _auto = False
    _order = 'tl_expiry_date'

    customer_id = fields.Many2one('res.partner', string='Customer')
    customer_name = fields.Char('Customer Name')
    customer_code = fields.Char('Customer Code')
    trade_number = fields.Char(related='customer_id.trade_number')
    tl_expiry_date = fields.Date('TL Expiry Date')
    is_credit_hold = fields.Boolean('Credit Hold')
    credit_hold_reason = fields.Char('Hold Reason')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    expiry_status = fields.Selection([
        ('expired', 'Expired'),
        ('expiring_soon', 'Expiring Soon'),
        ('valid', 'Valid'),
    ], string='Expiry Status',  compute='_compute_status', store=False)

    @api.depends('tl_expiry_date')
    def _compute_status(self):
        today = fields.Date.today()
        for rec in self:
            if rec.tl_expiry_date:
                if rec.tl_expiry_date < today:
                    rec.expiry_status = 'expired'
                elif today <= rec.tl_expiry_date <= today + relativedelta(days=30):
                    rec.expiry_status = 'expiring_soon'
                else:
                    rec.expiry_status = 'valid'
            else:
                rec.status = False

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW tl_expiry_report AS (
                SELECT 
                    rp.id AS id,
                    rp.id AS customer_id,
                    rp.name AS customer_name,
                    rp.ref AS customer_code,
                    rp.tl_expiry_date,
                    rp.is_credit_hold,
                    ch.name AS credit_hold_reason,
                    rp.email,
                    rp.phone
                FROM res_partner rp
                LEFT JOIN credit_hold_reason ch ON rp.credit_hold_reason_id = ch.id
                WHERE 
                    rp.customer_rank > 0
                    AND rp.contact_type = 'customer'
                    AND rp.tl_expiry_date IS NOT NULL
                    AND (
                        rp.tl_expiry_date < CURRENT_DATE -- expired
                        OR
                        rp.tl_expiry_date BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '30 days') -- near expiry
                    )
            );
        """)


