/** @odoo-module **/
import {_t} from "@web/core/l10n/translation";
import {useRef, useState, onWillStart, Component} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {imageUrl} from "@web/core/utils/urls";
import {FileUploader} from "@web/views/fields/file_handler";
import {url} from "@web/core/utils/urls";
import {isBinarySize} from "@web/core/utils/binary";
import {loadJSModule} from "./assets";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {useService} from "@web/core/utils/hooks";

const placeholder = "/web_widget_model_viewer_18/static/glb/placeholder.glb";

export class ModelViewerField extends Component {
    static template = "web_widget_model_viewer_18.ModelViewerField";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardFieldProps,
        previewImage: {type: String, optional: true},
        acceptedFileExtensions: {type: String, optional: true},
        width: {type: Number, optional: true},
        height: {type: Number, optional: true},
        reload: {type: Boolean, optional: true},
        style: {type: String, optional: true},
    };
    static defaultProps = {
        acceptedFileExtensions: "model/gltf-binary",
        reload: true,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.modelViewerRef = useRef("modelViewer");
        this.windowState = useState({
            isFullscreen: false,
            jsLibLoaded: false,
        });
        this.state = useState({
            isValid: true,
        });
        onWillStart(async () => {
            if (!this.windowState.jsLibLoaded) {
                await loadJSModule(
                    "https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js"
                );
                this.windowState.jsLibLoaded = true;
            }
        });
    }

    get rawCacheKey() {
        return this.props.record.data.write_date;
    }

    get fieldType() {
        return this.props.record.fields[this.props.name].type;
    }

    /**
     * @param {string} imageFieldName
     */
    getUrl(imageFieldName) {
        if (!this.props.reload && this.lastURL) {
            return this.lastURL;
        }
        if (!this.props.record.data[this.props.name] || !this.state.isValid) {
            return placeholder;
        }
        if (this.fieldType === "many2one") {
            this.lastURL = imageUrl(
                this.props.record.fields[this.props.name].relation,
                this.props.record.data[this.props.name][0],
                imageFieldName
            );
        } else if (isBinarySize(this.props.record.data[this.props.name])) {
            this.lastURL = imageUrl(
                this.props.record.resModel,
                this.props.record.resId,
                imageFieldName,
                {unique: this.rawCacheKey}
            );
        } else {
            this.lastURL = `data:model/gltf-binary;base64,${
                this.props.record.data[this.props.name]
            }`;
        }
        return this.lastURL;
    }

    onFileRemove() {
        this.state.isValid = true;
        this.props.record.update({[this.props.name]: false});
    }

    onFileUploaded(info) {
        this.state.isValid = true;
        this.props.record.update({[this.props.name]: info.data});
    }

    /**
     * @param {Event} ev
     */
    fullscreen(ev) {
        const isFullscreenAvailable = document.fullscreenEnabled || false;
        var modelViewerElem = this.modelViewerRef.el;
        if (isFullscreenAvailable) {
            var fullscreenElement = document.fullscreenElement;
            if (fullscreenElement) {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                    this.windowState.isFullscreen = false;
                }
            } else {
                modelViewerElem.requestFullscreen();
                this.windowState.isFullscreen = true;
            }
        } else {
            console.error("ERROR : full screen not supported by web browser");
        }
    }

    get style() {
        let style = this.props.style || "";
        if (this.props.width) {
            style += `max-width: ${this.props.width}px;`;
        }
        if (this.props.height) {
            style += `max-height: ${this.props.height}px;`;
        }
        console.log("style", style);
        return style;
    }
}

export const modelViewerField = {
    component: ModelViewerField,
    displayName: _t("3D Model Viewer"),
    supportedOptions: [
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
    ],
    supportedTypes: ["binary"],
    fieldDependencies: [{name: "write_date", type: "datetime"}],
    isEmpty: () => false,
    extractProps: ({attrs, options}) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        width: options.size && Boolean(options.size[0]) ? options.size[0] : attrs.width,
        height:
            options.size && Boolean(options.size[1]) ? options.size[1] : attrs.height,
        style: attrs.style ?? "",
    }),
};

registry.category("fields").add("model_viewer", modelViewerField);
