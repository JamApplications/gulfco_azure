/** @odoo-module **/

import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { patch } from "@web/core/utils/patch";
import BarcodePickingBatchModel from '@stock_barcode_picking_batch/models/barcode_picking_batch_model';

import { registry } from "@web/core/registry";
const formatters = registry.category("formatters");
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { pinDialog } from "./PinInputDiolog";

import { session } from "@web/session";
import { user } from "@web/core/user";
import { Component, useSubEnv, xml } from "@odoo/owl";




patch(BarcodePickingBatchModel.prototype, {




    async get_current_user(user){
        debugger;
       return await rpc("/get/user/details", {
            user_id: user
        });
    },

    async confirmSelection() {
     debugger;

          if (this.needPickingType && this.selectedPickingTypeId) {
          debugger;
                // Applies the selected picking type to the batch.
                this.record.picking_type_id = this.cache.getRecord("stock.picking.type", this.selectedPickingTypeId);
                this.trigger('update');
          } else if (this.needPickings && this.selectedPickings.length) {
                debugger;
                const currentUser = await this.get_current_user(user);
                if (currentUser){

                    const dialogInstance = this.dialogService.add(pinDialog, {
                    confirm: async (pin) => {
                        debugger;
                        const result = await rpc("/validate/batch_picking/employee/barcode/", {
                                    access_pin: pin,
                                    res_id: this.resId,
                                    res_model: this.resModel,
                                });

                        if (result){
                            const data = await this.orm.call(
                                'stock.picking.batch',
                                'action_add_pickings_and_confirm',
                                [[this.resId],
                                {
                                    picking_type_id: this.record.picking_type_id.id,
                                    picking_ids: this.selectedPickings,
                                    state: 'in_progress',
                                }]
                            );
                            await this.refreshCache(data.records);
                            this.selectedPickings = [];
                            this.config = data.config || {}; // Get the picking type's scan restrictions configuration.
                            this.trigger('update');

                             // close open dilog box
                            this.dialogService.closeAll();

                        }
                        else{
                            this.dialog.add(AlertDialog, {
                                body: _t("No valid record to Found"),
                                dismiss: () => this.leaveEditMode({ discard: true }),
                            });
                            return false;
                        }
                    },
                    cancel: () => {},
                });

                }else{
                const data = await this.orm.call(
                        'stock.picking.batch',
                        'action_add_pickings_and_confirm',
                        [[this.resId],
                        {
                            picking_type_id: this.record.picking_type_id.id,
                            picking_ids: this.selectedPickings,
                            state: 'in_progress',
                        }]
                    );
                    await this.refreshCache(data.records);
                    this.selectedPickings = [];
                    this.config = data.config || {}; // Get the picking type's scan restrictions configuration.
                    this.trigger('update');
                }

          }
     },

});

