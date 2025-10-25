/** @odoo-module **/
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
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

import { Component, useSubEnv, xml } from "@odoo/owl";


import BarcodeQuantModel from '@stock_barcode/models/barcode_quant_model';

console.log("ji import quant data: ->:", BarcodeQuantModel)

patch(BarcodeQuantModel.prototype, {


     async get_current_user(user){
        debugger;
       return await rpc("/get/user/details", {
            user_id: user
        });
    },



    async _apply() {
        debugger;
        console.log("MY Inherite : apply button:,", this, this.pageLines)

        const currentUser = await this.get_current_user(user);

        if (currentUser){
            this.dialogService.add(pinDialog, {
            confirm: async (pin) => {
                debugger;
                const result = await rpc("/validate/stock_quant/employee/barcode/", {
                    access_pin: pin,
                    res_id: this.pageLines.filter(line => line.inventory_quantity_set).map(quant => quant.id),
                    res_model: this.resModel,
                });
                if (result){
                    await this.save();
                    const linesToApply = this.pageLines.filter(line => line.inventory_quantity_set);
                    const quantIds = linesToApply.map(quant => quant.id);
                    const action = await this.orm.call("stock.quant", "action_validate", [quantIds]);
                    const notifyAndGoAhead = res => {
                        if (res && res.special) { // Do nothing if come from a discarded wizard.
                            return this.trigger('refresh');
                        }
                        this.notification(this.validateMessage, { type: "success" });
                        this.trigger('history-back');
                    };
                    if (action && action.res_model) {
                        return this.action.doAction(action, { onClose: notifyAndGoAhead });
                    }
                    notifyAndGoAhead();
                }
                },
                 cancel: () => {},
            });


        }else{


                    await this.save();
                    const linesToApply = this.pageLines.filter(line => line.inventory_quantity_set);
                    const quantIds = linesToApply.map(quant => quant.id);
                    const action = await this.orm.call("stock.quant", "action_validate", [quantIds]);
                    const notifyAndGoAhead = res => {
                        if (res && res.special) { // Do nothing if come from a discarded wizard.
                            return this.trigger('refresh');
                        }
                        this.notification(this.validateMessage, { type: "success" });
                        this.trigger('history-back');
                    };
                    if (action && action.res_model) {
                        return this.action.doAction(action, { onClose: notifyAndGoAhead });
                    }
                    notifyAndGoAhead();
        }
    },


});