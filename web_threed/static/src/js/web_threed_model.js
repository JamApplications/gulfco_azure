/** @odoo-module */

/** @typedef {import("./web_threed_arch_parser").ItemFieldsMapping} ItemFieldsMapping */
/** @typedef {import("./web_threed_arch_parser").ArchInfo} ArchInfo */
/**
 *
 * @typedef {Object} GroundArea
 * @property {number} id
 * @property {string} name
 * @property {string} planimetryImage
 * @property {number} sizex
 * @property {number} sizey
 * @property {number} sizez
 * @property {number} [scale]
 *
 */

/**
 * @typedef {Object} Item3d
 * @property {number} id
 * @property {string} name
 * @property {number} sizex
 * @property {number} sizey
 * @property {number} sizez
 * @property {number} positionx
 * @property {number} positiony
 * @property {number} positionz
 * @property {number} rotationx
 * @property {number} rotationy
 * @property {number} rotationz
 * @property {number} areaId
 * @property {string} color
 * @property {string} geometry
 * @property {number} opacity
 * @property {string} gltf
 * @property {number} scaleFactor
 * @property {string} [gltf_load_url]
 */

/**
 * @typedef {Object} Legend
 * @property {string} name
 * @property {string} color
 * @property {number} opacity
 */

import {KeepLast} from "@web/core/utils/concurrency";

export class ThreedModel {
    /**
     * @param {import("@web/core/orm_service").ORM} orm
     * @param {string} resModel
     * @param {import("fields").FieldDefinitionMap} fields
     * @param {import("./web_threed_arch_parser").ArchInfo} archInfo
     * @param {any[]} domain
     * @param {Object<string, Object|Array|number|string|null|boolean>} context
     */
    constructor(orm, resModel, fields, archInfo, domain, context) {
        this.orm = orm;
        /** @type {string} */
        this.resModel = resModel;
        /** @type {ArchInfo} */
        const {
            readFields,
            itemFieldsMapping,
            areaFieldsMapping,
            legendFieldsMapping,
            legendModel,
        } = archInfo;
        /** @type {string} */
        this.legendModel = legendModel;
        /** @type {ArchInfo['legendFieldsMapping']} */
        this.legendFieldsMapping = legendFieldsMapping;
        this.fields = fields;
        /** @type {ArchInfo['readFields']} */
        this.readFields = readFields;
        /** @type {ArchInfo['itemFieldsMapping']} */
        this.itemFieldsMapping = itemFieldsMapping;
        /** @type {ArchInfo['areaFieldsMapping']} */
        this.areaFieldsMapping = areaFieldsMapping;

        const areaField = this.fields[this.itemFieldsMapping.areaField];
        if (
            areaField.type === "many2one" ||
            areaField.type === "many2many" ||
            areaField.type === "one2many"
        ) {
            this.areaModel = areaField.relation;
        } else {
            throw new Error("The area field should be a relational field");
        }
        /** @type {Array} */
        this.domain = domain;
        /** @type {KeepLast} */
        this.keepLast = new KeepLast();
        /** @type {Object} */
        this.context = context;
        /** @type {Item3d[]} */
        this.all3dItems = [];
        /** @type {Item3d[]} */
        this.selected3dItems = [];
        /** @type {Legend[]} */
        this.legendItems = [];
        /** @type {boolean} */
        this.areasLoaded = false;
        /** @type {boolean} */
        this.selectedItems3dLoaded = false;
        /** @type {boolean} */
        this.allItems3dLoaded = false;
        /** @type {boolean} */
        this.legendLoaded = false;
        /** @type {number} */
        this.selectedGroundAreaId = null;
    }

    get withSizeDomain() {
        return [
            [this.itemFieldsMapping.sizexField, ">", 0],
            [this.itemFieldsMapping.sizeyField, ">", 0],
            [this.itemFieldsMapping.sizezField, ">", 0],
        ];
    }

    /**
     * @param {{ [x: string]: any; id: number; }} record
     * @return {Item3d}
     */
    mapRecordToItem3d(record) {
        const item3d = {
            id: record.id,
            name: record[this.itemFieldsMapping.nameField],
            sizex: record[this.itemFieldsMapping.sizexField],
            sizey: record[this.itemFieldsMapping.sizeyField],
            sizez: record[this.itemFieldsMapping.sizezField],
            positionx: record[this.itemFieldsMapping.positionxField],
            positiony: record[this.itemFieldsMapping.positionyField],
            positionz: record[this.itemFieldsMapping.positionzField],
            rotationx: record[this.itemFieldsMapping.rotationxField],
            rotationy: record[this.itemFieldsMapping.rotationyField],
            rotationz: record[this.itemFieldsMapping.rotationzField],
            areaId: record[this.itemFieldsMapping.areaField],
            color: record[this.itemFieldsMapping.colorField],
            geometry: record[this.itemFieldsMapping.geometryField],
            opacity: record[this.itemFieldsMapping.opacityField],
            gltf: record[this.itemFieldsMapping.gltfField],
            scaleFactor: record[this.itemFieldsMapping.scaleFactorField],
        };
        if (item3d.gltf) {
            item3d.gltf_load_url = `/web/content?model=${this.resModel}&id=${item3d.id}&field=${this.itemFieldsMapping.gltfField}`;
        }
        return item3d;
    }

