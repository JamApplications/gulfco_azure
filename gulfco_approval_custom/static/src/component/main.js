import { Record } from "@mail/core/common/record";
import { DemandPlanningMainComponent } from "@gulfco_demand_planning/components/main";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { Component, onWillStart, useSubEnv } from "@odoo/owl";

patch(DemandPlanningMainComponent.prototype, {
    setup() {
        super.setup();
        onWillStart(async () =>{
            this.show_order_button = await user.hasGroup("gulfco_contact_registration_custom.group_div_head_approval");
        });
    },
});
