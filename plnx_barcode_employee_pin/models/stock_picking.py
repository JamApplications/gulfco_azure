from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import frozendict
from datetime import datetime, time, timedelta


class StockPicking(models.Model):
    _inherit = "stock.picking"

    employee_ids = fields.Many2many('hr.employee', 'picking_employee_rel')
    employee_history_line = fields.One2many('stock.picking.employee.history', 'picking_id')
    forklift_partner_id = fields.Many2one('res.partner', string="Forklift")



    @api.depends('batch_id')
    def _compute_display_batch_button(self):
        super(StockPicking, self)._compute_display_batch_button()
        for picking in self:
            if picking.display_batch_button == picking.batch_id and picking.batch_id.state == 'in_progress' and picking.batch_id.employee_ids:
                for emp in picking.batch_id.employee_ids:
                    picking.employee_ids = [(4, emp.id)]
                    vals = {
                        'employee_id': emp.id,
                        'access_date': datetime.today(),
                        'batch_id': picking.id
                    }
                    picking.employee_history_line.create(vals)


    def action_open_picking_client_action(self):
        # if self.env.user.allow_multi_employee and not self.env.context.get('pop_wiz'):
        #     open_wiz = {
        #         'name': 'Enter PIN',
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'barcode.pin.wizard',
        #         'view_mode': 'form',
        #         'target': 'new',  # This makes it a pop-up
        #     }
        #     if open_wiz:
        #         # res = super(StockPicking, self).action_open_picking_client_action()
        #         return open_wiz
        #     else:
        #         raise UserError("Employee for this PIN does not exist!")

        # else:
        #     res = super(StockPicking, self).action_open_picking_client_action()
        res = super(StockPicking, self).action_open_picking_client_action()
        return res


    @api.model
    def action_open_new_picking(self):
        context = self._context.copy()
        context.update({'pop_wiz': True})
        self.env.context = frozendict(context)
        res = super(StockPicking, self).action_open_new_picking()
        return  res

    def _get_fields_stock_barcode(self):
        res = super()._get_fields_stock_barcode()
        res.append('employee_ids')
        res.append('employee_history_line')
        return res


    def _get_stock_barcode_data(self):
        res = super(StockPicking, self)._get_stock_barcode_data()
        self = self.with_context(display_default_code=False)
        res['records']['stock.picking.employee.history'] = self.read(self._get_fields_stock_barcode(), load=False)
        if 'employee_id' in self.env.context and self.env.context.get('employee_id'):
            move_lines = self.move_line_ids.filtered(lambda x: x.move_id.picker_partner_id == self.env.context.get(
                'employee_id').work_contact_id or x.move_id.forklift_partner_id == self.env.context.get(
                'employee_id').work_contact_id)

            res['records']['stock.move'] = self.move_ids.filtered(lambda x:x.picker_partner_id == self.env.context.get('employee_id').work_contact_id or x.forklift_partner_id == self.env.context.get('employee_id').work_contact_id).read(self.move_ids.filtered(lambda x:x.picker_partner_id == self.env.context.get('employee_id').work_contact_id or x.forklift_partner_id == self.env.context.get('employee_id').work_contact_id)._get_fields_stock_barcode(), load=False)
            res['records']["stock.move.line"] = move_lines.read(move_lines._get_fields_stock_barcode(), load=False)
            for pick in res['records']['stock.picking']:
                pick['move_ids'] = self.env['stock.move'].sudo().browse(pick.get('move_ids')).filtered(lambda x:x.picker_partner_id == self.env.context.get('employee_id').work_contact_id or x.forklift_partner_id == self.env.context.get('employee_id').work_contact_id).ids
                pick['move_line_ids'] = self.env['stock.move.line'].sudo().browse(pick.get('move_line_ids')).filtered(lambda x:x.move_id.picker_partner_id == self.env.context.get('employee_id').work_contact_id or x.move_id.forklift_partner_id == self.env.context.get('employee_id').work_contact_id).ids


        return res




class StockPickingType(models.Model):
    _inherit = "stock.picking.type"


    def get_filtered_action_picking_tree_ready_kanban(self, idList, emp_id):
        self.env['stock.picking'].search([('id', '=', idList)])

        action = self._get_action('stock_barcode.stock_picking_action_kanban')

        action['domain'] = None
        action['domain'] = [('id', '=', idList)]
        action['context'] = {'default_picker_partner_id': emp_id}
        return action
