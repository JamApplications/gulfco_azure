# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

bu_sales_field = ['customer_group_id',
                    'outlet_code',
                  'outlet_short_name',
                  'external_ref',
                  'sales_leader_id',
                  'collector_id',
                  'buyer_id',
                  'finance_manager_id',
                  'share_soa_email',
                  'share_invoice_email',
                  'latitude',
                  'longitude',
                  'partner_channel_id',
                  'outlet_id',
                  'sub_outlet_id']

bu_scm_field = [
    'delivery_receive_time'
]

ccd_fields = ['customer_name',
              'channel',
              'current_chanel',
              'current_sub_channel',
              'channel_mt',
              'channel_mt_hyper',
              'channel_mt_super',
              'channel_gt',
              'channel_gt_grocery',
              'channel_gt_cs',
              'channel_gt_super',
              'channel_gt_petrol',
              'channel_gt_discount',
              'channel_gt_wholesale',
              'channel_gt_tc',
              'channel_gt_sc',
              'channel_horeca',
              'channel_horeca_hr',
              'channel_horeca_rc',
              'channel_horeca_sa',
              'channel_horeca_caterings',
              'channel_horeca_tc',
              'channel_horeca_pc',
              'channel_ecom',
              'channel_ecom_mp',
              'channel_ecom_app',
              'channel_3pl',
              'detailed_address',
              'community_name',
              'city',
              'po_box',
              'emirate',
              'tl_issued_emirate',
              'trade_number',
              'establish_data',
              'tl_expiry_date',
              'category',
              'owner_name',
              'nationality_id',
              'owner_share',
              'vat_trn',
              'email',
              'credit_limit',
              'property_payment_term_id',
              'property_inbound_payment_method_line_id',
              'trade_license_attachment',
              'trade_license_file_name',
              'caf_attachment',
              'caf_file_name',
              'guarantees_copy_attachment',
              'guarantees_copy_file_name',
              'eid_attachment',
              'eid_file_name',
              'agreement_copy_attachment',
              'agreement_copy_file_name',
              'bank_statement_attachment',
              'bank_statement_file_name',
              'vat_trn_attachment',
              'vat_trn_file_name',
              'poer_attorney_attachment',
              'poer_attorney_file_name',
              'company_photo_attachment',
              'company_photo_file_name',
              'passport_copy_attachment',
              'passport_copy_file_name',
              'memorandum_association_attachment',
              'memorandum_association_file_name',
              'customer_type',
              'is_credit_hold',
              'credit_hold_reason_id',
              'delivery_receive_time',
              'is_key_account',
]

