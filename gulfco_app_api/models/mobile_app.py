from odoo import fields, models, api, _
from odoo.exceptions import UserError

class MobileApp(models.Model):
    _name = 'gulfco.mobile.app'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # <-- add this
    _description = 'Mobile App'
    _order = 'current_app desc, id desc'

    name = fields.Char(tracking=True)
    current_version = fields.Char(tracking=True)
    description = fields.Text()
    current_version_line_id = fields.Many2one("app.version.line", string="Current Version Line")
    version_line_ids = fields.One2many("app.version.line", "mobile_app_id", string="Versions")
    workers_config = fields.One2many("worker.config", "app_id", string="Workers")
    current_app = fields.Boolean(string="Is Current App?", default=False, tracking=True)
    running_versions_count = fields.Integer(compute="_compute_running_versions_count", string="Running Versions")
    app_hard_stop = fields.Boolean(string="Hard Stop App")
    hard_stop_reason = fields.Char(string="Stop Reason")
    @api.depends('version_line_ids.status')
    def _compute_running_versions_count(self):
        for rec in self:
            rec.running_versions_count = len(rec.version_line_ids.filtered(lambda l: l.status == 'running'))

    def action_set_as_current_app(self):
        """Make this record the only 'current' app."""
        for app in self:
            self.search([('current_app', '=', True)]).write({'current_app': False})
            app.current_app = True

    def action_sync_current_version(self):
        """Sync current_version from the selected current_version_line_id."""
        for app in self:
            if not app.current_version_line_id:
                raise UserError(_("Please select a Current Version Line first."))
            app.current_version = app.current_version_line_id.version_code or ''

    # ---------- Defaults / Sync ----------
    @api.model
    def _default_workers_config(self):
        """Return O2M commands to prefill with all worker partners."""
        workers = self.env['res.partner'].search([
            ('contact_type', '=', 'worker'),
            ('active', '=', True),
        ])
        # you can flip default for update_customer_geo_location here if you want
        return [(0, 0, {'worker_id': w.id, 'update_customer_geo_location': False}) for w in workers]

    def action_sync_workers_config(self):
        """
        Button: add any new workers (contact_type=worker) that don't yet exist
        for this app. It won't remove anything; just fills the gaps.
        """
        Partner = self.env['res.partner']
        all_workers = Partner.search([('contact_type', '=', 'worker'), ('active', '=', True)]).ids
        for app in self:
            existing = set(app.workers_config.mapped('worker_id').ids)
            missing = [wid for wid in all_workers if wid not in existing]
            if missing:
                app.write({
                    'workers_config': [(0, 0, {'worker_id': wid, 'update_customer_geo_location': False}) for wid in missing]
                })