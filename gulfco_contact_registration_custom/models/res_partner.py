from email.policy import default

from png import Default

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
# from odoo import exceptions


class ResPartner(models.Model):
    _inherit = 'res.partner'

    registration_type = fields.Selection([('vendor_registration', 'Vendor Registration'), ('customer_registration', 'Customer Registration')])
    customer_type = fields.Selection([('cash', 'Cash'), ('credit', 'Credit')], tracking=True)

    unregistered_bank = fields.Char(string="Unregistered Bank", help="If the bank was not found in the list")
    vendor_code = fields.Char(string='Vendor Code', index=True)

    vendor_state = fields.Selection([('draft', 'Draft'),
        ('supplier_create_request', 'Supplier Creation Request'),
        ('scm_approved', 'SCM Approved'),
        ('finance_approved', 'Finance Approved'),
        ('director_approved', 'Director Approved'),
        ('vendor_scd_approved','SCD Staff Approved'),
        ('manager_scd_approved','SCD manger Approved')
        ],
        default='draft',  tracking=True, copy=False)



    is_scd_user = fields.Boolean()
    scd_manager_id = fields.Many2one('res.users')
    credit_limit = fields.Float(
        string='Credit Limit', help='Credit limit specific to this partner.',
        groups='account.group_account_invoice,account.group_account_readonly',
        company_dependent=True, copy=False, readonly=False, tracking=True)
    mobile = fields.Char(required=False)
    use_partner_credit_limit = fields.Boolean(
        string='Credit Limit',
    )


    customer_cash_state = fields.Selection(
        [('customer_create_request', 'Draft Customer Creation Request'), ('waiting_manager_approval', 'Waiting Manager Approval'), ('sales_dep_approved', 'Sales Dep. Approved'),
         ('auth_user_confirmed', 'Confirmed'),  ('manager_approved', ' Manager Confirmed'),
         ('channel_head_approved', 'Channel Head Approved'),], default='customer_create_request',  tracking=True,)

    customer_credit_state = fields.Selection(
        [('customer_create_request', 'Draft Customer Creation Request'), ('waiting_ccd_officer_approval', 'Waiting CCD Officer Approval'), ('sales_dep_approved', 'Sales Dep. Approved'),
         ('auth_user_confirmed', 'Confirmed'), ('manager_approved', ' Manager Confirmed'),
         ('credit_officer_approved', 'Credit Officer Approved'), ('channel_head_approved', 'Channel Head Approved'),
         ('div_head_approved', 'Div Head Approved'), ('ccd_approved', 'Approved'),], default='customer_create_request',  tracking=True,)

    is_auth_manager = fields.Boolean(Default=False)
    manager_id = fields.Many2one('res.users')

    # change
    def action_submit_cash_customer_creation_button(self):
        self.customer_cash_state= 'waiting_manager_approval'
    # change
    def action_submit_credit_customer_creation_button(self):
        self.customer_credit_state= 'waiting_ccd_officer_approval'


    # change
    def action_draft_cash_customer_creation(self):
        self.customer_cash_state= 'customer_create_request'

    # change
    def action_draft_credit_customer_creation(self):
        self.customer_create_request= 'customer_create_request'

    # Vendor Approvals methods
    def action_reject_button(self):
        self.vendor_state = 'draft'

    def submit_registration_button(self):
        self.vendor_state = 'supplier_create_request'

    def scm_approve_button(self):
        self.vendor_state = 'scm_approved'

    def finance_approve_button(self):
        self.vendor_state = 'finance_approved'


    def director_approve_button(self):
        self.vendor_state = 'director_approved'

    def vendor_scd_approve_button(self):
        self.vendor_state = 'vendor_scd_approved'
        self.scd_manager_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)]).parent_id.user_id.id
        if self.scd_manager_id:
            self.is_scd_user = True
        else:
            raise ValidationError("Please assign manager to SCD approval User!")

    def scd_manager_approve_button(self):
        self.vendor_code = self.env['ir.sequence'].next_by_code("vendor.registration.code") or _('New')
        self.write({
            'vendor_state': 'manager_scd_approved',
            'active': True,
        })

    # change
    # Customer Cash Approvals methods
    def sales_cash_approve_button(self):
        self.customer_cash_state = 'sales_dep_approved'

    def auth_user_cash_approve_button(self):
        self.customer_cash_state = 'auth_user_confirmed'
        self.manager_id = self.env['hr.employee'].search([('user_id','=',self.env.user.id)]).parent_id.user_id.id
        if self.manager_id:
            self.is_auth_manager = True
        else:
            raise ValidationError("Please assign manager to Authorized User!")

    # change
    # def manager_cash_approve_button(self):
    #     self.customer_cash_state = 'manager_approved'

    def manager_cash_approve_button(self):
    # def channel_head_cash_approve_button(self):
        # self.customer_cash_state = 'channel_head_approved'
        self.customer_cash_state = 'manager_approved'
        self.active = True
        if not self.parent_id:
            # self.customer_code = self.env['ir.sequence'].next_by_code("customer.code.seq") or _('New')
            self.customer_code = self.env['ir.sequence'].next_by_code("cash.customer.code.seq") or _('New')
        else:
            parent_code = self.parent_id.customer_code
            if parent_code:
                # raise UserError("Parent customer does not have a customer code. Please assign one before proceeding.")

                existing_children = self.search([
                    ('parent_id', '=', self.parent_id.id),
                    ('customer_code', 'like', self.parent_id.customer_code + '-%'),
                    ('id', '!=', self.id or 0)  # Exclude current record if it exists
                ], order='customer_code desc')

                if existing_children:
                    # Get highest existing suffix number
                    last_suffix = existing_children[0].customer_code.split('-')[-1]
                    try:
                        next_num = int(last_suffix) + 1
                        next_suffix = f"{next_num:02d}"  # Format with leading zero
                    except ValueError:
                        # Handle case where suffix isn't numeric
                        next_suffix = '01'
                else:
                    next_suffix = '01'

                self.customer_code = f"{self.parent_id.customer_code}-{next_suffix}"


    # Customer Credit Approvals methods
    def sales_credit_approve_button(self):
        self.customer_credit_state = 'sales_dep_approved'

    def auth_user_credit_approve_button(self):
        self.customer_credit_state = 'auth_user_confirmed'
        self.manager_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)]).parent_id.user_id.id
        if self.manager_id:
            self.is_auth_manager = True
        else:
            raise ValidationError("Please assign manager to Authorized User!")

    def manager_credit_approve_button(self):
        self.customer_credit_state = 'manager_approved'
    # parent_id
    def credit_officer_approve_button(self):
        if self.parent_id:
            self.ccd_credit_approve_button()
        else:
            self.customer_credit_state = 'credit_officer_approved'

    def channel_head_credit_approve_button(self):
        self.customer_credit_state = 'channel_head_approved'

    def div_head_credit_approve_button(self):
        self.customer_credit_state = 'div_head_approved'

    def ccd_credit_approve_button(self):
        self.customer_credit_state = 'ccd_approved'
        self.active = True
        if not self.parent_id:
            # self.customer_code = self.env['ir.sequence'].next_by_code("customer.code.seq") or _('New')
            self.customer_code = self.env['ir.sequence'].next_by_code("credit.customer.code.seq") or _('New')
        else:
            parent_code = self.parent_id.customer_code
            if parent_code:
                existing_children = self.search([
                    ('parent_id', '=', self.parent_id.id),
                    ('customer_code', 'like', self.parent_id.customer_code),
                    ('id', '!=', self.id or 0)  # Exclude current record if it exists
                ], order='customer_code desc')

                if existing_children:
                    # Get highest existing suffix number
                    last_suffix = existing_children[0].customer_code.split('-')[-1]
                    try:
                        next_num = int(last_suffix) + 1
                        next_suffix = f"{next_num:02d}"  # Format with leading zero
                    except ValueError:
                        # Handle case where suffix isn't numeric
                        next_suffix = '01'
                else:
                    next_suffix = '01'

                self.customer_code = f"{self.parent_id.customer_code}-{next_suffix}"
