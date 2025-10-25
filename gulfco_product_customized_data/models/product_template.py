from odoo import models, fields, api, _,Command
from odoo.exceptions import AccessError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Management'


    weight = fields.Float(
        'Weight', compute='_compute_weight',digits=(16, 3),
        inverse='_set_weight', store=True)


    volume = fields.Float(
        'Volume', compute='_compute_volume', inverse='_set_volume', digits=(16, 3), store=True)


    unit_length = fields.Integer(string=" Unit Length mm")
    unit_width = fields.Integer(string=" Unit Width mm")
    unit_height = fields.Integer(string=" Unit Height mm")

    brand_id = fields.Many2one('product.brand', string="Brand")

    costing_dept_code_id = fields.Many2one('account.analytic.account', string=" Costing Dept Code")

    exercise_tax_id = fields.Many2one('account.tax', string=" Excise Tax %")
    exercise_price = fields.Float(string="Excise price",compute="compute_exercise_price",store=True,readonly=False,digits=(4,4))
    is_hazmat = fields.Boolean(string=" IS HAZMAT")


    manufacturer_id = fields.Many2one('res.partner', string="Manufacturer/Factory")
    manufacturer_street = fields.Char(related='manufacturer_id.street')
    manufacturer_street_2 = fields.Char(related='manufacturer_id.street2')
    manufacturer_zip= fields.Char(related='manufacturer_id.zip')
    manufacturer_city = fields.Char(related='manufacturer_id.city')
    manufacturer_country_id = fields.Many2one('res.country' , related='manufacturer_id.country_id')
    manufacturer_state_id = fields.Many2one('res.country.state' ,related='manufacturer_id.state_id')


    #not in the view
    no_box_ctn = fields.Float(string="No of Box in CTN",compute="compute_no_box_ctn") # Computed
    no_ctn_pallets = fields.Integer(string="No of CTNS in Pallets") # Computed
    no_ctn_layer = fields.Float(string="Number of CTN in a layer (Ti)") #,compute="compute_no_ctn_layer",) # Computed
    no_pcs_layer = fields.Float(string="Number of pieces in a layer, pcs.(Ti)",compute="compute_no_box_ctn") # Computed
    no_ctn_layer_pallet = fields.Float(string="No Of Layer in Pallet (HI)",compute="compute_no_ctn_layer_pallet") # Computed
    cartoon_cbm = fields.Float(string="Carton cbm",compute="compute_no_box_ctn") # Computed
    no_pallet_20_container = fields.Integer(string="Number of Pallets in 20inch Container")
    no_pallet_40_container = fields.Integer(string=" Number of Pallets in a 40inch Container")
    cartoon_net_weight = fields.Float(string="Carton Net Wt (kg)", digits=(6, 2)) #compute="compute_no_box_ctn")
    cartoon_gross_weight = fields.Float(
        string="Carton Gross Wt (kg)",
        digits=(6, 2)
    )
    is_storable = fields.Boolean(
        'Track Inventory', store=True,
        compute='compute_is_storable',
        readonly=False,
        default=True,
        precompute=True,
        help='A storable product is a product for which you manage stock.')

    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'By Quantity')],
        string="Tracking", required=True, default='lot',
        compute='_compute_tracking',
        store=True,
        readonly=False,
        precompute=True,
        help="Ensure the traceability of a storable product in your warehouse.")

    min_invoiceable_qty = fields.Integer(string="Min Invoiceable Qty")
    trans_temp = fields.Integer(string="Transportation temperature")
    storage_temp = fields.Integer(string="Storage temperature")
    sale_clearance_required = fields.Boolean(string="IS Municipality Clearance Required for Sale")
    storage_condition = fields.Text(string=" Storage Condition")
    type_uom_packaging = fields.Text(string="Type of unit packaging")
    uom_packaging_material = fields.Text(string="Unit packaging material")
    item_description = fields.Char(string="Item Description")
    item_type = fields.Selection([('tradable','Tradable'),('consumable','Consumable')],string="Item Type", default='tradable')

    division = fields.Selection([('food','Food'),
                                 ('non_food','Non-Food'),
                                 ('3pl', '3PL'),
                                 ('local', 'LOCAL'),
                                 ('posm', 'POSM'),
                                 ('mars','Mars')
                                 ],string="Division")

    unit_volume_cbn = fields.Float(string="Unit Volume CBN",compute="compute_unit_volume_cbn",store=True)



    @api.depends('unit_length','unit_width','unit_height')
    def compute_unit_volume_cbn(self):
        for record in self:
            record.unit_volume_cbn = record.unit_length * record.unit_width * record.unit_height
            record.volume = record.unit_length * record.unit_width * record.unit_height

    @api.depends('exercise_tax_id','list_price')
    def compute_exercise_price(self):
        for record in self:
            record.exercise_price = (record.exercise_tax_id.amount * record.list_price)/100

    # filter_package_ids = fields.Many2many('product.packaging',string="Filtered Packages")
    #
    # @api.onchange('packaging_ids','packaging_ids.name')
    # def onchange_package_id(self):
    #     self._compute_packaging_ids()
        # # virtual_records = self.packaging_ids.filtered(lambda r: isinstance(r.id, models.NewId))
        # self.filter_package_ids = self.packaging_ids

    @api.depends('product_variant_ids', 'product_variant_ids.packaging_ids')
    def _compute_packaging_ids(self):
        for p in self:
            if len(p.with_context(active_test=False).product_variant_ids) == 1:
                p.packaging_ids = p.with_context(active_test=False).product_variant_ids.packaging_ids
            else:
                p.packaging_ids = False

    def _set_packaging_ids(self):
        for p in self:
            if len(p.with_context(active_test=False).product_variant_ids) == 1:
                p.with_context(active_test=False).product_variant_ids.packaging_ids = p.packaging_ids


    def compute_no_box_ctn(self):
        for record in self:
            no_box_ctn = 0.0
            no_pcs_layer = 0.0
            cartoon_cbm = 0.0
            cartoon_net_weight = 0.0
            if record.packaging_ids:
                ctn_packages = record.packaging_ids.filtered(lambda s:s.package_type_id.type == 'ctn')
                if ctn_packages:
                    cartoon_net_weight = ctn_packages[0].package_type_id.width * ctn_packages[0].qty
                    cartoon_cbm = ctn_packages[0].package_type_id.packaging_length * ctn_packages[0].package_type_id.width * ctn_packages[0].package_type_id.height
                    ctn_qty = sum(ctn_packages.mapped('qty'))
                    box_qty = sum(record.packaging_ids.filtered(lambda s:s.package_type_id.type == 'box').mapped('qty'))
                    if box_qty > 0.0:
                        no_box_ctn = ctn_qty / box_qty
                    no_pcs_layer = ctn_qty * record.no_ctn_layer

            record.no_box_ctn = no_box_ctn
            record.no_pcs_layer = no_pcs_layer
            record.cartoon_cbm = cartoon_cbm
            # record.cartoon_net_weight = cartoon_net_weight

    def compute_no_ctn_layer_pallet(self):
        for record in self:
            record.no_ctn_layer_pallet = 0.0
            if record.no_ctn_layer > 0.0:
                if record.packaging_ids:
                    ctn_pallets = record.packaging_ids.filtered(lambda s: s.package_type_id.is_pallete_package)
                    no_ctn_pallets = sum(ctn_pallets.mapped('secondary_quantity')) or 0
                    record.no_ctn_layer_pallet = no_ctn_pallets / record.no_ctn_layer
            else:
                record.no_ctn_layer_pallet = 0.0

    # @api.depends('packaging_ids','packaging_ids.package_type_id','packaging_ids.qty')
    # def compute_no_ctn_layer(self):
    #     for record in self:
    #         no_ctn_layer = 0.0
    #         if record.packaging_ids:
    #             pallete_package = record.packaging_ids.filtered(
    #                 lambda s: s.package_type_id and s.package_type_id.is_pallete_package)
    #             if pallete_package:
    #                 no_ctn_layer =pallete_package.qty / 7
    #         record.no_ctn_layer = no_ctn_layer
    #         # record.no_ctn_layer = record.no_ctn_pallets / 7

    def open_packaging_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Product Packaging',
            'res_model': 'product.packaging',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.env['product.product'].search(
                    [('product_tmpl_id', '=', self.id), ('active', 'in', [True, False])]).id,
            }
        }

    @api.onchange('type')
    def onchange_product_type_value(self):
        if self.type != 'consu':
            self.item_type = False

class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"


    supplier_type_id = fields.Many2one('account.fiscal.position', related='partner_id.property_account_position_id', string="Supplier Type")
    est_landed_cost = fields.Float('Estimated landed cost')