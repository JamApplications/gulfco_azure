/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { FormController } from "@web/views/form/form_controller";
import { formView } from '@web/views/form/form_view';
import { registry } from "@web/core/registry";
console.log("jhvgh---:llllllll");
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";



patch(ListController.prototype, {
    setup () {
        super.setup();
        this.orm = useService("orm");
    },

    get actionMenuItems() {
//        debugger;
        const originalItems = super.actionMenuItems;
        // Remove the archive/unarchive actions from the "Actions" dropdown

        if (originalItems.action && this.props.resModel == 'res.partner' ) {
            originalItems.action = originalItems.action.filter(action => {
                return !["unarchive"].includes(action.key);
            });
        }
        return originalItems;
    }
});



//export class ContactListController extends ListController {
//
//    async getStaticActionMenuItems() {
//    debugger;
//        const menuItems = super.getStaticActionMenuItems();
//
//
////         if (!this.model?.root?.data || !this.model.root.selection) {
////            return menuItems;  // fallback early
////        }
//         // Get selected record IDs
//        const selectedRecords = this.model.root.selection;
//
//         const selectedResIds = await this.getSelectedResIds();
//
//
//        // You can also get the full record data:
////        const selectedData = this.model.root.data.filter(record =>
////            selectedRecords.includes(record.id)
////        );
//
//
//        if ('unarchive' in menuItems) {
//            delete menuItems.unarchive;
//        }
//
//        // Remove 'unarchive' from the 'other' group (if it exists)
//        if (menuItems.other && 'unarchive' in menuItems.other) {
//            delete menuItems.other.unarchive;
//        }
//
//        return menuItems;
//
////        if (this.props.resModel === 'res.partner' && menuItems.unarchive) {
////
////        debugger
//////         delete menuItems.unarchive;
////         menuItems = menuItems.filter(item => item.key !== 'unarchive');
////
////        debugger
////            // Example logic: remove 'unarchive' if any selected record is inactive
//////            const hasInactive = selectedData.some(rec => rec.data.active === false);
//////            if (hasInactive && menuItems.other) {
////
//////if (record.active === false && menuItems.unarchive && this.model.root.resModel === 'res.partner') {
//////            delete menuItems.unarchive;
//////        }
//////            if (this.model.root.resModel === 'res.partner' && menuItems.unarchive) {
////////                menuItems.other = menuItems.other.filter(item => item.key !== 'unarchive');
//////                delete menuItems.unarchive;
//////            }
////
////
////        }
////
////        return menuItems;
//
//
////        const records = this.model.root.data;
////        if (record.active === false && menuItems.unarchive && this.model.root.resModel === 'res.partner') {
////            delete menuItems.unarchive;
////        }
////        return menuItems;
//    }
//}


//registry.category("controllers").add("contact_list_not_unarchive", ContactListController);
//
//registry.category("views").add("contact_list_not_unarchive", {
//    ...listView,
//    Controller: ContactListController,
//});


export class ContactFormController extends FormController {

    getStaticActionMenuItems() {
    debugger;
        const menuItems = super.getStaticActionMenuItems();
        const record = this.model.root.data;
        if (record.active === false && menuItems.unarchive && this.model.root.resModel === 'res.partner') {
            delete menuItems.unarchive;
        }
        if (this.model.root.resModel === 'res.partner' && this.props.context)
        {
           this.props.context.is_res_partner_action = 1;
        }

        return menuItems;
    }
}

registry.category("views").add("contact_not_unarchive", {
    ...formView,
    Controller: ContactFormController,
});