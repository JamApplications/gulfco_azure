import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { registry } from "@web/core/registry";
const formatters = registry.category("formatters");
import { _t } from "@web/core/l10n/translation";

patch(ListRenderer.prototype, {

   getRowClass(record) {
        const classNames = super.getRowClass(record).split(" ");
        if(record._config && record._config.resModel &&record._config.resModel == 'purchase.order.line')
        {
            if(record.data && record.data.is_existing_line)
            {
                classNames.push("readonly_row");
            }
        }
        return classNames.join(" ");
    }
});
