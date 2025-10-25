/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { formView } from '@web/views/form/form_view';
import { registry } from "@web/core/registry";
import { FormCompiler } from "@web/views/form/form_compiler";

export class ProductFormController extends FormController {
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const record = this.model.root.data;
        if (record.active === false && menuItems.unarchive && this.model.root.resModel === 'product.template' || this.model.root.resModel === 'product.product') {
            delete menuItems.unarchive;
        }
        return menuItems;
    }
    async save(params) {
        if(this.props.resModel && this.props.resModel == 'product.template')
        {
            this.props.context.from_create_prod_template = 1;
        }
        return await super.save(params);
    }
}
export class ProductFormCompiler extends FormCompiler {
    compileField(el, params) {
        const field = super.compileField(el, params);
        field.setAttribute(
            "readonly",
            `__comp__.props.record?.data?.registration_status == 'approved' && !__comp__.props.record?.data?.is_all_edit ? true : false`
        );
        return field;
    }
}

registry.category("views").add("is_not_unarchive", {
    ...formView,
    Controller: ProductFormController,
    Compiler: ProductFormCompiler,
});