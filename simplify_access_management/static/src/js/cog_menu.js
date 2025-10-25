/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { useState } from "@odoo/owl";
import { onMounted } from "@odoo/owl";

patch(CogMenu.prototype, {
    setup() {  
        super.setup();
        this.access = useState({removeSpreadsheet: false}); 
        onMounted(async () => {
            var self = this; 
            if(this?.env?.config?.actionType == "ir.actions.act_window") { 
                await this.orm.call(
                    "access.management",
                    "is_spread_sheet_available",
                    [1, this?.env?.config?.actionType, this?.env?.config?.actionId]
                ).then(function(res){
                    self.access.removeSpreadsheet = res;
                })
            } 
        });
    },
    // async checkAvailbility(){
    //     var self = this; 
    //     if(this?.env?.config?.actionType == "ir.actions.act_window") { 
    //         await this.orm.call(
    //             "access.management",
    //             "is_spread_sheet_available",
    //             [1, this?.env?.config?.actionType, this?.env?.config?.actionId]
    //         ).then(function(res){
    //             self.access.removeSpreadsheet = res;
    //         })
    //     } 
    // }, 
    // async _registryItems() {
    //     this.checkAvailbility();
    //     return super._registryItems();
    // },
    get cogItems() {
        let res = super.cogItems;
        if(this.access.removeSpreadsheet){
            res = res.filter((item) => item.key !== "SpreadsheetCogMenu");
        }
        return res
    }
})