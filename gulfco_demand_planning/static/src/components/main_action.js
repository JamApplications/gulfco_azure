/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { WithSearch } from "@web/search/with_search/with_search";
import { DemandPlanningMainComponent } from '@gulfco_demand_planning/components/main';
import { MrpMpsSearchModel } from '@mrp_mps/search/mrp_mps_search_model';
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart } from "@odoo/owl";

export class DemandPlanningAction extends Component {
    static template = "gulfco_demand_planning.demand_planning_action";
    static components = { WithSearch, DemandPlanningMainComponent };
    static props = {...standardActionServiceProps};

    setup() {
        this.viewService = useService("view");
        this.resModel = "demand.planning";

        onWillStart(async () => {
            const views = await this.viewService.loadViews(
                {
                    resModel: this.resModel,
                    context: this.props.action.context,
                    views: [[false, "search"]],
                }
            );
            this.withSearchProps = {
                resModel: this.resModel,
                SearchModel: MrpMpsSearchModel,
                context: this.props.action.context,
                domain: this.props.action.domain,
                orderBy: [{name: "id", asc: true}],
                searchMenuTypes: ['filter', 'favorite'],
                searchViewArch: views.views.search.arch,
                searchViewId: views.views.search.id,
                searchViewFields: views.fields,
                loadIrFilters: true
            };
        });
    }
}

registry.category("actions").add("demand_planning_client_action", DemandPlanningAction);
