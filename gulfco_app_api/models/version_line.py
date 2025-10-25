from odoo import fields, models, api, _
from odoo.exceptions import UserError

class VersionLine(models.Model):
    _name = 'app.version.line'
    _description = 'Mobile App Version'
    _order = 'status desc, id desc'

    name = fields.Char(required=True)
    version_code = fields.Char(required=True, help="Use semantic versioning e.g. 1.3.0")
    is_current_version = fields.Boolean(string="Is Current Version?")
    status = fields.Selection(
        [("draft","Draft"),("running","Running"),("closed","Closed")],
        default="draft",
        required=True
    )
    mobile_app_id = fields.Many2one("gulfco.mobile.app", required=True)

    def action_set_as_current(self):
        """Mark this line as the app's current version (and update app)."""
        for line in self:
            # Ensure only one current per app
            siblings = self.search([('mobile_app_id','=', line.mobile_app_id.id), ('is_current_version','=', True)])
            siblings.write({'is_current_version': False})
            line.is_current_version = True

            # Optionally force status to running
            if line.status != 'running':
                line.status = 'running'

            # Sync back to app
            line.mobile_app_id.write({
                'current_version_line_id': line.id,
                'current_version': line.version_code or '',
            })
