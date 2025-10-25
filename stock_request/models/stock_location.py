# Copyright 2018 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = "stock.location"

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Warehouse",
        compute='_compute_warehouse_id',
        store=True,
        readonly=False,  # Optional, if you want to allow manual override
    )

    @api.depends('location_id')
    def _compute_warehouse_id(self):
        warehouse_model = self.env['stock.warehouse']
        for loc in self:
            if not loc.id:
                loc.warehouse_id = False
                continue
            warehouse = warehouse_model.search([
                ('view_location_id', 'child_of', loc.id)
            ], limit=1)
            loc.warehouse_id = warehouse or False

    _sql_constraints = [
        (
            'barcode_warehouse_uniq',
            'unique(barcode, warehouse_id)',
            'The barcode for a location must be unique within the same warehouse.'
        ),
        (
            'inventory_freq_nonneg',
            'check(cyclic_inventory_frequency >= 0)',
            'The inventory frequency (days) must be non-negative.'
        ),
    ]

    @api.constrains("company_id")
    def _check_company_stock_request(self):
        if any(
            rec.company_id
            and self.env["stock.request"].search(
                [("company_id", "!=", rec.company_id.id), ("location_id", "=", rec.id)],
                limit=1,
            )
            for rec in self
        ):
            raise ValidationError(
                _(
                    "You cannot change the company of the location, as it is "
                    "already assigned to stock requests that belong to "
                    "another company."
                )
            )
        if any(
            rec.company_id
            and self.env["stock.request.order"].search(
                [
                    ("company_id", "!=", rec.company_id.id),
                    ("warehouse_id", "=", rec.id),
                ],
                limit=1,
            )
            for rec in self
        ):
            raise ValidationError(
                _(
                    "You cannot change the company of the location, as it is "
                    "already assigned to stock request orders that belong to "
                    "another company."
                )
            )

    # @api.model
    # def _search(self, domain, offset=0, limit=None, order=None):
    #     if self._context.get('get_parents'):
    #         return super()._search(domain, offset, limit, order)
    #     if self._context.get('stock_request_direction') and self._context.get('stock_request_warehouse_id'):
    #         if self._context.get('stock_request_direction') in ['internal_transfer','damage_expiry_issue_out','scrap_issuance', 'consumable_issuance',]:
    #             domain = domain.copy()
    #             domain.append((('warehouse_id', '=', self._context.get('stock_request_warehouse_id'))))
    #             # if self._context.get('stock_request_direction') in ['damage_expiry_issue_out','scrap_issuance','consumable_issuance'] and self._context.get('is_destination'):
    #             if self._context.get('stock_request_direction') in ['damage_expiry_issue_out','scrap_issuance'] and self._context.get('is_destination'):
    #                 domain.append((('usage', '=', 'inventory')))
    #
    #         if self._context.get('stock_request_direction') in ['miscellaneous_issue_out'] and not self._context.get('is_destination'):
    #             domain = domain.copy()
    #             domain.append((('warehouse_id', '=', self._context.get('stock_request_warehouse_id'))))
    #
    #         if self._context.get('stock_request_direction') in ['miscellaneous_issue_out'] and self._context.get('is_destination'):
    #             domain = domain.copy()
    #             domain.append((('usage', '=', 'inventory')))
    #             # domain.append((('warehouse_id', '=', self._context.get('stock_request_warehouse_id'))))
    #
    #         if self._context.get('stock_request_direction') in ['miscellaneous_receiving'] and self._context.get('is_destination'):
    #             domain = domain.copy()
    #             domain.append((('warehouse_id', '=', self._context.get('stock_request_warehouse_id'))))
    #
    #     return super()._search(domain, offset, limit, order)


    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        ctx = self._context


        # 1. Bypass custom domain logic when:
        #    - Explicitly resolving parents
        #    - No stock_request_direction in context
        if ctx.get('get_parents') or not ctx.get('stock_request_direction'):
            return super(StockLocation, self.sudo())._search(domain, offset, limit, order)

        # 2. Protect against child_of searches (hierarchy lookup)
        if any(isinstance(cond, (list, tuple)) and cond[1] == 'child_of' for cond in domain):
            return super(StockLocation, self.sudo())._search(domain, offset, limit, order)

        # 3. Apply your custom filters only when direction + warehouse are present
        direction = ctx.get('stock_request_direction')
        warehouse_id = ctx.get('stock_request_warehouse_id')
        is_destination = ctx.get('is_destination')

        if not direction or not warehouse_id:
            return super(StockLocation, self.sudo())._search(domain, offset, limit, order)

        if direction and warehouse_id:
            domain = domain.copy()

            # Internal transfer, damage/expiry, scrap, consumable
            if direction in ['internal_transfer', 'damage_expiry_issue_out', 'scrap_issuance', 'consumable_issuance', 'stock_takeover']:
                domain.append(('warehouse_id', '=', warehouse_id))
                if direction in ['damage_expiry_issue_out', 'scrap_issuance'] and is_destination:
                    domain.append(('usage', '=', 'inventory'))

            # Miscellaneous Issue Out
            elif direction == 'miscellaneous_issue_out':
                if is_destination:
                    domain += [
                        ('usage', '=', 'inventory'),
                        '|', ('warehouse_id', '=', warehouse_id),
                        ('warehouse_id', '=', False),
                    ]
                else:
                    domain.append(('warehouse_id', '=', warehouse_id))

            # Miscellaneous Receiving
            elif direction == 'miscellaneous_receiving' and is_destination:
                domain.append(('warehouse_id', '=', warehouse_id))

        return super()._search(domain, offset, limit, order)
