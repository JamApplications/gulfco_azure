/** @odoo-module **/

import MainComponent from "@stock_barcode/components/main";
import { barcodeStore } from "../control_panel/barcode_store";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Mutex } from "@web/core/utils/concurrency";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { View } from "@web/views/view";
import { url } from '@web/core/utils/urls';


patch(MainComponent.prototype, {
     async onWillStart() {
        debugger;
        const barcodeData = await rpc("/stock_barcode/get_barcode_data", {
            model: this.resModel,
            res_id: this.resId,
            emp_id: barcodeStore.empId,
        });
        barcodeData.actionId = this.props.actionId;
        this.config = { play_sound: true, ...barcodeData.data.config };
        if (this.config.play_sound) {
            const fileExtension = new Audio().canPlayType("audio/ogg") ? "ogg" : "mp3";
            this.sounds = {
                error: new Audio(url(`/barcodes/static/src/audio/error.${fileExtension}`)),
                notify: new Audio(url(`/mail/static/src/audio/ting.${fileExtension}`)),
                success: new Audio(url(`/stock_barcode/static/src/audio/success.${fileExtension}`)),
            };
            this.sounds.error.load();
            this.sounds.notify.load();
            this.sounds.success.load();
        }
        this.setupCameraScanner();
        this.groups = barcodeData.groups;
        this.env.model.setData(barcodeData);
        this.state.displayNote = Boolean(this.env.model.record.note);
        this.env.model.addEventListener("process-action", this._onDoAction.bind(this));
        this.env.model.addEventListener("refresh", (ev) => this._onRefreshState(ev.detail));
        this.env.model.addEventListener("update", () => {
            if (!this.state.uiBlocked) {
                this.render(true);
            }
        });
        this.env.model.addEventListener("history-back", () => this._exit());
    }
});