/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Mutex } from "@web/core/utils/concurrency";
import { EventBus } from "@odoo/owl";

export class DemandPlanningModel extends EventBus {
    constructor(params, services) {
        super();
        this.domain = [];
        this.offset = 0;
        this.limit = false;
        this.params = params;
        this.orm = services.orm;
        this.action = services.action;
        this.dialog = services.dialog;
        this.selectedRecords = new Set();
        this.mutex = new Mutex();
    }

    async load(domain, offset, limit, scale) {
        if (domain !== undefined) {
            this.domain = domain;
        }
        if (offset !== undefined) {
            this.offset = offset;
        }
        if (limit !== undefined) {
            this.limit = limit;
        }
        if (scale !== undefined) {
            this.scale = scale;
        }
        this.data = await this.orm.call('demand.planning', 'get_demand_planning_view_state', [this.domain, this.offset, this.limit, this.scale]);
        this.notify();
    }

    async reload(demandPlanningId) {
        return this.orm.call(
                'demand.planning',
                'get_demand_plannings_view_state',
                [demandPlanningId, this.scale],
            ).then((demand_planning_ids) => {
            for (var i = 0; i < demand_planning_ids.length; i++) {
                const index = this.data.demand_planning_ids.findIndex(ps => ps.id === demand_planning_ids[i].id);
                if (index >= 0) {
                    this.data.demand_planning_ids.splice(index, 1, demand_planning_ids[i]);
                } else {
                    this.data.demand_planning_ids.push(demand_planning_ids[i]);
                }
            }
            this.notify();
        });
    }

    notify() {
        this.unselectAll();
        this.trigger('update');
    }



    /**
     * Open the mrp.production.schedule form view in order to create the record.
     * Once the record is created get its state and render it.
     * @private
     * @return {Promise}
     */
    _createProduct() {
        this.mutex.exec(() => {
            this.action.doAction('gulfco_demand_planning.action_demand_planning_view', {
                onClose: () => this.load(),
            });
        });
    }

    _editProduct(demandPlanningId) {
        this.mutex.exec(() => {
            this.action.doAction({
                name: 'Edit Demand Planning',
                type: 'ir.actions.act_window',
                res_model: 'demand.planning',
                views: [[false, 'form']],
                target: 'new',
                res_id: demandPlanningId,
            }, {
                onClose: () => this.reload(demandPlanningId),
            });
        });
    }

    _unlinkProduct(demandPlanningIds) {
        function doIt() {
            this.mutex.exec(async () => {
                return Promise.all(demandPlanningIds.map((id) => this.orm.unlink(
                    'demand.planning',
                    [id]
                ))).then(() => {
                    for (const demandPlanningId of demandPlanningIds) {
                        const index = this.data.demand_planning_ids.findIndex(ps => ps.id === demandPlanningId);
                        this.data.demand_planning_ids.splice(index, 1);
                    }
                    this.notify();
                });
            });
        }
        const body = demandPlanningIds.length > 1
            ? _t("Are you sure you want to delete these records?")
            : _t("Are you sure you want to delete this record?");
        this.dialog.add(ConfirmationDialog, {
            body: body,
            title: _t("Confirmation"),
            confirm: doIt.bind(this),
        });
    }

    unlinkSelectedRecord() {
        return this._unlinkProduct(Array.from(this.selectedRecords));
    }

    _actionOpenDetails(demandPlanningId, action, dateStr, dateStart, dateStop) {
        this.mutex.exec(() => {
            return this.orm.call(
                'demand.planning',
                action,
                [demandPlanningId, dateStr, dateStart, dateStop]
            ).then((action) => {
                return this.action.doAction(action);
            });
        });
    }

    _saveCompanySettings(values) {
        this.mutex.exec(() => {
            this.orm.call(
                'res.company',
                'save_company_settings',
                [this.data.company_id, values],
            ).then(() => {
                this.load();
            });
        });
    }

    mouseOverReplenish() {
        this.trigger('mouse-over');
    }

    mouseOutReplenish() {
        this.trigger('mouse-out');
    }

    selectAll() {
        this.data.demand_planning_ids.map(
            ({ id }) => this.selectedRecords.add(id)
        );
    }

    unselectAll() {
        this.selectedRecords.clear();
    }

   _getOriginValue(demandPlanningId, dateIndex, inputName) {
        return this.data.demand_planning_ids.find(ps => ps.id === demandPlanningId).demand_planning_line_ids[dateIndex][inputName];
    }

    _saveToRegularSales(demandPlanningId, dateIndex, regular_sales_qty) {
        return this.mutex.exec(() => {
            this.orm.call(
                'demand.planning',
                'set_demandPlanningId',
                [demandPlanningId, dateIndex, regular_sales_qty, this.scale],
            ).then(() => {
                return this.reload(demandPlanningId);
            });
        });
    }

   _saveToPromoSales(demandPlanningId, dateIndex, regular_sales_qty) {
        return this.mutex.exec(() => {
            this.orm.call(
                'demand.planning',
                'set_promo_demandPlanningId',
                [demandPlanningId, dateIndex, regular_sales_qty, this.scale],
            ).then(() => {
                return this.reload(demandPlanningId);
            });
        });
    }

   _saveToOrderQTY(demandPlanningId, dateIndex, regular_sales_qty) {
        return this.mutex.exec(() => {
            this.orm.call(
                'demand.planning',
                'set_to_order_qty_demandPlanningId',
                [demandPlanningId, dateIndex, regular_sales_qty, this.scale],
            ).then(() => {
                return this.reload(demandPlanningId);
            });
        });
    }
    _saveActualToOrderQTY(demandPlanningId, dateIndex, to_order_qty) {
        return this.mutex.exec(() => {
            return this.orm.call(
                'demand.planning',
                'set_actual_to_order',
                [demandPlanningId,to_order_qty,dateIndex,this.scale]
            ).then((action) => {
                return true;
            });
        });
    }

    toggleRecordSelection(demandPlanningId) {
        if (this.selectedRecords.has(demandPlanningId)) {
            this.selectedRecords.delete(demandPlanningId);
        } else {
            this.selectedRecords.add(demandPlanningId);
        }
        this.trigger('update');
    }

    toggleSelection() {
        if (this.selectedRecords.size === this.data.demand_planning_ids.length) {
            this.unselectAll();
        } else {
            this.selectAll();
        }
        this.trigger('update');
    }


}
