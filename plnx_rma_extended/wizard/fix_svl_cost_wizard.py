from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class FixSVLCostWizard(models.TransientModel):
    _name = "fix.svl.cost.wizard"
    _description = "Fix Stock Valuation Layer Values"

    product_id = fields.Many2one(
        'product.product',
        string="Product",
        required=True,
        domain=[('type', '=', 'consu'), ('is_storable', '=', True)],
    )
    fix_from_date = fields.Datetime(
        string="Fix From Date",
        required=True,
    )
    enter_manual_unit_cost = fields.Boolean("Enter Correct Unit Cost Manually", default=False)
    correct_unit_cost = fields.Float(
        string="Correct Unit Cost",
        default=0.0,
        compute='_compute_correct_unit_cost',
        help="If 'Enter Manually' is unchecked, this will be auto-filled with the last SVL Unit Cost before the 'Fix From Date'.",
    )
    manual_unit_cost = fields.Float(
        string="Manual Unit Cost",
        default=0.0,
    )
    
    @api.depends('product_id', 'fix_from_date', 'enter_manual_unit_cost', 'manual_unit_cost')
    def _compute_correct_unit_cost(self):
        for record in self:
            if record.enter_manual_unit_cost:
                record.correct_unit_cost = record.manual_unit_cost
            elif record.product_id and record.fix_from_date:
                one_day_before = self.fix_from_date - timedelta(days=1)
                prev_svl = self.env['stock.valuation.layer'].search([
                    ('product_id', '=', record.product_id.id),
                    ('create_date', '<=', one_day_before),
                    ('quantity', '!=', 0),
                    ('unit_cost', '!=', 0),
                ], order="create_date desc", limit=1)
                record.correct_unit_cost = prev_svl.unit_cost if prev_svl else 0.0
            else:
                record.correct_unit_cost = 0

    def action_fix_svl_costs(self):
        self.ensure_one()
        svl_model = self.env['stock.valuation.layer']
        
        # 1. Find last SVL before fix_from_date
        one_day_before = self.fix_from_date - timedelta(days=1)
        prev_svl = svl_model.search([
            ('product_id', '=', self.product_id.id),
            ('create_date', '<=', one_day_before),
            ('quantity', '!=', 0),
            ('unit_cost', '!=', 0),
        ], order="create_date desc", limit=1)

        if not prev_svl and not self.enter_manual_unit_cost:
            raise UserError(_("No valid SVL found before %s for product %s") % (
                self.fix_from_date, self.product_id.display_name
            ))

        correct_unit_cost = self.correct_unit_cost

        # 2. Get all SVLs on/after fix_from_date
        target_svls = svl_model.search([
            ('product_id', '=', self.product_id.id),
            ('create_date', '>=', self.fix_from_date),
            ('quantity', '!=', 0),
            ('unit_cost', '!=', 0),
            ('unit_cost', '!=', correct_unit_cost),
        ], order="create_date asc")

        updated_count = 0
        if self.product_id.standard_price != correct_unit_cost:
            self.product_id.sudo().write({'standard_price': correct_unit_cost})
            
        for svl in target_svls:
            if svl.unit_cost == 0:
                continue
            if svl.unit_cost == correct_unit_cost:
                continue

            new_value = correct_unit_cost * svl.quantity
            svl.write({
                'unit_cost': correct_unit_cost,
                'value': new_value,
                'remaining_value': new_value,
            })
            # Rebuild accounting entries
            svl.account_move_id.button_draft()
            svl.account_move_id.unlink()
            svl._validate_accounting_entries()                        

            updated_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("SVL Fix Completed"),
                'message': _("Fixed %s SVLs for %s with Unit Cost %.2f and Value as per their quantity and Updated Product Cost.") % (
                    updated_count, self.product_id.display_name, correct_unit_cost
                ),
                'sticky': False,
            }
        }
