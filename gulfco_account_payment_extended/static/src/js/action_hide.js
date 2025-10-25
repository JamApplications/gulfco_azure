/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { rpc } from "@web/core/network/rpc";
import { ActionMenus} from "@web/search/action_menus/action_menus";

patch(ListController.prototype, {
    get actionMenuItems() {
        const originalItems = super.actionMenuItems;
        const selectedResModels = this.model.root.selection.map((r) => r.resModel);
        const is_move_line = selectedResModels.every(model => model === 'account.move.line');
        if (is_move_line && this.model.root.resModel === 'account.move.line') {
            const matching_numbers = this.model.root.selection.map((r) => r.data.matching_number);
            console.log('Valid Partner IDs:', matching_numbers);
            const uniqueMatchingNumbers = new Set(matching_numbers);
            console.log('Unique partner IDs:', uniqueMatchingNumbers);

            if(this.model.action && this.model.action.currentController && this.model.action.currentController.action && this.model.action.currentController.action.xml_id == 'account_accountant.action_move_line_posted_unreconciled'){
                var modifiedItems = {
                    ...originalItems,
                    action: originalItems.action.filter(item => {
                        return item.name !== 'Unreconcile';
                    }),
                };
            }
            else{
                var modifiedItems = {
                    ...originalItems,
                    action: originalItems.action.filter(item => {
                        return uniqueMatchingNumbers.size === 1 || item.name !== 'Unreconcile';
                    }),
                };
            }
            return modifiedItems;
        } else {
            console.warn('Selected records do not belong to account.move.line.');
            return originalItems;
        }
    }
});
