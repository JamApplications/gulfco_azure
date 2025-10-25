# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models,api
from lxml import etree
from odoo.exceptions import ValidationError
import re


class ResPartner(models.Model):
    _inherit = "res.partner"

    child_ids = fields.One2many('res.partner', 'parent_id', string='Contact',
                                         domain=['|',('active', '=', True), ('active', '=', False)],
                                         context={'active_test': False})

    vehicle_id = fields.Many2one('fleet.vehicle')
    working_schedule_id = fields.Many2one('resource.calendar')
    type = fields.Selection(selection_add=[("fsm_location", "Location")])
    fsm_location = fields.Boolean("Is a FS Location")
    fsm_person = fields.Boolean("Is a FS Worker")
    van_location = fields.Many2one("stock.location", string="Van Sub-Inventory")

    def _internal_user_domain(self):
        user_list = []
        for rec in self.env['res.users'].search([]):
            if rec._is_internal():
                user_list.append(rec.id)
        return [("id", "in", user_list)]

    internal_user = fields.Many2one("res.users", string="Internal user", domain=_internal_user_domain)
    fsm_location_id = fields.One2many(
        comodel_name="fsm.location",
        string="Related FS Location",
        inverse_name="partner_id",
        readonly=True,
    )
    contact_type = fields.Selection(selection_add=[('worker', "Worker")],
                                    ondelete={'worker': 'cascade'})

    @api.constrains('phone')
    def _check_phone_numeric(self):
        for partner in self:
            if partner.phone:
                # Allow +, -, space and numbers only; no alphabets allowed
                if re.search(r'[a-zA-Z]', partner.phone):
                    raise ValidationError("The phone field must not contain alphabetic characters.")

    @api.onchange('fsm_person')
    def onchange_fsm_person(self):
        if self.fsm_person:
            self.contact_type = 'worker'
            self.company_type = 'person'

    service_location_id = fields.Many2one(
        "fsm.location", string="Primary Service Location"
    )
    owned_location_ids = fields.One2many(
        "fsm.location",
        "owner_id",
        string="Owned Locations",
        domain=[("fsm_parent_id", "=", False)],
    )
    owned_location_count = fields.Integer(
        compute="_compute_owned_location_count", string="# of Owned Locations"
    )

    def _compute_owned_location_count(self):
        for partner in self:
            partner.owned_location_count = self.env["fsm.location"].search_count(
                [("owner_id", "child_of", partner.id)]
            )

    def action_open_owned_locations(self):
        for partner in self:
            owned_location_ids = self.env["fsm.location"].search(
                [("owner_id", "child_of", partner.id)]
            )
            action = self.env.ref("fieldservice.action_fsm_location").sudo().read()[0]
            action["context"] = {}
            if len(owned_location_ids) > 1:
                action["domain"] = [("id", "in", owned_location_ids.ids)]
            elif len(owned_location_ids) == 1:
                action["views"] = [
                    (self.env.ref("fieldservice.fsm_location_form_view").id, "form")
                ]
                action["res_id"] = owned_location_ids.ids[0]
            return action

    def _convert_fsm_location(self):
        wiz = self.env["fsm.wizard"]
        partners_with_loc_ids = (
            self.env["fsm.location"]
            .sudo()
            .search([("active", "in", [False, True]), ("partner_id", "in", self.ids)])
            .mapped("partner_id")
        ).ids

        partners_to_convert = self.filtered(
            lambda p: p.type == "fsm_location" and p.id not in partners_with_loc_ids
        )
        for partner_to_convert in partners_to_convert:
            wiz.action_convert_location(partner_to_convert)

    def write(self, value):
        res = super().write(value)
        self._convert_fsm_location()
        return res

    # @api.model_create_multi
    # def create(self, vals_list):
    #     res = super(ResPartner, self).create(vals_list)
    #     res.fsm_person = True
    #     return res

    @api.model
    def create(self, vals):
        if vals.get('parent_id') and vals.get('type') in ('fsm_location'):
            vals['active'] = False
        # parent = self.browse(vals['parent_id'])
        # if parent.customer_code:
        #     # Find the highest existing child number
        #     last_child = self.search([
        #         ('parent_id', '=', parent.id),
        #         ('customer_code', 'like', parent.customer_code + '-%')
        #     ], order='customer_code desc', limit=1)
        #
        #     if last_child:
        #         # Extract last number and increment
        #         last_number = int(last_child.customer_code.split('-')[-1])
        #         next_number = last_number + 1
        #     else:
        #         next_number = 1
        #
        #     # Format with leading zeros
        #     vals['customer_code'] = f"{parent.customer_code}-{next_number:02d}"
        res = super(ResPartner, self).create(vals)
        if res and res.type == 'fsm_location':

            if res.parent_id.contact_type == 'customer':
                registration_type = 'customer_registration'
            elif res.parent_id.contact_type == 'supplier':
                registration_type = 'vendor_registration'
            else:
                registration_type = res.parent_id.registration_type

            res.registration_type = registration_type
            res.customer_type = res.parent_id.customer_type
            res.contact_type = res.parent_id.contact_type
        return res

 # for worker menu in dashboard
    def action_open_inventory_adjustment(self):
        location_ids  = []
        user_id = self.env['res.users'].search([('partner_id', '=', self.id)])
        if user_id:
            location = self.env['stock.location'].search([('responsible_id', 'in', user_id.ids)])
            if location:
                location_ids = location.ids
        view = self.env.ref('stock.view_stock_quant_tree_inventory_editable')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Count/Adjustment',
            'view_mode': 'list',
            'view_id': view.id,
            'res_model': 'stock.quant',
            'target': 'current',
            'domain': [('location_id', 'in', location_ids)],
            'context': {'default_location_id': location_ids[0] if location_ids else False},
        }

    def action_open_van_stock(self):
        self.ensure_one()
        location_id = []
        user_id = self.env['res.users'].search([('partner_id', '=', self.id)])
        if user_id:
            location = self.env['stock.location'].search([('responsible_id', 'in', user_id.ids)])
            if location:
                location_id = location.ids
        action_ref = self.env.ref('stock.location_open_quants')
        action_data = action_ref.read()[0]
        action_data['domain'] = [('location_id', "in", location_id)]
        return action_data

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'kanban' and options.get('action_id') == self.env.ref('fieldservice.action_workers').id:
            doc = etree.XML(res['arch'])

            # Remove the existing opportunity button
            for node in doc.xpath("//a[@name='action_view_opportunity']"):
                node.getparent().remove(node)
            for node in doc.xpath("//a[@name='action_view_sale_order']"):
                node.getparent().remove(node)
            for node in doc.xpath("//field[@name='purchase_order_count']//.."):
                node.getparent().remove(node)

            # Add new buttons — find where to insert (e.g., under a div with class "o_kanban_footer_right" or any custom class you use)
            footer_divs = doc.xpath("//footer//div")
            if footer_divs:
                stock_buttons = etree.fromstring('''
                            <div class="d-flex w-100 justify-content-between mt-2">
                                <button type="object" name="action_open_inventory_adjustment"
                                        class="btn btn-primary btn-sm" style="margin-left:5px">Stock Count</button>
                                <button type="object" name="action_open_van_stock"
                                        class="btn btn-info btn-sm">Van Stock</button>
                            </div>
                        ''')
                footer_divs[0].append(stock_buttons)

            res['arch'] = etree.tostring(doc, encoding='unicode')

        return res