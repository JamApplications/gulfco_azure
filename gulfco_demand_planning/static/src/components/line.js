/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { useService, useBus } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { Component, useRef, onPatched } from "@odoo/owl";
import { Mutex } from "@web/core/utils/concurrency";
import {SaveToOrderQtyTrigger} from '@gulfco_demand_planning/components/SaveToOrderQtyTrigger';

console.log('SaveToOrderQtyTrigger',SaveToOrderQtyTrigger)

export const SCALE_WEIGHTS = {
    day: 0,
    week: 1,
    month: 2,
    year: 3,
};

export default class DemandPlanningLineComponent extends Component {
    static template = "gulfco_demand_planning.DemandPlanningLineComponent";
    static components = {
        CheckBox,
        SaveToOrderQtyTrigger,
    };
    static props = ["data", "groups"];

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.model = this.env.model;
        this.forecastRow = useRef("forecastRow");
        this.replenishRow = useRef("replenishRow");
        this.mutex = new Mutex();
        onPatched(() => {
            // after a replenishment, switch to next column if possible
//            const previousEl = this.replenishRow.el.getElementsByClassName('o_mrp_mps_hover')[0];
//            if (previousEl) {
//                previousEl.classList.remove('o_mrp_mps_hover');
//                const el = this.replenishRow.el.getElementsByClassName('o_mrp_mps_forced_replenish')[0];
//                if (el) {
//                    el.classList.add('o_mrp_mps_hover');
//                }
//            }
        });

        useBus(this.model, 'mouse-over', () => this._onMouseOverReplenish());
        useBus(this.model, 'mouse-out', () => this._onMouseOutReplenish());
    }

    get demandPlanning() {
        return this.props.data;
    }

    get groups() {
        return this.props.groups;
    }

    get isSelected() {
        return this.model.selectedRecords.has(this.demandPlanning.id);
    }

    get forecastToReplenish() {
        return this.props.data.forecast_ids.find(forecast => forecast.replenish_qty > 0)  && this.props.data.replenish_trigger !== 'never' && this.model.data.demand_planning_period === this.model.data.default_period;
    }

    get isReadonly() {
        return SCALE_WEIGHTS[this.model.data.demand_planning_period] > SCALE_WEIGHTS[this.model.data.default_period];
    }

    formatFloat(value) {
        const precision = (value % 1) ? this.demandPlanning.precision_digits : 0;
        if (isNaN(value))
        {
            return 0.0
        }
        else
        {
           return formatFloat(value, { digits: [false, precision] });
        }

    }

     _onChangeRegularSales(ev, demandPlanningId) {
        const dateIndex = parseInt(ev.target.dataset.date_index);
        const regular_sales_qty = ev.target.value;
        if (regular_sales_qty === "" || isNaN(regular_sales_qty)) {
            ev.target.value = this.model._getOriginValue(demandPlanningId, dateIndex, 'regular_sales_qty');
        } else {
            debugger;
            this.model._saveToRegularSales(demandPlanningId, dateIndex, regular_sales_qty).then(() => {
//                const inputSelector = 'input[data-date_index="' + (dateIndex + 1) + '"]';
//                const nextInput = this.replenishRow.el.querySelector(inputSelector);
//                if (nextInput) {
//                    nextInput.select();
//                }
            }, () => {
                ev.target.value = this.model._getOriginValue(demandPlanningId, dateIndex, 'regular_sales_qty');
            });
        }
    }

    _onChangePromotionSales(ev, demandPlanningId) {
        const dateIndex = parseInt(ev.target.dataset.date_index);
        const promotion_sales_qty = ev.target.value;
        if (promotion_sales_qty === "" || isNaN(promotion_sales_qty)) {
            ev.target.value = this.model._getOriginValue(demandPlanningId, dateIndex, 'promotion_sales_qty');
        } else {
            debugger;
            this.model._saveToPromoSales(demandPlanningId, dateIndex, promotion_sales_qty).then(() => {
            }, () => {
                ev.target.value = this.model._getOriginValue(demandPlanningId, dateIndex, 'promotion_sales_qty');
            });
        }
    }

    _onChangeToOrder(ev, demandPlanningId) {
        const dateIndex = parseInt(ev.target.dataset.date_index);
        const to_order_qty = ev.target.value;
        if (to_order_qty === "" || isNaN(to_order_qty)) {
            ev.target.value = this.model._getOriginValue(demandPlanningId, dateIndex, 'to_order_qty');
        } else {
            debugger;
            this.model._saveToOrderQTY(demandPlanningId, dateIndex, to_order_qty).then(() => {
            }, () => {
                ev.target.value = this.model._getOriginValue(demandPlanningId, dateIndex, 'to_order_qty');
            });
        }
    }
    set_actual_to_order_qty(demand_planning_id,to_order_qty,date_index){
        debugger;
        this.model._saveActualToOrderQTY(demand_planning_id, date_index, to_order_qty)
    }

    /**
     * Handles the click on replenish button. It will call action_replenish with
     * all the Ids present in the view.
     * @private
     * @param {Integer} id mrp.production.schedule Id.
     */
    _onClickReplenish(id) {
        this.model._actionReplenish([id]);
    }

    /**
     * Handles the click on product name. It will open the product form view
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRecordLink(ev) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: ev.currentTarget.dataset.model,
            res_id: Number(ev.currentTarget.dataset.resId),
            views: [[false, 'form']],
            target: 'current',
        });
    }

    _onClickEdit(ev, id) {
        this.model._editProduct(id);
    }

    async _onClickForecastReport() {
        const action = await this.orm.call(
            "product.product",
            "action_product_forecast_report",
            [[this.demandPlanning.id]],
        );
        action.context = {
            active_model: "product.product",
            active_id: this.demandPlanning.product_id[0],
            warehouse_id: this.demandPlanning.warehouse_id && this.demandPlanning.warehouse_id[0],
        };
        return this.actionService.doAction(action);
    }


    _onFocusInput(ev) {
        ev.target.select();
    }

    _onMouseOverReplenish(ev) {
        const className = ev ? 'o_mrp_mps_forced_replenish' : 'o_mrp_mps_to_replenish';
//        const elems = this.replenishRow.el.getElementsByClassName(className);
//        if (elems) {
//            for (const el of elems) {
//                el.classList.add('o_mrp_mps_hover');
//            }
//        }
    }

    _onMouseOutReplenish(ev) {
//        const elems = this.replenishRow.el.getElementsByClassName('o_mrp_mps_hover');
//        while (elems.length > 0) {
//            elems[0].classList.remove('o_mrp_mps_hover');
//        }
    }

    toggleSelection(ev, demandPlanningId) {
        this.model.toggleRecordSelection(demandPlanningId);
    }

}
