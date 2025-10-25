/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { MrpMpsControlPanel, MrpMpsSearchBar } from "@mrp_mps/search/mrp_mps_control_panel";
//import { MrpMpsControlPanel, MrpMpsSearchBar } from "../search/mrp_mps_control_panel";
import DemandPlanningLineComponent from '@gulfco_demand_planning/components/line';
import { DemandPlanningModel } from '@gulfco_demand_planning/models/demand_planning_model';
import { useService, useBus } from "@web/core/utils/hooks";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { usePager } from "@web/search/pager_hook";
import { useSetupAction } from "@web/search/action_hook";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { download } from "@web/core/network/download";
import { rpc } from "@web/core/network/rpc";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, useSubEnv } from "@odoo/owl";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";

export const SCALE_LABELS = {
    day: _t("Day"),
    week: _t("Week"),
    month: _t("Month"),
    year: _t("Year"),
};

export class DemandPlanningMainComponent extends Component {
    static template = "gulfco_demand_planning.demand_planning";
    static components = {
        MrpMpsControlPanel,
        DemandPlanningLineComponent,
        CheckBox,
        MrpMpsSearchBar,
        ActionMenus,
        ViewScaleSelector,
    };
    static props = {
        ...standardActionServiceProps,
        searchDomain: { type: Array },
    };

    //--------------------------------------------------------------------------
    // Lifecycle
    //--------------------------------------------------------------------------
    setup() {
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.viewService = useService("view");

        const { orm, action, dialog } = this;
        this.model = new DemandPlanningModel(this.props, { orm, action, dialog });

        useSubEnv({
            demandPlanningPeriods: [],
            model: this.model,
            defaultPageLimit: 20,
            config: {
                ...this.env.config,
                offset: 0,
                limit: 20,
                mpsImportRecords: true,
            },
        });

        useSetupAction({
            getContext: () => {
                return this.props.action.context;
            },
        });

        useBus(this.model, "update", () => this.render(true));

        onWillStart(async () => {
            this.env.config.setDisplayName(_t("Demand Planning"));
            const domain = this.props.searchDomain;
            await this.model.load(domain, this.env.config.offset, this.env.config.limit);
        });

        usePager(() => {
            return {
                offset: this.env.config.offset,
                limit: this.env.config.limit,
                total: this.model.data.count,
                onUpdate: async ({ offset, limit }) => {
                    this.env.config.offset = offset;
                    this.env.config.limit = limit;
                    this.model.load(undefined, offset, limit);
                },
            };
        });
    }

    get lines() {
        console.log('fdsfsddsfdfsline',this.model.data.demand_planning_ids);
        return this.model.data.demand_planning_ids;
    }

    get groupedByVendorId()
    {
        const groupedByVendorId  = this.model.data.demand_planning_ids.reduce((acc, item) => {
                let key;
                if (Array.isArray(item.vendor_id)) {
                key = item.vendor_id[1];
                } else if (item.vendor_id === false || item.vendor_id === undefined) {
                key = 'Without Vendor';
                } else {
                key = String(item.vendor_id);
                }
                if (!acc[key]) {
                acc[key] = [];
                }
                acc[key].push(item);
                return acc;
        }, {});
        console.log('asasdd',groupedByVendorId);
        return groupedByVendorId;
    }

    get demandPlanningPeriods() {
        return this.model.data.dates;
    }

    get periodTypes() {
        return Object.fromEntries(
            this.model.data.demand_planning_period_types.map((s) => [s, { description: SCALE_LABELS[s] }])
        );
    }

    get currentPeriodType() {
        return this.model.data.demand_planning_period;
    }

    get isInDefaultPeriod() {
        return this.model.data.demand_planning_period === this.model.data.default_period;
    }

    async setScale(scale) {
        await this.model.load(
            this.props.searchDomain,
            this.env.config.offset,
            this.env.config.limit,
            scale,
        );
    }

    get groups() {
        return this.model.data.groups[0];
    }

    get isSelected() {
        return this.model.selectedRecords.size === this.lines.length;
    }

    toggleSelection() {
        this.model.toggleSelection();
    }

    /**
     * Handles the click on replenish button. It will call action_replenish with
     * all the Ids present in the view.
     *
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickReplenish(ev) {
        const action = await this.orm.call(
            "demand.planning",
            "action_order_analysis",
            [[],this.model.data.demand_planning_ids.map((p) => (p.id))],
        );
        return this.action.doAction(action);
    }

    _onMouseOverReplenish(ev) {
        this.model.mouseOverReplenish();
    }

    _onMouseOutReplenish(ev) {
        this.model.mouseOutReplenish();
    }

    _onClickCreate(ev) {
        this.model._createProduct();
    }

    get actionMenuItems() {
        return {
            action: [
                {
                    key: "export",
                    description: _t("Export"),
                    callback: () => this.onExportData(),
                },
                {
                    key: "delete",
                    description: _t("Delete"),
                    callback: () => this.model.unlinkSelectedRecord(),
                }
            ],
        };
    }

    get isRecordSelected() {
        return this.model.selectedRecords.size > 0;
    }

    async getExportedFields(model, import_compat, parentParams) {
        const resIds = Array.from(this.model.selectedRecords);
        const ids = resIds.length > 0 && resIds;
        const domain = [['id', 'in', ids]]
        return await rpc("/web/export/get_fields", {
            ...parentParams,
            model,
            domain,
            import_compat,
        });
    }

    async downloadExport(fields, import_compat, format) {
        const resIds = Array.from(this.model.selectedRecords);
        const exportedFields = fields.map((field) => ({
            name: field.name || field.id,
            label: field.label || field.string,
            store: field.store,
            type: field.field_type,
        }));
        if (import_compat) {
            exportedFields.unshift({ name: "id", label: _t("External ID") });
        }
        await download({
            data: {
                data: JSON.stringify({
                    import_compat,
                    context: this.props.context,
                    domain: this.model.domain,
                    fields: exportedFields,
                    ids: resIds.length > 0 && resIds,
                    model: "demand.planning",
                }),
            },
            url: `/web/export/${format}`,
        });
    }

    /**
     * Opens the Export Dialog
     *
     * @private
     */
    onExportData() {
        const dialogProps = {
            context: this.props.context,
            defaultExportList: [],
            download: this.downloadExport.bind(this),
            getExportedFields: this.getExportedFields.bind(this),
            root: {
                resModel: "demand.planning",
                activeFields: [],
            },
        };
        this.dialog.add(ExportDataDialog, dialogProps);
    }
}