class CustomerAmendment(models.Model):
    _name = "customer.amendment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Customer Amendment"

    name = fields.Char(string="Name")
    partner_id = fields.Many2one('res.partner', string="Partner")
    company_id = fields.Many2one('res.company', related="partner_id.company_id", store=True)
    type = fields.Selection([('sales_amendment', 'Sales Amendment'), ('scm_amendment', 'SCM Amendment'),
                             ('ccd_amendment', 'CCD Amendment')], string="Type")
    bu_sales_state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_manager_approval','Waiting Manager Approval'),('manager_approval','Manager Approved'),
        ('channel_head_approved', 'Channel Head Approved'),
        ('division_head_approved', 'Division Head Approved'),
        ('reject','Reject')], default="draft", string="BU Sales State",tracking=True)
    bu_scm_state = fields.Selection([
        ('draft', 'Draft'),('waiting_ccd_officer_approval','Waiting CCD Officer Approval'),('ccd_officer_approval','CCD Officer Approved'),
        ('operation_manager_approved', 'Operational Manager Approved'),
        ('scm_approved', 'SCM Approved'),
        ('reject','Reject')], default="draft", string="BU SCM State",tracking=True)
    bu_ccd_state = fields.Selection([
        ('draft', 'Draft'),('waiting_ccd_officer_approval','Waiting CCD Officer Approval'),
        ('channel_head_approved', 'Channel Head Approved'),
        ('division_head_approved', 'Division Head Approved'),
        ('ccd_officer_approved', 'CCD Officer Approved'),
        ('ccd_approved', 'CCD Manager Approved'),
        ('reject','Reject')], default="draft", string="CCD State",tracking=True)
    is_ccd_officer_direct_approved = fields.Boolean(string="Is CCD Officer Direct Approved", default=False)

    # BU SALES FIELDS
    # customer_group = fields.Char(string="Customer Group")
    customer_group_id = fields.Many2one('customer.group', string="Customer Group")
    outlet_code = fields.Char(string="Customer Outlet Code")
    outlet_short_name = fields.Char(string="Outlet Short Name")
    external_ref = fields.Char(string="External Reference")
    sales_men_ids = fields.One2many('sales.men', 'cust_amendment_id', string="Salesman",)
    sales_leader_id = fields.Many2one('res.users', string="Supervisor/Salesman")
    collector_id = fields.Many2one('res.users', string="Collector")
    buyer_id = fields.Many2one('res.users', string="Buyer")
    finance_manager_id = fields.Many2one('res.users', string="Finance Manager")
    share_soa_email = fields.Char(string="Email ID to Share SOA")
    share_invoice_email = fields.Char(string="Email ID to Share Invoice")
    latitude = fields.Char(string="Latitude")
    longitude = fields.Char(string="Longitude")

    partner_channel_id = fields.Many2one(
        'channel.channel',
        string='Channel',
        tracking=True,
        required=False
    )

    outlet_id = fields.Many2one(
        'outlet.channel',
        string='Outlet Classification',
        domain="[('channel_name_id', '=', partner_channel_id)]",
        tracking=True,
        required=False
    )

    sub_outlet_id = fields.Many2one(
        'sub.outlet.channel',
        string='SubOutlet Classification',
        domain="[('outlet_id', '=', outlet_id)]",
        tracking=True,
        required=False
    )
    @api.onchange('partner_channel_id')
    def _onchange_partner_channel_id(self):
        self.outlet_id = False
        self.sub_outlet_id = False

    @api.onchange('outlet_id')
    def _onchange_outlet_id(self):
        self.sub_outlet_id = False


    # BU SALES Prevous Fields

    # prev_customer_group = fields.Char(string="Previous Customer Group")
    prev_customer_group_id = fields.Many2one('customer.group', string="Customer Group")
    prev_outlet_code = fields.Char(string="Previous Customer Outlet Code")
    prev_outlet_short_name = fields.Char(string="Previous Outlet Short Name")
    prev_external_ref = fields.Char(string="Previous External Reference")
    prev_sales_leader_id = fields.Many2one('res.users', string="Previous Supervisor/Salesman")
    prev_collector_id = fields.Many2one('res.users', string="Previous Collector")
    prev_buyer_id = fields.Many2one('res.users', string="Previous Buyer")
    prev_finance_manager_id = fields.Many2one('res.users', string="Previous Finance Manager")
    prev_share_soa_email = fields.Char(string="Previous SOA Email")
    prev_share_invoice_email = fields.Char(string="Previous Invoice Email")
    prev_latitude = fields.Char(string="Previous Latitude")
    prev_longitude = fields.Char(string="Previous Longitude")

    prev_partner_channel_id = fields.Many2one(
        'channel.channel',
        string='Channel',
        tracking=True,
        required=False
    )

    prev_outlet_id = fields.Many2one(
        'outlet.channel',
        string='Outlet Classification',
        domain="[('channel_name_id', '=', prev_partner_channel_id)]",
        tracking=True,
        required=False
    )

    prev_sub_outlet_id = fields.Many2one(
        'sub.outlet.channel',
        string='SubOutlet Classification',
        domain="[('outlet_id', '=', prev_outlet_id)]",
        tracking=True,
        required=False
    )
    # BU SCM FIELDS
    delivery_receive_time = fields.Datetime(string="Delivery Receive Time")

    # BU SCM Previous Fields
    prev_delivery_receive_time = fields.Datetime(string="Previous Delivery Receive Time")

    # CCD FIELDS

    customer_name = fields.Char(string="Customer Name")
    channel = fields.Selection([
        ('MT', 'MT'),
        ('GT', 'GT'),
        ('HORECA', 'HORECA'),
        ('E-Com', 'E-Com'),
        ('3PL', '3PL'),
    ], string='Channel')

    # current_chanel
    current_chanel = fields.Selection([
        ('MT', 'MT'),
        ('GT', 'GT'),
        ('HORECA', 'HORECA'),
        ('E-Com', 'E-Com'),
        ('3PL', '3PL'),
    ], string='Current Channel')

    current_sub_channel = fields.Text()

    # Channel MT
    channel_mt = fields.Selection([('HyperMarket', 'Hyper Market'), ('SuperMarket', 'Super Market')])
    channel_mt_hyper = fields.Selection([('ChainHM', 'Chain HM'), ('COOP', 'COOP')])
    channel_mt_super = fields.Selection([('ChainSM', 'Chain SM'), ('COOP', 'COOP')])
    # Chanel GT
    channel_gt = fields.Selection(
        [('Grocery', 'Grocery'), ('ConvenienceStore', 'Convenience Store'), ('Supermarket', 'Supermarket'),
         ('PetrolStation', 'Petrol Station'), ('DiscountCenter', 'Discount Center'), ('Wholesale', 'Wholesale'),
         ('TradingCompany', 'Trading Company'), ('SpecialAccounts', 'Special Accounts')])
    channel_gt_grocery = fields.Selection(
        [('GroceryA', 'Grocery A'), ('GroceryB', 'Grocery B'), ('GroceryC', 'Grocery C')])
    channel_gt_cs = fields.Selection(
        [('ConvenienceA', 'Convenience A'), ('ConvenienceB', 'Convenience B'), ('PetrolStation-A', 'Petrol Station-A'),
         ('PetrolStation-B', 'Petrol Station-B'), ('PetrolStation-C', 'Petrol Station-C')])
    channel_gt_super = fields.Selection([('SM-A', 'SM-A'), ('SM-B', 'SM-B'), ('COOP', 'COOP')])
    channel_gt_petrol = fields.Selection([('PS-A', 'PS-A'), ('PS-B', 'PS-B'), ('PS-C', 'PS-C')])
    channel_gt_discount = fields.Selection([('DiscountCenter', 'Discount Center')])
    channel_gt_wholesale = fields.Selection([('Wholesale', 'Wholesale')])
    channel_gt_tc = fields.Selection([('TradingCompany', 'Trading Company'), ('Roasteries', 'Roasteries')])
    channel_gt_sc = fields.Selection(
        [('Pharmacy', 'Pharmacy'), ('Roasteries', 'Roasteries'), ('ShipChandlers', 'Ship Chandlers'),
         ('Others', 'Others')])

    # Channel HORECA
    channel_horeca = fields.Selection(
        [('HotelsandResorts', 'Hotels and Resorts'), ('RestaurantandCafe', 'Restaurant and Cafe'),
         ('SpecialAccount', 'Special Account'), ('Caterings', 'Caterings'),
         ('HORECATradingCompany', 'HORECA Trading Company'), ('PubsandClubs', 'Pubs and Clubs')])

    channel_horeca_hr = fields.Selection([('Chain', 'Chain'), ('Single', 'Single')])
    channel_horeca_rc = fields.Selection([('Chain', 'Chain'), ('Single', 'Single')])
    channel_horeca_sa = fields.Selection(
        [('AirportLounge', 'Airport Lounge'), ('SportsLeisures', 'Sports Leisures'), ('Roasteries', 'Roasteries'),
         ('Education', 'Education'), ('GovernmentEntities', 'Government Entities'), ('JAMGroup', 'JAM Group'),
         ('Cinemas', 'Cinemas'), ('Hospitals', 'Hospitals'), ('Pharmacy', 'Pharmacy'),
         ('ShipChandlers', 'Ship Chandlers'), ('Others', 'Others')])
    channel_horeca_caterings = fields.Selection(
        [('Caterings', 'Caterings'), ('Airlines', 'Airlines')])
    channel_horeca_tc = fields.Selection([('HORECATradingCompany', 'HORECA Trading Company')])
    channel_horeca_pc = fields.Selection([('PubsandClubs', 'Pubs and Clubs')])
    # Channel Com
    channel_ecom = fields.Selection([('OnlineMarketPlace', 'Online Market Place'), ('DeliveryApps', 'Delivery Apps')])

    channel_ecom_mp = fields.Selection([('OnlineMarketPlace', 'Online Market Place')])
    channel_ecom_app = fields.Selection([('DeliveryApps', 'Delivery Apps')])

    # Channel 3PL
    channel_3pl = fields.Selection([('Sales', 'Sales'), ('Logistic', 'Logistic')])
    detailed_address = fields.Text(string="Detailed Address")
    community_name = fields.Text(string="Province / Community Name")
    city = fields.Char(string="City")
    po_box = fields.Char(string="P.O Box")
    emirate = fields.Char(string="Emirate ID")
    tl_issued_emirate = fields.Char(string="TL issued From Emirates")
    trade_number = fields.Char(string="Trade License Number")
    establish_data = fields.Text(string="Establish Data")
    tl_expiry_date = fields.Date(string="TL Expiry Date")
    category = fields.Char(string="Category")
    owner_name = fields.Char(string="Owner Name")
    nationality_id = fields.Many2one('res.country', string="Nationality")
    owner_share = fields.Integer(string="Owner Share %")
    vat_trn = fields.Char(string="TRN No")
    email = fields.Char(string="Email")
    credit_limit = fields.Float(string="Credit Limit")
    property_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True,
                                               string='Customer Payment Terms',
                                               help="This payment term will be used instead of the default one for sales orders and customer invoices",
                                               ondelete='restrict')
    property_inbound_payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        company_dependent=True,
        domain=lambda self: [('payment_type', '=', 'inbound'), ('company_id', '=', self.env.company.id)],
        help="Preferred payment method when selling to this customer. This will be set by default on all"
             " incoming payments created for this customer",
    )
    is_credit_hold = fields.Boolean(string="Is Credit Hold")
    prev_is_credit_hold = fields.Boolean(string="Is Prev Credit Hold")

    credit_hold_reason_id = fields.Many2one(
        'credit.hold.reason',
        string='Credit Hold Reason',
    )
    prev_credit_hold_reason_id = fields.Many2one(
        'credit.hold.reason',
        string='Credit Hold Reason',
    )
    credit_hold_reason = fields.Text(string="Describe Reason")
    prev_credit_hold_reason = fields.Text(string="Prev Describe Reason")

    is_key_account = fields.Boolean('Key account classification')
    prev_is_key_account = fields.Boolean('Prev Key account classification')



    # CCD Previous Fields

    # Basic CCD Fields
    prev_customer_name = fields.Char(string="Previous Customer Name")
    prev_channel = fields.Selection([
        ('MT', 'MT'),
        ('GT', 'GT'),
        ('HORECA', 'HORECA'),
        ('E-Com', 'E-Com'),
        ('3PL', '3PL'),
    ], string="Previous Channel")

    # Channel MT
    prev_channel_mt = fields.Selection([
        ('HyperMarket', 'Hyper Market'),
        ('SuperMarket', 'Super Market')
    ], string="Previous Channel MT")

    prev_channel_mt_hyper = fields.Selection([
        ('ChainHM', 'Chain HM'),
        ('COOP', 'COOP')
    ], string="Previous MT Hyper Market")

    prev_channel_mt_super = fields.Selection([
        ('ChainSM', 'Chain SM'),
        ('COOP', 'COOP')
    ], string="Previous MT Super Market")

    # Channel GT
    prev_channel_gt = fields.Selection([
        ('Grocery', 'Grocery'),
        ('ConvenienceStore', 'Convenience Store'),
        ('Supermarket', 'Supermarket'),
        ('PetrolStation', 'Petrol Station'),
        ('DiscountCenter', 'Discount Center'),
        ('Wholesale', 'Wholesale'),
        ('TradingCompany', 'Trading Company'),
        ('SpecialAccounts', 'Special Accounts')
    ], string="Previous Channel GT")

    prev_channel_gt_grocery = fields.Selection([
        ('GroceryA', 'Grocery A'),
        ('GroceryB', 'Grocery B'),
        ('GroceryC', 'Grocery C')
    ], string="Previous GT Grocery")

    prev_channel_gt_cs = fields.Selection(
        [('ConvenienceA', 'Convenience A'), ('ConvenienceB', 'Convenience B'), ('PetrolStation-A', 'Petrol Station-A'),
         ('PetrolStation-B', 'Petrol Station-B'), ('PetrolStation-C', 'Petrol Station-C')])

    prev_channel_gt_super = fields.Selection([
        ('SM-A', 'SM-A'),
        ('SM-B', 'SM-B'),
        ('COOP', 'COOP')
    ], string="Previous GT Supermarket")

    prev_channel_gt_petrol = fields.Selection([
        ('PS-A', 'PS-A'),
        ('PS-B', 'PS-B'),
        ('PS-C', 'PS-C')
    ], string="Previous GT Petrol Station")

    prev_channel_gt_discount = fields.Selection([
        ('DiscountCenter', 'Discount Center')
    ], string="Previous GT Discount Center")

    prev_channel_gt_wholesale = fields.Selection([
        ('Wholesale', 'Wholesale')
    ], string="Previous GT Wholesale")

    prev_channel_gt_tc = fields.Selection([
        ('TradingCompany', 'Trading Company'),
        ('Roasteries', 'Roasteries')
    ], string="Previous GT Trading Company")

    prev_channel_gt_sc = fields.Selection([
        ('Pharmacy', 'Pharmacy'),
        ('Roasteries', 'Roasteries'),
        ('ShipChandlers', 'Ship Chandlers'),
        ('Others', 'Others')
    ], string="Previous GT Special Accounts")

    # Channel HORECA
    prev_channel_horeca = fields.Selection([
        ('HotelsandResorts', 'Hotels and Resorts'),
        ('RestaurantandCafe', 'Restaurant and Cafe'),
        ('SpecialAccount', 'Special Account'),
        ('Caterings', 'Caterings'),
        ('HORECATradingCompany', 'HORECA Trading Company'),
        ('PubsandClubs', 'Pubs and Clubs')
    ], string="Previous Channel HORECA")

    prev_channel_horeca_hr = fields.Selection([
        ('Chain', 'Chain'),
        ('Single', 'Single')
    ], string="Previous HORECA Hotels and Resorts")

    prev_channel_horeca_rc = fields.Selection([
        ('Chain', 'Chain'),
        ('Single', 'Single')
    ], string="Previous HORECA Restaurant and Cafe")

    prev_channel_horeca_sa = fields.Selection([
        ('AirportLounge', 'Airport Lounge'),
        ('SportsLeisures', 'Sports Leisures'),
        ('Roasteries', 'Roasteries'),
        ('Education', 'Education'),
        ('GovernmentEntities', 'Government Entities'),
        ('JAMGroup', 'JAM Group'),
        ('Cinemas', 'Cinemas'),
        ('Hospitals', 'Hospitals'),
        ('Pharmacy', 'Pharmacy'),
        ('ShipChandlers', 'Ship Chandlers'),
        ('Others', 'Others')
    ], string="Previous HORECA Special Account")

    prev_channel_horeca_caterings = fields.Selection([
        ('Caterings', 'Caterings'),
        ('Airlines', 'Airlines')
    ], string="Previous HORECA Caterings")

    prev_channel_horeca_tc = fields.Selection([
        ('HORECATradingCompany', 'HORECA Trading Company')
    ], string="Previous HORECA Trading Company")

    prev_channel_horeca_pc = fields.Selection([
        ('PubsandClubs', 'Pubs and Clubs')
    ], string="Previous HORECA Pubs and Clubs")

    # Channel E-Com
    prev_channel_ecom = fields.Selection([
        ('OnlineMarketPlace', 'Online Market Place'),
        ('DeliveryApps', 'Delivery Apps')
    ], string="Previous Channel E-Com")

    prev_channel_ecom_mp = fields.Selection([
        ('OnlineMarketPlace', 'Online Market Place')
    ], string="Previous E-Com Marketplace")

    prev_channel_ecom_app = fields.Selection([
        ('DeliveryApps', 'Delivery Apps')
    ], string="Previous E-Com Delivery App")

    # Channel 3PL
    prev_channel_3pl = fields.Selection([
        ('Sales', 'Sales'),
        ('Logistic', 'Logistic')
    ], string="Previous Channel 3PL")

    # CCD Basic Info
    prev_detailed_address = fields.Text(string="Previous Detailed Address")
    prev_community_name = fields.Text(string="Previous Province / Community Name")
    prev_city = fields.Char(string="Previous City")
    prev_po_box = fields.Char(string="Previous P.O Box")
    prev_emirate = fields.Char(string="Previous Emirate ID")
    prev_tl_issued_emirate = fields.Char(string="Previous TL issued From Emirates")
    prev_trade_number = fields.Char(string="Previous Trade License Number")
    prev_establish_data = fields.Text(string="Previous Establish Data")
    prev_tl_expiry_date = fields.Date(string="Previous TL Expiry Date")
    prev_category = fields.Char(string="Previous Category")
    prev_owner_name = fields.Char(string="Previous Owner Name")
    prev_nationality_id = fields.Many2one('res.country', string="Previous Nationality")
    prev_owner_share = fields.Integer(string="Previous Owner Share %")
    prev_vat_trn = fields.Char(string="Previous TRN No")
    prev_email = fields.Char(string="Previous Email")
    prev_credit_limit = fields.Float(string="Previous Credit Limit")
    prev_property_payment_term_id = fields.Many2one('account.payment.term', string="Previous Payment Terms")
    prev_property_inbound_payment_method_line_id = fields.Many2one('account.payment.method.line',
                                                                   string="Previous Payment Method")

    # Document attachment fields - Current
    trade_license_attachment = fields.Binary(string="Trade License Attachment")
    trade_license_file_name = fields.Char(string="Trade License File Name")

    caf_attachment = fields.Binary(string="CAF Attachment")
    caf_file_name = fields.Char(string="CAF File Name")

    guarantees_copy_attachment = fields.Binary(string="Guarantees Copy Attachment")
    guarantees_copy_file_name = fields.Char(string="Guarantees Copy File Name")

    eid_attachment = fields.Binary(string="Emirates ID Attachment")
    eid_file_name = fields.Char(string="Emirates ID File Name")

    agreement_copy_attachment = fields.Binary(string="Agreement Copy Attachment")
    agreement_copy_file_name = fields.Char(string="Agreement Copy File Name")

    bank_statement_attachment = fields.Binary(string="Bank Statement Attachment")
    bank_statement_file_name = fields.Char(string="Bank Statement File Name")

    vat_trn_attachment = fields.Binary(string="VAT TRN Attachment")
    vat_trn_file_name = fields.Char(string="VAT TRN File Name")

    poer_attorney_attachment = fields.Binary(string="Power of Attorney Attachment")
    poer_attorney_file_name = fields.Char(string="Power of Attorney File Name")

    company_photo_attachment = fields.Binary(string="Company Photo Attachment")
    company_photo_file_name = fields.Char(string="Company Photo File Name")

    passport_copy_attachment = fields.Binary(string="Passport Copy Attachment")
    passport_copy_file_name = fields.Char(string="Passport Copy File Name")

    memorandum_association_attachment = fields.Binary(string="Memorandum of Association Attachment")
    memorandum_association_file_name = fields.Char(string="Memorandum of Association File Name")
    customer_type = fields.Selection([('cash', 'Cash'), ('credit', 'Credit')], string="Customer Type", tracking=True)

    # Document attachment fields - Previous
    prev_trade_license_attachment = fields.Binary(string="Previous Trade License Attachment")
    prev_trade_license_file_name = fields.Char(string="Previous Trade License File Name")

    prev_caf_attachment = fields.Binary(string="Previous CAF Attachment")
    prev_caf_file_name = fields.Char(string="Previous CAF File Name")

    prev_guarantees_copy_attachment = fields.Binary(string="Previous Guarantees Copy Attachment")
    prev_guarantees_copy_file_name = fields.Char(string="Previous Guarantees Copy File Name")

    prev_eid_attachment = fields.Binary(string="Previous Emirates ID Attachment")
    prev_eid_file_name = fields.Char(string="Previous Emirates ID File Name")

    prev_agreement_copy_attachment = fields.Binary(string="Previous Agreement Copy Attachment")
    prev_agreement_copy_file_name = fields.Char(string="Previous Agreement Copy File Name")

    prev_bank_statement_attachment = fields.Binary(string="Previous Bank Statement Attachment")
    prev_bank_statement_file_name = fields.Char(string="Previous Bank Statement File Name")

    prev_vat_trn_attachment = fields.Binary(string="Previous VAT TRN Attachment")
    prev_vat_trn_file_name = fields.Char(string="Previous VAT TRN File Name")

    prev_poer_attorney_attachment = fields.Binary(string="Previous Power of Attorney Attachment")
    prev_poer_attorney_file_name = fields.Char(string="Previous Power of Attorney File Name")

    prev_company_photo_attachment = fields.Binary(string="Previous Company Photo Attachment")
    prev_company_photo_file_name = fields.Char(string="Previous Company Photo File Name")

    prev_passport_copy_attachment = fields.Binary(string="Previous Passport Copy Attachment")
    prev_passport_copy_file_name = fields.Char(string="Previous Passport Copy File Name")

    prev_memorandum_association_attachment = fields.Binary(string="Previous Memorandum of Association Attachment")
    prev_memorandum_association_file_name = fields.Char(string="Previous Memorandum of Association File Name")
    prev_customer_type = fields.Selection([('cash', 'Cash'), ('credit', 'Credit')], string="Customer Type")

    @api.onchange('channel')
    def _get_current_chanel(self):
        self.current_chanel = self.channel

    @api.onchange('channel_mt')
    def _get_mt_current_sub_channel_1(self):
        """ Get the selected value from the changed channel field and set it in `current_chanel_1` """
        if self.channel_mt:
            self.current_sub_channel = self.channel_mt

    @api.onchange('channel_gt')
    def _get_gt_current_sub_channel_1(self):
        """ Get the selected value from the changed channel field and set it in `current_chanel_1` """
        if self.channel_gt:
            self.current_sub_channel = self.channel_gt

    @api.onchange('channel_horeca')
    def _get_horeca_current_sub_channel_1(self):
        """ Get the selected value from the changed channel field and set it in `current_chanel_1` """
        if self.channel_horeca:
            self.current_sub_channel = self.channel_horeca

    @api.onchange('channel_3pl')
    def _get_pl_current_sub_channel_1(self):
        """ Get the selected value from the changed channel field and set it in `current_chanel_1` """
        if self.channel_3pl:
            self.current_sub_channel = self.channel_3pl

    @api.onchange('channel_ecom')
    def _get_ecom_current_sub_channel_1(self):
        """ Get the selected value from the changed channel field and set it in `current_chanel_1` """
        if self.channel_ecom:
            self.current_sub_channel = self.channel_ecom


    # new changes

    def action_submit_bu_sales(self):
        if self.type == 'sales_amendment' and self.bu_sales_state == 'draft':
            self.bu_sales_state = 'waiting_manager_approval'

    def action_channel_head_bu_sales_approved(self):
        if self.type == 'sales_amendment' and self.bu_sales_state == 'draft':
            self.bu_sales_state = 'channel_head_approved'

    def action_reject_bu_sales(self):
        if self.type == 'sales_amendment':
            self.bu_sales_state = 'reject'

    def action_manager_approve_bu_sales(self):
        if self.type == 'sales_amendment' and self.bu_sales_state == 'waiting_manager_approval':
            self.bu_sales_state = 'manager_approval'
            data = self.read(bu_sales_field)[0]
            data.pop('id')
            filtered_data = {k: v for k, v in data.items() if v not in (False, None, [], 0)}
            self.partner_id.sudo().with_context(from_customer_amendment=True).write(filtered_data)

    # new changes

    def action_submit_bu_scm(self):
        if self.type == 'scm_amendment' and self.bu_sales_state == 'draft':
            self.bu_scm_state = 'waiting_ccd_officer_approval'


    def action_operational_manager_bu_scm_approved(self):
        if self.type == 'scm_amendment':
            self.bu_scm_state = 'operation_manager_approved'

    def action_reject_bu_scm(self):
        if self.type == 'scm_amendment':
            self.bu_scm_state = 'reject'

    def action_ccd_officer_bu_scm(self):
        if self.type == 'scm_amendment' and self.bu_scm_state == 'waiting_ccd_officer_approval':
            self.bu_scm_state = 'ccd_officer_approval'
            data = self.read(bu_scm_field)[0]
            data.pop('id')
            filtered_data = {k: v for k, v in data.items() if v not in (False, None, [], 0)}
            self.partner_id.sudo().with_context(from_customer_amendment=True).write(filtered_data)

    def action_channel_head_ccd_approved(self):
        if self.type == 'ccd_amendment':
            self.bu_ccd_state = 'channel_head_approved'

    def action_reject_ccd(self):
        if self.type == 'ccd_amendment':
            self.bu_ccd_state = 'reject'

    def action_division_head_ccd_approved(self):
        if self.type == 'ccd_amendment':
            self.bu_ccd_state = 'division_head_approved'    

    # ccd
    def submit_to_ccd_officer_approval(self):
        if self.type == 'ccd_amendment' and self.bu_ccd_state == 'draft':
            self.bu_ccd_state = 'waiting_ccd_officer_approval'

    def action_ccd_officer_approve(self):
        if self.type == 'ccd_amendment' and self.bu_ccd_state == 'waiting_ccd_officer_approval':
            self.bu_ccd_state = 'ccd_officer_approved'
            # Only require CCD Manager approval if these fields are changed
            ccd_manager_fields = [
                'property_payment_term_id',
                'property_inbound_payment_method_line_id',
                'credit_limit',
                'name',
                'owner_name',
                'nationality_id',
                'owner_share'
            ]
            data = self.read(ccd_fields)[0]
            data.pop('id')
            filtered_data = {k: v for k, v in data.items() if v not in (False, None, [], 0)}
            if filtered_data.get('customer_name'):
                name = filtered_data.pop('customer_name')
                filtered_data.update({'name':name})
            for field in ccd_manager_fields:
                if field in filtered_data and filtered_data[field] != getattr(self.partner_id, field, False):
                    return
            self.is_ccd_officer_direct_approved = True
            self.partner_id.sudo().with_context(from_customer_amendment=True).write(filtered_data)

    def action_ccd_approved(self):
        if self.type == 'ccd_amendment' and self.bu_ccd_state == 'ccd_officer_approved':
            self.bu_ccd_state = 'ccd_approved'
            data = self.read(ccd_fields)[0]
            data.pop('id')
            filtered_data = {k: v for k, v in data.items() if v not in (False, None, [], 0)}
            if filtered_data.get('customer_name'):
                name = filtered_data.pop('customer_name')
                filtered_data.update({'name':name})
            self.partner_id.sudo().with_context(from_customer_amendment=True).write(filtered_data)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        partner_id = self.env.context.get('default_partner_id')
        if partner_id and 'type' in res and res.get('type'):
            partner = self.env['res.partner'].browse(partner_id)
            if res.get('type') == 'sales_amendment':
                for field in bu_sales_field :
                    prev_field = f'prev_{field}'
                    if prev_field in self._fields and hasattr(partner, field):
                        res[prev_field] = getattr(partner, field)
            elif res.get('type') == 'scm_amendment':
                for field in bu_scm_field :
                    prev_field = f'prev_{field}'
                    if prev_field in self._fields and hasattr(partner, field):
                        res[prev_field] = getattr(partner, field)
            elif res.get('type') == 'ccd_amendment':
                for field in ccd_fields :
                    prev_field = f'prev_{field}'
                    if prev_field in self._fields and hasattr(partner, field):
                        res[prev_field] = getattr(partner, field)
                    elif field == 'customer_name':
                        res[prev_field] = getattr(partner, 'name')
        return res




