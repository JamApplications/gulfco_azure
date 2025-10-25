/** @odoo-module **/
import { reactive } from "@odoo/owl";

export const barcodeStore = reactive({
    empId: localStorage.getItem("barcodeEmpId") || null,
    setEmpId(empId) {
        this.empId = empId;
        localStorage.setItem("barcodeEmpId", empId);
    },
    clearEmpId() {
        this.empId = null;
        localStorage.removeItem("barcodeEmpId");
    },
});
