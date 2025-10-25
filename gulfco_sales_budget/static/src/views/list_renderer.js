import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { registry } from "@web/core/registry";
const formatters = registry.category("formatters");
import { _t } from "@web/core/l10n/translation";

patch(ListRenderer.prototype, {

    get aggregates() {
        let values;
        if (this.props.list.selection && this.props.list.selection.length) {
            values = this.props.list.selection.map((r) => r.data);
        } else if (this.props.list.isGrouped) {
            values = this.props.list.groups.map((g) => g.aggregates);
        } else {
            values = this.props.list.records.map((r) => r.data);
        }
        const aggregates = {};
        for (const column of this.allColumns) {
            if (column.type !== "field") {
                continue;
            }
            const fieldName = column.name;
            if (fieldName in this.optionalActiveFields && !this.optionalActiveFields[fieldName]) {
                continue;
            }
            const field = this.fields[fieldName];
//            debugger;
            const fieldValues = values.map((v) => v[fieldName]).filter((v) => v || v === 0);
            if (!fieldValues.length) {
                continue;
            }
            const type = field.type;
            if (type !== "integer" && type !== "float" && type !== "monetary") {
                continue;
            }
            const { attrs, widget } = column;
            const func =
                (attrs.sum_gp && "sum_gp") ||
                (attrs.sum && "sum") ||
                (attrs.avg && "avg") ||
                (attrs.max && "max") ||
                (attrs.min && "min");
            let currencyId;
            if (type === "monetary" || widget === "monetary") {
                const currencyField =
                    column.options.currency_field ||
                    this.fields[fieldName].currency_field ||
                    "currency_id";
                if (!(currencyField in this.props.list.activeFields)) {
                    aggregates[fieldName] = {
                        help: _t("No currency provided"),
                        value: "—",
                    };
                    continue;
                }
                currencyId = values[0][currencyField] && values[0][currencyField][0];
                if (currencyId && func) {
                    const sameCurrency = values.every(
                        (value) => currencyId === value[currencyField][0]
                    );
                    if (!sameCurrency) {
                        aggregates[fieldName] = {
                            help: _t("Different currencies cannot be aggregated"),
                            value: "—",
                        };
                        continue;
                    }
                }
            }
            if (func) {
                let aggregateValue = 0;
                if (func === "max") {
                    aggregateValue = Math.max(-Infinity, ...fieldValues);
                } else if (func === "min") {
                    aggregateValue = Math.min(Infinity, ...fieldValues);
                } else if (func === "avg") {
                    aggregateValue =
                        fieldValues.reduce((acc, val) => acc + val) / fieldValues.length;
                } else if (func === "sum") {
                     if(this.props.list._config.resModel == 'sales.budget.line' && field.name.split('_').includes('gp'))
                     {
                            var name = field.name.split('_')[0]
                            const gross_margin_field_name = name + '_gross_margin'
                            const sales_value_field_name = name + '_sales_value'
                            const GmfieldValues = values.map((v) => v[gross_margin_field_name]).filter((v) => v || v === 0);
                            const SVfieldValues = values.map((v) => v[sales_value_field_name]).filter((v) => v || v === 0);
                            const GmaggregateValue = GmfieldValues.reduce((acc, val) => acc + val);
                            const SVaggregateValue = SVfieldValues.reduce((acc, val) => acc + val);
                            aggregateValue = (GmaggregateValue / SVaggregateValue ) * 100;
                     }
                     else
                     {
                       aggregateValue = fieldValues.reduce((acc, val) => acc + val);
                     }
                 }
//                }else if (func === "sum_gp") {
//                    var name = field.name.split('_')[0]
//                    const gross_margin_field_name = name + '_gross_margin'
//                    const sales_value_field_name = name + '_sales_value'
//                    const GmfieldValues = values.map((v) => v[gross_margin_field_name]).filter((v) => v || v === 0);
//                    const SVfieldValues = values.map((v) => v[sales_value_field_name]).filter((v) => v || v === 0);
//                    const GmaggregateValue = GmfieldValues.reduce((acc, val) => acc + val);
//                    const SVaggregateValue = SVfieldValues.reduce((acc, val) => acc + val);
//                    aggregateValue = (GmaggregateValue / SVaggregateValue ) * 100;
//                    console.log('----GmaggregateValue------------',GmaggregateValue);
//                    console.log('---------SVaggregateValue-------',SVaggregateValue)
//                    console.log('------------aggregateValue----',aggregateValue)
//                }

                const formatter = formatters.get(widget, false) || formatters.get(type, false);
                const formatOptions = {
                    digits: attrs.digits ? JSON.parse(attrs.digits) : undefined,
                    escape: true,
                };
                if (currencyId) {
                    formatOptions.currencyId = currencyId;
                }
                aggregates[fieldName] = {
                    help: attrs[func],
                    value: formatter ? formatter(aggregateValue, formatOptions) : aggregateValue,
                };
            }
        }
        return aggregates;
    }
});
