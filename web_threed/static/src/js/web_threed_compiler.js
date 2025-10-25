/* @odoo-module */

import {ViewCompiler} from "@web/views/view_compiler";

export class WebThreeDCompiler extends ViewCompiler {}

WebThreeDCompiler.OWL_DIRECTIVE_WHITELIST = [
    ...ViewCompiler.OWL_DIRECTIVE_WHITELIST,
    "t-name",
    "t-esc",
    "t-out",
    "t-set",
    "t-value",
    "t-if",
    "t-else",
    "t-elif",
    "t-foreach",
    "t-as",
    "t-key",
    "t-att.*",
    "t-call",
    "t-translation",
];
