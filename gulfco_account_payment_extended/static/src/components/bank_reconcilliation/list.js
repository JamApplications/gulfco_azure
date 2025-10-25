/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { omit } from "@web/core/utils/objects";

import { BankRecListController } from "@account_accountant/components/bank_reconciliation/list";
import { ListController } from "@web/views/list/list_controller";
import { ActionMenus, STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";


patch(ListController.prototype, {

    get actionMenuProps() {
        const actionMenuProps = {
            ...super.actionMenuProps,
        };
        if (actionMenuProps && actionMenuProps.context.list_view_ref === 'account_accountant.view_account_move_line_list_bank_rec_widget'){
            actionMenuProps.items = this.actionMenuItemsMatchingEntries;
        }
        return actionMenuProps
    },

    get actionMenuItemsMatchingEntries() {
        const { actionMenus } = this.props.info;
        const staticActionItems = Object.entries(this.getStaticActionMenuItemsMatchingEntries())
            .filter(([key, item]) => item.isAvailable === undefined || item.isAvailable())
            .sort(([k1, item1], [k2, item2]) => (item1.sequence || 0) - (item2.sequence || 0))
            .map(([key, item]) =>
                Object.assign(
                    { key, groupNumber: STATIC_ACTIONS_GROUP_NUMBER },
                    omit(item, "isAvailable")
                )
            );

        return {
            action: [...staticActionItems, ...(actionMenus?.action || [])],
            print: actionMenus?.print,
        };
    },

    getStaticActionMenuItemsMatchingEntries() {
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: _t("Export"),
                callback: () => this.onExportData(),
            }
        };
    }

});
