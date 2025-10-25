from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_group = fields.Char(string="Customer Group")
    customer_group_id = fields.Many2one('customer.group',string="Customer Group")
    is_van_sale_customer = fields.Boolean(string="Is Van Sale Customer", required=False)
    external_ref = fields.Char(string="External Reference")

    # Related
    collector_id = fields.Many2one('res.users', string="Collector")

    customer_code = fields.Char(string='Customer Code', copy=False)
    makani_code = fields.Char(string='MAKANI Code', copy=False)
    create_source = fields.Selection([('backend', 'Backend'), ('portal', 'Portal')], default='backend',string='Create Source', copy=False)

    

    sales_leader_id = fields.Many2one('res.users', string="Supervisor / Salesman") #, required=False)


    sales_men_ids = fields.One2many('sales.men', 'sales_partner_id' , string="Salesman",) #required=False)

    sales_man_id = fields.Many2one('res.users', string="Salesman")
    sales_man_contact = fields.Char(related='sales_man_id.phone', )
    sales_man_email = fields.Char(related='sales_man_id.email')

    outlet_code = fields.Char(string="Customer Outlet Code", required=False)
    outlet_short_name = fields.Char(string="Outlet Short Name", required=False)

    owner_name = fields.Char(string="Owner Name")
    owner_share = fields.Integer(string="Owner Share %")

    po_box = fields.Char(string="P.O Box", required=False)
    detailed_address = fields.Text(string="Detailed Address", required=False)
    community_name = fields.Text(string="Province / Community Name", required=False)
    worker_code = fields.Char(string="Worker Code")
    previous_credit_limit = fields.Float(
        string='Previous Credit Limit',
        company_dependent=True, copy=False)
    
    customer_class_id = fields.Many2one('customer.class', string="Customer Class")
    customer_status_id = fields.Many2one('customer.status', string="Customer Status")
    customer_subdivision_id = fields.Many2one('customer.subdivision', string="Subdivision")

    @api.constrains('worker_code')
    def _check_worker_code_unique(self):
        for rec in self:
            if rec.worker_code:
                existing = self.search([
                    ('worker_code', '=', rec.worker_code),
                    ('id', '!=', rec.id)
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _("Worker Code '%s' is already used by another record. Please enter a unique code.") % rec.worker_code)

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
    product_shelf_life_ids = fields.One2many('customer.product.shelf.life','partner_id',string="Product Shelf Life")

    #     all_3rd_level = [
    #         'channel_mt_hyper', 'channel_mt_super', 'channel_gt_grocery', 'channel_gt_cs', 'channel_gt_super',
    #         'channel_gt_petrol', 'channel_gt_discount', 'channel_gt_wholesale', 'channel_gt_tc', 'channel_gt_sc',
    #         'channel_horeca_hr', 'channel_horeca_rc', 'channel_horeca_sa', 'channel_horeca_caterings',
    #         'channel_horeca_tc', 'channel_horeca_pc', 'channel_ecom_mp', 'channel_ecom_app'
    #     ]
    #


    @api.model_create_multi
    def create(self, vals_list):
        res = super(ResPartner, self).create(vals_list)
        for record in res:
            if record.active and record.contact_type == 'customer' and not record.customer_code and not record.parent_id:
                # record.customer_code = self.env['ir.sequence'].next_by_code("customer.code.seq") or _('New')
                if record.customer_type == 'cash':
                    record.customer_code = self.env['ir.sequence'].next_by_code("cash.customer.code.seq") or _('New')
                else:
                    record.customer_code = self.env['ir.sequence'].next_by_code("credit.customer.code.seq") or _('New')
            # if not record.parent_id and not record.child_ids and record.contact_type:
            #     raise ValidationError(_("Contact and Address  Required"))
            # if not record.use_partner_credit_limit and record.contact_type and record.contact_type == 'customer':
            #     raise ValidationError(_("Credit Limit Required"))
        # for vals in vals_list:
        #     if not vals.get('parent_id') and not vals.get('child_ids'):
        #         raise ValidationError(_("Contact and Address  Required"))
        #
        #     if vals.get('use_partner_credit_limit') == False and vals.get('contact_type') == 'customer':
        #         raise ValidationError(_("Credit Limit Required"))
        return res


    def write(self, vals):
        # if vals.get('use_partner_credit_limit') == False:
        #     raise ValidationError(_("Credit Limit Required"))
        if 'credit_limit' in vals:
            for partner in self:
                if partner.credit_limit != vals['credit_limit']:
                    vals['previous_credit_limit'] = partner.credit_limit
        res =  super(ResPartner, self).write(vals)
        # for record in self:
        #     if not record.use_partner_credit_limit and record.contact_type and record.contact_type == 'customer':
        #         raise ValidationError(_("Credit Limit Required"))
        return res


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





    establish_data = fields.Text(string="Establish Data", required=False)
    tl_expiry_date = fields.Date(string="TL Expiry Date", required=False)
    delivery_receive_time = fields.Datetime(string="Delivery Receive Time")

    nationality_id = fields.Many2one('res.country')

    emirate_id = fields.Many2one(
        'res.country.state',
        string='Emirate',
        required=False,
    )

    emirate = fields.Char(string="Emirate ID", required=False)
    tl_issued_emirate = fields.Char(string="TL issued From Emirates", required=False)
    trade_number = fields.Char(string="Trade License Number", required=False)

    contact_payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms", required=False)
    contact_payment_method_id = fields.Many2one('account.payment.method', string="Payment Method", required=False)
    contact_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier'), ('both', 'Both')],
                                    required=False)

    vat_trn = fields.Char(string="TRN No", required=False)

    #@api.constrains('trade_number')
    #def _check_duplicate_trade_license(self):
    #    for rec in self:
    #        if rec.trade_number:
    #            duplicate = self.env['res.partner'].search([
    #                ('id', '!=', rec.id),
    #                ('trade_number', '=', rec.trade_number)
    #            ], limit=1)
    #            if duplicate:
    #                raise ValidationError("This Trade License Number is already used.")

    # is_required_contact_type = fields.Boolean(compute="compute_is_required_contact_type")
    #
    # @api.depends('type','company_type')
    # def compute_is_required_contact_type(self):
    #     for record in self:
    #         is_required_contact_type = False
    #         if record.type == 'contact':
    #             is_required_contact_type = True
    #         record.is_required_contact_type =



    # contact_person = fields.Char(string="TRN No")
    # contact_person_email = fields.Char(string="TRN No")
    # contact_number = fields.Char(string="TRN No")
    # division_name = fields.Char(string="TRN No")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if 'default_contact_type' in self.env.context:
            res['contact_type'] = self.env.context.get('default_contact_type') # set default value here
        return res



    @api.onchange('contact_type')
    def onchange_contact_type(self):
        if self.contact_type == 'customer':
            self.customer_rank = self.customer_rank or 1
            self.supplier_rank = 0
        elif self.contact_type == 'supplier':
            self.customer_rank = 0
            self.supplier_rank = self.supplier_rank or 1
        elif self.contact_type == 'both':
            self.customer_rank = self.customer_rank or 1
            self.supplier_rank = self.supplier_rank or 1
        else:
            self.customer_rank = 0
            self.supplier_rank = 0




    buyer_id = fields.Many2one('res.users', string='Buyer')

    buyer_contact = fields.Char(related='buyer_id.phone', string="Buyer Contact")

    buyer_email = fields.Char(string="Buyer Email ID", related='buyer_id.email', )

    finance_manager_id = fields.Many2one('res.users', string="Finance Manager")
    finance_manager_contact = fields.Char(string="Finance Manager Contact", related='finance_manager_id.phone')
    finance_manager_email = fields.Char(string="Finance Manager Email ID", related='finance_manager_id.email')

    share_invoice_email = fields.Char(string="Email ID to Share Invoice")
    share_soa_email = fields.Char(string="Email ID to Share SOA")

    latitude = fields.Char(string="Latitude")
    longitude = fields.Char(string="Longitude")


    division_id = fields.Many2one('division.management')

    # department = fields.Char(string="Department")
    department = fields.Many2one('account.analytic.account', string="Department")
    category = fields.Char(string="Category")
    business_type = fields.Char(string="Business Type")
