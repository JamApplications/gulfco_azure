/** @odoo-module **/
import { Component,onMounted } from "@odoo/owl";

export class SaveToOrderQtyTrigger extends Component {
    static props = {
        line_id: Number,
        date_index: Number,
        qty: Number,
    };
    setup() {
         console.log("setup called");
        this.model = this.env.model
        onMounted(async () => {
            this.model.loading = true;
            const { line_id, date_index, qty } = this.props;
            try {
                await this.model._saveActualToOrderQTY(line_id, date_index, qty);
                this.model.loading = false;
                console.log(`Saved qty=${qty} for line ${line_id}`);
            } catch (err) {
                console.error("Failed to save:", err);
            }
        });
    }
}
SaveToOrderQtyTrigger.template = "gulfco_demand_planning.SaveToOrderQtyTrigger";