    /**
     * @param {number[]} areaIds
     */
    async _getAreas(areaIds) {
        const {records} = await this.keepLast.add(
            this.orm.webSearchRead(this.areaModel, [["id", "in", areaIds]], {
                specification: {
                    [this.areaFieldsMapping.nameField]: {},
                    [this.areaFieldsMapping.planimetryImageField]: {},
                    [this.areaFieldsMapping.sizexField]: {},
                    [this.areaFieldsMapping.sizeyField]: {},
                    [this.areaFieldsMapping.sizezField]: {},
                },
            })
        );
        /** @type {GroundArea[]} */
        const results = records.map((record) => {
            /** @type {GroundArea} */
            return {
                id: record.id,
                name: record[this.areaFieldsMapping.nameField],
                planimetryImage: record[this.areaFieldsMapping.planimetryImageField],
                sizex: record[this.areaFieldsMapping.sizexField],
                sizey: record[this.areaFieldsMapping.sizeyField],
                sizez: record[this.areaFieldsMapping.sizezField],
                scale: record[this.areaFieldsMapping.sizexField] / 500,
            };
        });
        return results;
    }

    /**
     * @return {Promise<Item3d[]>}
     * @private
     */
    async _getSelectedItems() {
        const {records} = await this.keepLast.add(
            this.orm.webSearchRead(
                this.resModel,
                this.domain.concat(this.withSizeDomain),
                {
                    specification: this.readFields.reduce((acc, curr) => {
                        return {
                            ...acc,
                            [curr]: {},
                        };
                    }, {}),
                    context: this.context,
                }
            )
        );
        /** @type {Item3d[]} */
        const selected3dItems = records.map(
            (/** @type {{ [x: string]: any; id: number; }} */ record) =>
                this.mapRecordToItem3d(record)
        );
        return selected3dItems;
    }

    /**
     * @return {Promise<Item3d[]>}
     *
     * @param {number[]} groundAreaIds
     */
    async _getAllItems(groundAreaIds) {
        /** @type any[] */
        const allItemsForAreaDomain = [
            [this.itemFieldsMapping.areaField, "in", groundAreaIds],
        ];
        const {records} = await this.keepLast.add(
            this.orm.webSearchRead(
                this.resModel,
                allItemsForAreaDomain.concat(this.withSizeDomain),
                {
                    specification: this.readFields.reduce((acc, curr) => {
                        return {
                            ...acc,
                            [curr]: {},
                        };
                    }, {}),
                }
            )
        );
        /** @type {Item3d[]} */
        const all3dItems = records.map(
            (/** @type {{ [x: string]: any; id: number; }} */ record) =>
                this.mapRecordToItem3d(record)
        );
        return all3dItems;
    }

    /**
     * Load the data from Odoo.
     * The load method is called from the Controller
     */
    async load() {
        /** @type {Item3d[]} */
        this.selected3dItems = await this._getSelectedItems();

        /** @type {number[]} */
        const groundAreaIds = [
            ...new Set(
                this.selected3dItems.map((/** @type {Item3d} */ item) => item.areaId)
            ),
        ];

        this.legendLoaded = await this._loadLegend();
        this.groundAreas = await this._getAreas(groundAreaIds);
        this.all3dItems = await this._getAllItems(groundAreaIds);
        this.areasLoaded = true;
        this.allItems3dLoaded = true;
        this.selectedItems3dLoaded = true;
    }

    async update() {
        this.selected3dItems = await this._getSelectedItems();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Load the legend.
     *
     * Legends can be hardcoded inside the context or we can fetch them given a model and
     * a list of field.
     */
    async _loadLegend() {
        if (this.context.force_legend_items) {
            this.legendItems = this.context.force_legend_items;
            return true;
        }
        if (this.legendModel && this.legendModel !== "") {
            const {records} = await this.keepLast.add(
                this.orm.webSearchRead(this.legendModel, [], {
                    specification: {
                        [this.legendFieldsMapping.nameField ?? "name"]: {},
                        [this.legendFieldsMapping.colorField ?? "color"]: {},
                        [this.legendFieldsMapping.opacityField ?? "opacity"]: {},
                    },
                })
            );
            /** @type {Legend[]} */
            const results = records.map(
                (/** @type {{ [x: string]: any; }} */ record) => {
                    /** @type {Legend} */
                    return {
                        name: record[this.legendFieldsMapping.nameField],
                        color: record[this.legendFieldsMapping.colorField],
                        opacity: record[this.legendFieldsMapping.opacityField] ?? 1,
                    };
                }
            );
            this.legendItems = results;
            return true;
        }
        this.legendItems = [];
        return true;
    }
}
