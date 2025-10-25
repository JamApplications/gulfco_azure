/** @odoo-module **/

import { Component, onWillStart } from "@odoo/owl";
import { useInputField } from "@web/views/fields/input_field_hook";
import { formatDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { DateTimeField, dateTimeField } from "@web/views/fields/datetime/datetime_field";
import { localization } from "@web/core/l10n/localization";

class OnlyDateFieldWidget extends DateTimeField {
    static template = "plennix_date_widget.OnlyDateWidget";

    getFormattedValue(valueIndex) {
        console.log('0000000000000000000',valueIndex)
        const value = this.values[valueIndex];
        if (!value){
            return;
        }
        return formatDate(value, { format: "yyyy-MM-dd" });
    }


}

registry.category("fields").add("only_date", {
    ...dateTimeField,
    component: OnlyDateFieldWidget,
});
