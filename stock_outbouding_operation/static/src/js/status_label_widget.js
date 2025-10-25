/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class StatusLabelWidget extends Component {
    setup() {
        this.label = this.props.value;
        this.colorClass = this.getColorClass(this.label);
    }

    getColorClass(label) {
    debugger;
    console.log("ji...:", label)
        if (label === "Delivery Done" || label === "Picked" || label === "Packed") {
            return "badge-success";
        } else if (label === "Ready to Pick" || label === "Ready to Pack") {
            return "badge-warning";
        } else {
            return "badge-secondary";
        }
    }
}

StatusLabelWidget.template = "stock_outbouding_operation.StatusLabelWidget";

registry.category("field_widgets").add("status_pill", StatusLabelWidget);
