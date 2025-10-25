/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { onMounted, useState, useEffect } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { router } from "@web/core/browser/router";
import { useService } from "@web/core/utils/hooks";
import { MainMenu } from "@stock_barcode/main_menu/main_menu";
import { barcodeStore } from "./barcode_store";
import { registry } from "@web/core/registry";


patch(ControlPanel.prototype, {
    setup() {
        super.setup();
         this.orm = useService("orm");
        this.router = router;
//        this.state = useState({
//                        isBarcodeOps: false,
//                        pickings: [],
//                    });

        const emp_id = barcodeStore.empId
        this.state.emp_id = emp_id;
        this.state.isBarcodeOps = emp_id;
        this.state.pickings = useState([]);
        this.main_menu = MainMenu;
        this.actionService = useService("action");
            useEffect(() => {
//                this.checkAndLoadPickings(emp_id);
                this.loadPickings(emp_id);
//                window.location.reload();
            }, () => [this.router.current]);

    },

    async checkAndLoadPickings(emp_id) {

       const actionId = this.router.current?.action;
       if (typeof actionId === "number") {
            const action = await this.actionService.loadAction(actionId);
            const isBarcode = action?.xml_id === "stock_barcode.stock_picking_type_action_kanban";
//            this.state.isBarcodeOps = isBarcode;
            if (isBarcode) {
                    this.state.isBarcodeOps = true;
                    await this.loadPickings(emp_id);
            }

        }
    },

    async waitForEmpId(timeout = 3000) {
        const interval = 100;
        let waited = 0;
        while (!barcodeStore.empId && waited < timeout) {
            await new Promise((resolve) => setTimeout(resolve, interval));
            waited += interval;
        }
    },

    async loadPickings(emp_id) {
        try {
        await this.waitForEmpId();
//            const empId = barcodeStore.empId;
            const empId = emp_id;
             if (!empId) {
//             debugger;
                    console.warn("No EmpID set. Skipping picking load.");
                    return;
                }
//                debugger;
            const result = await rpc("/my/barcode/user/pickings", {'emp_id':empId} );
            this.state.pickings.splice(0, this.state.pickings.length, ...result);
        } catch (error) {
            console.error("Failed to load pickings:", error);
        }
    },


    async get_pik_operation(pickings) {
        debugger;
        let emp_id = barcodeStore.empId;
        let idList = pickings.map(item => item.id);

        const context = {'emp_id': emp_id};
        const domain = [['id', 'in', idList]];

//        debugger;
        const action = await this.orm.call(
            "stock.picking.type",
            "get_filtered_action_picking_tree_ready_kanban",
            [false, idList, emp_id],
        );
        return this.actionService.doAction(action);
    },


//    openPicking(pickingId) {
//        this.actionService.doAction({
//            type: 'ir.actions.act_window',
//            res_model: 'stock.picking',
//            res_id: pickingId,
//            view_mode: 'form',
//            target: 'current', // or 'new' if you want it in a popup
//        });
//    }

});
