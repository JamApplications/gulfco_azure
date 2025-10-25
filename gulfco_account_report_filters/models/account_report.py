from odoo import models, api, fields


class AccountFilterPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"

    def _get_custom_display_config(self):
        parent_config = super()._get_custom_display_config()
        parent_config.get("templates", {}).update({'AccountReportFilters': "gulfco_account_report_filters.SalespersonFilters"})
        return parent_config


class AccountAgedPartnerBalance(models.AbstractModel):
    _inherit = "account.aged.partner.balance.report.handler"

    def _get_custom_display_config(self):
        return {
            "templates": {
                "AccountReportFilters": "gulfco_account_report_filters.SalespersonFilters",
            },
        }


class AccountReport(models.Model):
    _inherit = "account.report"

    filter_salesperson = fields.Boolean(
        string="Salesperson",
        compute=lambda x: x._compute_report_option_filter("filter_salesperson"),
        readonly=False,
        store=True,
        depends=["root_report_id", "section_main_report_ids"],
    )

    def _init_options_salesperson(self, options, previous_options):
        if not self.filter_salesperson:
            return
        options["salesperson"] = True

        # Salesperson (Assign To) filter
        previous_salesperson_ids = previous_options.get("salesperson_ids") or []
        selected_salesperson_ids = [
            int(partner) for partner in previous_salesperson_ids
        ]
        # search instead of browse so that record rules apply and filter out the ones the user does not have access to
        selected_salesperson = (
            selected_salesperson_ids
            and self.env["res.partner"]
            .with_context(active_test=False)
            .search([("id", "in", selected_salesperson_ids)])
            or self.env["res.partner"]
        )
        options["selected_salesperson_ids"] = selected_salesperson.mapped("name")
        options["salesperson_ids"] = selected_salesperson.ids

        # Sales Team filter
        previous_sales_team_ids = previous_options.get("sales_team_ids") or []
        selected_sales_team_ids = [int(team) for team in previous_sales_team_ids]
        # search instead of browse so that record rules apply and filter out the ones the user does not have access to
        selected_sales_team = (
            selected_sales_team_ids
            and self.env["crm.team"]
            .with_context(active_test=False)
            .search([("id", "in", selected_sales_team_ids)])
            or self.env["crm.team"]
        )
        options["selected_sales_team_ids"] = selected_sales_team.mapped("name")
        options["sales_team_ids"] = selected_sales_team.ids

    @api.model
    def _get_options_salesperson_domain(self, options):
        domain = []
        has_salesperson = options.get("salesperson_ids")
        has_sales_team = options.get("sales_team_ids")

        if has_salesperson and has_sales_team:
            salesperson_ids = [int(pid) for pid in options["salesperson_ids"]]
            sales_team_ids = [int(tid) for tid in options["sales_team_ids"]]
            domain = [
                "|",
                ("move_id.assign_to", "in", salesperson_ids),
                ("move_id.team_id", "in", sales_team_ids),
            ]
        elif has_salesperson:
            salesperson_ids = [int(pid) for pid in options["salesperson_ids"]]
            domain = [("move_id.assign_to", "in", salesperson_ids)]
        elif has_sales_team:
            sales_team_ids = [int(tid) for tid in options["sales_team_ids"]]
            domain = [("move_id.team_id", "in", sales_team_ids)]

        return domain

    def _get_options_domain(self, options, date_scope):
        self.ensure_one()
        domain = super()._get_options_domain(options, date_scope)
        domain += self._get_options_salesperson_domain(options)
        return domain
