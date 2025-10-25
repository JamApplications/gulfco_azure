/** @odoo-module **/
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { patch } from "@web/core/utils/patch";
import MainComponent from "@stock_barcode/components/main";
//import  PinInputDialog  from './PinInputDialog';
import { pinDialog } from "./PinInputDiolog";

import { registry } from "@web/core/registry";
const formatters = registry.category("formatters");
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

import { session } from "@web/session";
import { user } from "@web/core/user";

import { kanbanView } from '@web/views/kanban/kanban_view';
import { StockBarcodeKanbanController } from '@stock_barcode/kanban/stock_barcode_kanban_controller';
import { StockBarcodeKanbanRenderer } from '@stock_barcode/kanban/stock_barcode_kanban_renderer';;

import { Component, useSubEnv, xml } from "@odoo/owl";


import { barcodeStore } from "./control_panel/barcode_store";

patch(StockBarcodeKanbanController.prototype, {

    setup() {
//    debugger;
        super.setup();
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.employee_id = barcodeStore.empId;
//        this.employee_id = this.props.context.default_picking_type_id;

    },

    async get_current_user(user){
        debugger;
       return await rpc("/get/user/details", {
            user_id: user
        });
    },

   async openRecord(record) {
        debugger;
        const currentUser = await this.get_current_user(user);

//        const employee_id = this.action.currentController.action.context.default_picker_partner_id


//        debugger;
        if (this.employee_id){
            debugger;
              const employee_id = this.employee_id;
              const picking_object = await this.orm.call(
                "hr.employee",
                "get_direct_employees_pin_validated",
                [record.res_id, employee_id, record.resId, record.resModel],
            );
            if (picking_object){
//                debugger;

                 if (this.props.resModel === 'mrp.production') {
//                    debugger;
                    return this.actionService.doAction('stock_barcode_mrp.stock_barcode_mo_client_action', {
                        additionalContext: { active_id: record.resId },
                    });
                }
                else{
//                    debugger;
                    if (employee_id){
                        this.actionService.doAction('stock_barcode.stock_barcode_picking_client_action', {
                            additionalContext: { active_id: record.resId , employee_id: employee_id},
                        });
                    }else{
                        this.dialog.add(AlertDialog, {
                            body: _t("No valid record to Found"),
                            dismiss: () => this.leaveEditMode({ discard: true }),
                        });
                        return false;
                    }
                }


            }

        }
        else if (currentUser){
//        debugger
            this.dialogService.add(pinDialog, {
            confirm: async (pin) => {
//                debugger;
                const result = await rpc("/validate/employee/barcode/", {
                    access_pin: pin,
                    res_id: record.resId,
                    res_model: record.resModel,
                })
                if (this.props.resModel === 'mrp.production') {
                    return this.actionService.doAction('stock_barcode_mrp.stock_barcode_mo_client_action', {
                        additionalContext: { active_id: record.resId },
                    });
                }
                else{

                    if (result){
                        this.actionService.doAction('stock_barcode.stock_barcode_picking_client_action', {
                            additionalContext: { active_id: record.resId , employee_id: result},
                        });
                    }else{
                        this.dialog.add(AlertDialog, {
                            body: _t("No valid record to Found"),
                            dismiss: () => this.leaveEditMode({ discard: true }),
                        });
                        return false;
                    }
                }
            },
            cancel: () => {},
        });
        }else{
             super.openRecord(record);
        }
    },

});





