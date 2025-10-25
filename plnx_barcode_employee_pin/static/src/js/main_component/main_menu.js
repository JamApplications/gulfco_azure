/** @odoo-module **/
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { MainMenu } from "@stock_barcode/main_menu/main_menu";

import { pinDialog } from "../PinInputDiolog";

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
console.log("iiiiiiiiiiiiioooopp:");

import { barcodeStore } from "../control_panel/barcode_store";





patch(MainMenu.prototype, {

     setup() {
        super.setup();
        this.state.EmpID = false;
//        this.barcodeStore.empId = '';

     },


    async get_current_user(user){
           return await rpc("/get/user/details", {
                user_id: user
            });
    },



    async openManualBarcodeDialog(){
        debugger;
        console.log("0-00 my test---")

        const currentUser = await this.get_current_user(user);
            if (currentUser){

                const result = await new Promise((resolve, reject) => {
                        this.dialogService.add(pinDialog, {
                            confirm: async (pin) => {
                                    debugger;

                                      const result = await rpc("/barcode/employee/validation/", {
                                            access_pin: pin,
                                            res_model: "hr.employee",
                                        });

                                      console.log("hi...:", result, this)

                                      if (result){
                                            await super.openManualBarcodeDialog();
                                      }else{
                                             this.dialogService.add(AlertDialog, {
                                                body: _t("No valid record to Found"),
                                                dismiss: () => this.leaveEditMode({ discard: true }),
                                            });
                                            return false;
                                      }
                            },
                            cancel: () => {},
                        });
                    });
                    // Proceed only if confirmed
                    if (result){
                        await super.openManualBarcodeDialog();
                    }

                await super.openManualBarcodeDialog();

            }else{
                await super.openManualBarcodeDialog();
            }
    },

    async onClickOperations() {
    console.log("my custom butotm click..")

        const currentUser = await this.get_current_user(user);
        if (currentUser){
            try {
                    const result = await new Promise((resolve, reject) => {
                        this.dialogService.add(pinDialog, {
                            confirm: async (pin) => {
                            debugger;
                                      const result = await rpc("/barcode/employee/validation/", {
                                            access_pin: pin,
                                            res_model: "hr.employee",
                                        });

                                      console.log("hi...:", result, this)

                                      if (result){
                                            barcodeStore.setEmpId(result);
                                             const context = {
                                                    emp_id: barcodeStore.EmpID,
                                                    // Add any other context parameters you need
                                                };
                                             const domain = [['picker_partner_id', '=', barcodeStore.empId]];
                                            this.state.EmpID = result;
                                            this.actionService.doAction('stock_barcode.stock_picking_type_action_kanban');
//                                             {  context: context,
//                                                domain: domain, });
                                      }else{
                                             this.dialogService.add(AlertDialog, {
                                                body: _t("No valid record to Found"),
                                                dismiss: () => this.leaveEditMode({ discard: true }),
                                            });
                                            return false;
                                      }

                            },
                            cancel: () => {},
                        });
                    });
                    debugger;
                    // Proceed only if confirmed
                    if (result){
                        this.actionService.doAction('stock_barcode.stock_picking_type_action_kanban');
                    }
                } catch (err) {
                    // Cancelled or error
                    console.log("Popup cancelled", err);
                }
        }else{
            this.actionService.doAction('stock_barcode.stock_picking_type_action_kanban');
        }
    },


     async onClickInventoryCount() {
    console.log("my onClickInventoryCount click..")

        const currentUser = await this.get_current_user(user);
        if (currentUser){
            debugger;
            try {
                    const result = await new Promise((resolve, reject) => {
                        this.dialogService.add(pinDialog, {
                            confirm: async (pin) => {
                                     const result = await rpc("/barcode/employee/validation/", {
                                            access_pin: pin,
                                            res_model: "hr.employee",
                                        });

                                      console.log("hi...:", result, this)

                                      if (result){
                                            barcodeStore.setEmpId(result);
                                            this.actionService.doAction('stock_barcode.stock_barcode_inventory_client_action');
                                      }else{
                                             this.dialogService.add(AlertDialog, {
                                                body: _t("No valid record to Found"),
                                                dismiss: () => this.leaveEditMode({ discard: true }),
                                            });
                                            return false;
                                      }

                            },
                            cancel: () => {},
                        });
                    });
                    // Proceed only if confirmed
                    if (result){
                        this.actionService.doAction('stock_barcode.stock_barcode_inventory_client_action');
                    }
                } catch (err) {
                    // Cancelled or error
                    console.log("Popup cancelled", err);
                }
        }else{
            this.actionService.doAction('stock_barcode.stock_barcode_inventory_client_action');
        }
    },


});


