from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class NotificationConfig(models.Model):
    _name = 'notification.config'
    _description = 'Notification Configuration'

    name = fields.Char(required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=False, ondelete='set null')
    group_ids = fields.Many2many('res.groups', string='Groups')
    active = fields.Boolean(default=True, compute='_compute_active_status', inverse='_inverse_active_status', store=True)
    date_from = fields.Date(string='Effective From')
    date_to = fields.Date(string='Effective To')
    user_ids = fields.Many2many(
        'res.users',
        'notification_config_group_users_rel',
        'config_id',
        'user_id',
        string='Users from Groups',
        compute='_compute_group_users',
        store=True
    )
    notify_users = fields.Many2many(
        'res.users',
        'notification_config_notify_users_rel',
        'config_id',
        'user_id',
        string='Users to Notify',
        domain="[(\'id\', \'in\', user_ids)]"
    )
    state_field_values = fields.One2many(
        'notification.state.value', 'config_id',
        string='Available State Values',
        compute='_compute_state_values',
        store=True
    )
    selected_states = fields.Many2many(
        'notification.state.value',
        'notification_config_state_rel',
        'config_id',
        'state_value_id',
        string='Trigger States'
    )

    # --------------------------
    # Constraints & Computes
    # --------------------------
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError("Start Date must be earlier than or equal to End Date.")

    @api.depends('group_ids')
    def _compute_group_users(self):
        for rec in self:
            users = self.env['res.users'].search([('groups_id', 'in', rec.group_ids.ids)])
            rec.user_ids = users

    @api.depends('model_id')
    def _compute_state_values(self):
        for rec in self:
            rec.state_field_values = [(5, 0, 0)]  # Clear existing
            if not rec.model_id or not rec.model_id.model:
                continue

            model = self.env[rec.model_id.model]
            fields_found = self.env['ir.model.fields'].search([
                ('model', '=', rec.model_id.model),
                ('ttype', '=', 'selection'),
                '|', '|',
                ('name', 'ilike', 'state'),
                ('name', 'ilike', 'status'),
                ('name', 'ilike', 'registration'),
            ])

            for field in fields_found:
                field_obj = model._fields.get(field.name)
                if not field_obj or not field_obj.selection:
                    continue

                selection = field_obj.selection
                if callable(selection):
                    selection = selection(model)

                for val_key, val_label in selection:
                    state_value = self.env["notification.state.value"].search([
                        ("name", "=", val_key),
                        ("label", "=", val_label),
                        ("field_name", "=", field.name),
                    ], limit=1)
                    if not state_value:
                        state_value = self.env["notification.state.value"].create({
                            "name": val_key,
                            "label": val_label,
                            "field_name": field.name,
                        })
                    rec.state_field_values = [(4, state_value.id)]

    @api.depends('date_to')
    def _compute_active_status(self):
        today = date.today()
        for rec in self:
            rec.active = not (rec.date_to and rec.date_to < today)

    def _inverse_active_status(self):
        # Allow toggling manually in UI
        pass

    @api.model
    def deactivate_expired_configs(self):
        today = date.today()
        expired_configs = self.search([('date_to', '<', today), ('active', '=', True)])
        expired_configs.write({'active': False})

    def send_notification(self, res_id, model_name, current_state, field_name='state'):
        """Trigger a notification if a record in model_name moves to current_state for field_name."""
        today = date.today()
        configs = self.search([
            ('active', '=', True),
            ('model_id.model', '=', model_name),
            '|', ('date_from', '=', False), ('date_from', '<=', today),
            '|', ('date_to', '=', False), ('date_to', '>=', today),
        ])

        for config in configs:
            matching = config.selected_states.filtered(
                lambda val: val.name == current_state and val.field_name == field_name
            )
            if matching:
                label = matching[0].label
                for user in config.notify_users:
                    self.env['mail.activity'].create({
                        'res_model_id': self.env['ir.model']._get(model_name).id,
                        'res_id': res_id,
                        'user_id': user.id,
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'summary': f'Notification: {label}',
                        'note': f'Record <b>{res_id}</b> in model <code>{model_name}</code> changed to <b>{label}</b> ({current_state}) in field <code>{field_name}</code>',
                    })

class NotificationStateValue(models.Model):
    _name = 'notification.state.value'
    _description = 'Selectable State Value'

    name = fields.Char(string='Value Key', required=True)
    label = fields.Char(string='Label', required=True)
    field_name = fields.Char(string='Field Name', required=True)
    config_id = fields.Many2one('notification.config', string='Config')


