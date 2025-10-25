from odoo import _, api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    task_ids = fields.One2many('project.task', 'picking_id', string='Tasks')
    task_count = fields.Integer(compute='_compute_task_count', string='Task Count')

    @api.depends('task_ids')
    def _compute_task_count(self):
        for picking in self:
            picking.task_count = len(picking.task_ids)

    # def action_create_project_task(self):
    #     return {
    #         'name': _('Create Task'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'project.task',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'view_id': self.env.ref('project.view_task_form2').id,
    #         'target': 'current',
    #         'context': {
    #             'default_picking_id': self.id,
    #             'default_name': self.name,
    #         }
    #     }



    def action_view_tasks(self):
        action = self.env.ref('project.action_view_task').read()[0]
        action['domain'] = [('picking_id', 'in', self.ids)]
        return action

    def internal_transfer_done_notify(self):
        for picking in self:
            # create notification activity for creator
            if picking.create_uid:
                pass
                # activity = self.env['mail.activity'].create({
                #     'res_id': picking.id,
                #     'res_model_id': self.env['ir.model']._get('stock.picking').id,
                #     'summary': _('Internal Transfer Done'),
                #     'note': _('The internal transfer %s has been done.') % picking.name,
                #     'user_id': picking.create_uid.id,
                #     'activity_type_id': self.env['mail.activity']._default_activity_type_for_model('project.task').id,
                # })

    def button_validate(self):
        res = super().button_validate()
        # nothing in that method code that why comment
        # self.internal_transfer_done_notify()
        return res