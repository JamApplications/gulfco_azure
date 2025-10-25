/** @odoo-module **/

import BarcodeModel from '@stock_barcode/models/barcode_model';
import { patch } from "@web/core/utils/patch";
import { barcodeStore } from "./control_panel/barcode_store";

patch(BarcodeModel.prototype, {
    getActionRefresh(newId) {
        return {
            route: '/stock_barcode/get_barcode_data',
            params: {model: this.resModel, res_id: this.resId || false, emp_id: barcodeStore.empId || false},
        };
    }
});
