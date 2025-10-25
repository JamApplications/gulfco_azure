/** @odoo-module **/

import { registry } from "@web/core/registry";
//import { FloatField, IntegerField } from "@web/views/fields/fields";
import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { _t } from "@web/core/l10n/translation";
import { monetaryField, MonetaryField } from "@web/views/fields/monetary/monetary_field";
import { WarningDialog } from "@web/core/errors/error_dialogs";


patch(FloatField.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialog = useService('dialog');
    },
     parse(value) {
        if(this.props.record && this.props.record.model && this.props.record.model.config && this.props.record.model.config.resModel && ['product.template','product.product'].includes(this.props.record.model.config.resModel))
            {
                if (value < 0) {
                      this.dialog.add(WarningDialog, {
                            title: _t("Warning"),
                            message: _t("%s negative value is not valid", this.props.name),
                        });
//                    this.notification.add(
//                        _t("%s negative value is not valid", this.props.name),
//                        { type: "danger" }
//                    );
                    this.props.update({ [this.props.name]: null });
                }
            }
        return super.parse(value);
    }
});

patch(IntegerField.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");  // <-- use notification service
        this.dialog = useService('dialog');
    },
    get formattedValue()
    {
        if(this.props.record && this.props.record.model && this.props.record.model.config && this.props.record.model.config.resModel && ['product.template','product.product'].includes(this.props.record.model.config.resModel))
            {
                if (this.value < 0) {
                   this.dialog.add(WarningDialog, {
                        title: _t("Warning"),
                        message: _t("%s negative value is not valid", this.props.name),
                    });
                   this.props.record.update({ [this.props.name]: 0 });
                }
            }
        return super.formattedValue;

    },
});

patch(MonetaryField.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");  // <-- use notification service
        this.dialog = useService('dialog');
    },
     onInput(ev) {
        if(this.props.record && this.props.record.model && this.props.record.model.config && this.props.record.model.config.resModel && ['product.template','product.product'].includes(this.props.record.model.config.resModel))
            {
                if (ev.target.value < 0) {
                     this.dialog.add(WarningDialog, {
                        title: _t("Warning"),
                        message: _t("%s negative value is not valid", this.props.name),
                    });
//                    this.notification.add(
//                        _t("%s negative value is not valid", this.props.name),
//                        { type: "danger" }
//                    );
                    ev.target.value = 0.0
//                    this.props.record.update({ [this.props.name]: 0.0 });
                }
            }
        super.onInput(...arguments);
    },
});

