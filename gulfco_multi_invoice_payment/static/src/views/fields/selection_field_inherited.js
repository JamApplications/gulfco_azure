/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { user } from "@web/core/user";
import { onWillStart } from "@odoo/owl";

patch(SelectionField.prototype, {

    setup() {
        super.setup();
        onWillStart(async () => {
            this.hasQuickPaymentGroup = await user.hasGroup("gulfco_multi_invoice_payment.group_allow_quick_payment");
        });
    },

    get options() {
        const res = super.options;
        if (
            this.props.name === "payment_type_selection" &&
            this.props.record?.resModel === "account.payment" &&
            this.props.record?.data?.payment_type === "outbound" &&
            !this.hasQuickPaymentGroup
        ) {
            // Filter out 'quick_payment'
            return res.filter(([value]) => value !== "quick_payment");
        }
        // Fallback to the original options getter
        return res;
    },

    get string() {
        if (this.type == "selection" 
            && this.props.name === "payment_type_selection" 
            && this.props.record.data[this.props.name] === "quick_payment" 
            && !this.hasQuickPaymentGroup) 
        {
            return "Quick Payment";
        }
        return super.string;
    },
});
