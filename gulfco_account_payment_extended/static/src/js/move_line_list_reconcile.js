/** @odoo-module **/

import { AccountMoveLineReconcileListController } from "@account_accountant/components/move_line_list_reconcile/move_line_list_reconcile";

import { patch } from "@web/core/utils/patch";

patch(AccountMoveLineReconcileListController.prototype, {
   importDataWizard(){
    return this.actionService.doAction("gulfco_account_payment_extended.action_open_import_wizard_from_move_line");
   }
});