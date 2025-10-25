/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { rpc } from "@web/core/network/rpc";
import { ActionMenus} from "@web/search/action_menus/action_menus";



patch(ListController.prototype, {
    setup () {
        super.setup();
        this.orm = useService("orm");
        },

    get actionMenuItems() {
        debugger;
        const originalItems = super.actionMenuItems; // Store the original action items
//        console.log(originalItems, '---originalItems:');

        // Check if the selected records belong to 'purchase.order.line'
        const selectedResModels = this.model.root.selection.map((r) => r.resModel);
        const isPurchaseOrderLine = selectedResModels.every(model => model === 'purchase.order.line');
//        console.log(isPurchaseOrderLine, '---isPurchaseOrderLine:');
        if (isPurchaseOrderLine && this.model.root.resModel === 'purchase.order.line') {
            // Extract valid partner IDs and names
            const validPartnerIds = this.model.root.selection.map((r) => r.data.partner_id[0]);
            const validPartnerNames = this.model.root.selection.map((r) => r.data.partner_id[1]);
            console.log('Valid Partner IDs:', validPartnerIds);
            console.log('Valid Partner Names:', validPartnerNames);

            // Check if all selected records have the same partner_id
            const uniquePartnerIds = new Set(validPartnerIds);
            console.log('Unique partner IDs:', uniquePartnerIds);

            // Modify action items based on partner ID check
            const modifiedItems = {
                ...originalItems,
                action: originalItems.action.filter(item => {
                    // Hide action if not all selected records have the same partner_id
                    return uniquePartnerIds.size === 1 || item.sequence !== 1001; // Replace 1001 with your action key
                }),
            };

            return modifiedItems; // Return the modified action items
        } else {
            console.warn('Selected records do not belong to purchase.order.line.');
            return originalItems; // Return original items if the condition is not met
        }
    }

});
