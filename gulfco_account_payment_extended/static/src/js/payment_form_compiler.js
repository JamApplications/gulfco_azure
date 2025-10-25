/** @odoo-module **/

import { formView } from '@web/views/form/form_view';
import { registry } from "@web/core/registry";
import { FormCompiler } from "@web/views/form/form_compiler";

export class PaymentFormCompiler extends FormCompiler {
    compileField(el, params) {
        const field = super.compileField(el, params);
        field.setAttribute(
            "readonly",
            `__comp__.props.record?.data?.state != 'draft' ? true : false`
        );
        return field;
    }
}

registry.category("views").add("is_readonly_payment", {
    ...formView,
    Compiler: PaymentFormCompiler,
});