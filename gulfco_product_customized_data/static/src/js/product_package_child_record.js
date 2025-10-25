///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { FormController } from "@web/views/form/form_controller";
//import { onMounted, onWillUnmount } from "@odoo/owl";
//
//class ProductFormController extends FormController {
//    setup() {
//    debugger;
//        super.setup();
//
//        this._interval = null;
//
//        onMounted(() => {
//            this._startPollingPackages();
//        });
//
//        onWillUnmount(() => {
//            if (this._interval) {
//                clearInterval(this._interval);
//            }
//        });
//    }
//
//    _startPollingPackages() {
//        this._interval = setInterval(() => {
//            const packagingLines = this.model.data.packaging_ids || [];
//            const allLineIds = packagingLines.map(pkg => pkg.id).filter(id => id);
//
//            for (const line of packagingLines) {
//                if (!line || !line.id) continue;
//
//                const otherIds = allLineIds.filter(id => id !== line.id);
//                const lineRecord = this.model.get(line.id);
//                if (lineRecord) {
//                    lineRecord.update({
//                        secondary_package: {
//                            domain: [['id', 'in', otherIds]],
//                        },
//                    });
//                }
//            }
//        }, 5); // Check every second
//    }
//}
//
//registry.category("views").add("product_form_custom", {
//    ...registry.category("views").get("form"),
//    Controller: ProductFormController,
//});
//
//
//
//
//
//
/////** @odoo-module **/
////
////import { registry } from '@web/core/registry';
////import { onMounted, useEffect } from '@odoo/owl';
////import { FormController } from '@web/views/form/form_controller';
////
////console.log("load form controlelr Js jjhfjdk:");
////class ProductFormController extends FormController {
////
////    setup() {
////    console.log("kjhgfhj----:", this);
////        super.setup();
//////        onMounted(() => {
//////            this._syncSecondaryPackages();
//////        });
//////      useWatcher(
//////                () => this.model.data.packaging_ids,
//////                () => this._updateSecondaryPackages()
//////            );
////    }
////     async onFieldChanged(event) {
////         debugger;
////        // Call super to preserve base behavior
////        await super.onFieldChanged(event);
////
////        // Check if the changed field is 'packaging_ids'
////        if (event.detail.data && 'packaging_ids' in event.detail.data) {
////            debugger;
////            this._updateSecondaryPackages();
////        }
////    }
////
//////    async _syncSecondaryPackages() {
//////        // Watch for packaging_ids field changes
//////        this.env.bus.on('FIELD_CHANGED', this, ({ data }) => {
//////            if (data.name === 'packaging_ids') {
//////                this._updateSecondaryPackages();
//////            }
//////        });
//////    }
////
////    _updateSecondaryPackages() {
////    debugger;
////        const packagingLines = this.model.data.packaging_ids || [];
////        const secondaryField = this.model.data.product_secondary_package || [];
////
////        // Extract unique IDs of packaging lines
////        const newIds = new Set(packagingLines.map(pkg => pkg.id).filter(id => id));
////        const existingIds = new Set(secondaryField.map(pkg => pkg.id));
////
////        const allIds = Array.from(new Set([...existingIds, ...newIds]));
////
////        this.model.update({
////            product_secondary_package: allIds.map(id => ({ id }))
////        });
////    }
////}
////
////registry.category('views').add('product_form_custom', {
////    ...registry.category('views').get('form'),
////    Controller: ProductFormController,
////});
////
////
////
////
//
//
//
//
/////** @odoo-module **/
////
////import { registry } from "@web/core/registry";
////import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
////
////console.log("jhgfhjp------------:")
////export class AutoSaveResPartnerField extends X2ManyField {
////     async onAdd({ context, editable } = {}) {
////     debugger;
////        await this.props.record.model.root.save();
////        await super.onAdd({ context, editable });
////     }
////}
////
////export const autoSaveResPartnerField = {
////    ...x2ManyField,
////    component: AutoSaveResPartnerField,
////};
////
////registry.category("fields").add("dynamic_secondary_filter", autoSaveResPartnerField);
////
//
//
//
/////** @odoo-module **/
////import { useService } from "@web/core/utils/hooks";
////console.log("hi 09876")
//////import { registry } from "@web/core/registry";
//////import { standardFieldProps } from "@web/views/fields/standard_field_props";
//////import { useEffect } from "@odoo/owl";
//////import { Component } from "@odoo/owl";
//////import { Component,  useState, useField } from "@odoo/owl";
//////import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
////
////
////import { registry } from "@web/core/registry";
////import { Component } from "@odoo/owl";
////import { standardFieldProps } from "@web/views/fields/standard_field_props";
////
////
//////import { registry } from "@web/core/registry";
////console.log("hi 1")
//////import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
//////console.log("hi 2")
//////import { standardFieldProps } from "@web/views/fields/standard_field_props";
//////import { useField } from "@odoo/owl";
//////console.log("hi 3")
//////import { useEffect } from "@odoo/owl";
////
////const fieldRegistry = registry.category("fields");
////
////console.log("HI tis my cistome iwdhet Js:")
////
////export class DynamicSecondaryFilter extends Component {
////
////    static props = { ...standardFieldProps };
////    setup() {
////
////        this.field = useService("field");
////        debugger;
//////        const parentRecord = this.field.record?.parent;
//////        if (!parentRecord) return;
//////
//////        // Watch for updates in packaging_ids
//////        useEffect(() => {
//////            const currentPackages = parentRecord.data.packaging_ids || [];
//////
//////            const existingSecondary = new Set(
//////                (parentRecord.data.product_secondary_package || []).map(p => p.id)
//////            );
//////
//////            const updatedPackages = [
//////                ...(parentRecord.data.product_secondary_package || []),
//////                ...currentPackages.filter(pkg => !existingSecondary.has(pkg.id))
//////            ];
//////
//////            // Update the parent field in memory
//////            parentRecord.update({
//////                product_secondary_package: updatedPackages,
//////            });
//////        }, [this.field.record.data.name]); // use a stable dependency if needed
////    }
////
//////    render() {
//////        return Many2OneField(this.props);
//////    }
////
////}
////
////
//////DynamicSecondaryFilter.props = {
//////    ...standardFieldProps,
//////};
////
////DynamicSecondaryFilter.supportedTypes = ["many2one"];
////
////fieldRegistry.add("dynamic_secondary_filter", DynamicSecondaryFilter);
////
////
////
///////** @odoo-module **/
//////
//////import { FormController } from "@web/views/form/form_controller";
//////
//////console.log("new form controler package save js:")
//////export class CustomFormController extends FormController {
//////    async saveOne2manyLine(lineRecord) {
//////    debugger;
//////        // lineRecord is a child record of the One2many (not saved yet)
//////        const saved = await this.model.save(lineRecord.id);
//////        return saved;
//////    }
//////}
