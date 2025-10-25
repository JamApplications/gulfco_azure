/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportLine } from "@account_reports/components/account_report/line/line";

import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";



patch(AccountReportFilters.prototype, {

   setup() {
        super.setup();
          this._t = _t;
    },

    get selectedLocationPlanFilters()
    {
        debugger;
            const selectedFilters = this.controller.options.location_plan.filter(
                (irFilter) => irFilter.selected,
            );

            if (selectedFilters.length === 1) {
                return selectedFilters[0].name;
            } else if (selectedFilters.length > 1) {
                return _t("%s selected", selectedFilters.length);
            } else {
                return _t("None");
            }
    },

    get selectedDepartmentPlanFilters() {
    debugger;
        const selectedFilters = this.controller.options.department_plan.filter(
            (irFilter) => irFilter.selected,
        );

        if (selectedFilters.length === 1) {
            return selectedFilters[0].name;
        } else if (selectedFilters.length > 1) {
            return _t("%s selected", selectedFilters.length);
        } else {
            return _t("None");
        }
    },

    get selectedChannelPlanFilters() {
        const selectedFilters = this.controller.options.channel_plan.filter(
            (irFilter) => irFilter.selected,
        );

        if (selectedFilters.length === 1) {
            return selectedFilters[0].name;
        } else if (selectedFilters.length > 1) {
            return _t("%s selected", selectedFilters.length);
        } else {
            return _t("None");
        }
    },


    async toggleSelectAll(optionKey) {
        if (!this.controller?.options?.[optionKey]) {
            console.warn("Option key not available:", optionKey);
            return;
        }
        const options = this.controller.options[optionKey];
        const allSelected = options.every((f) => f.selected);
        options.forEach((f) => { f.selected = !allSelected; });
        debugger
        await this.applyFilters(optionKey, true);
    }



});
