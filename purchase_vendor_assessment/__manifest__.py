# -*- coding: utf-8 -*-
{
    "name": "Purchase Vendor Assessment",
    "version": "18.1",
    "category": "Purchases",
    "description": """
Odoo purchase: compute the vendor assessment
    """,
    "summary": """
Odoo purchase: compute the vendor assessment
    """,
    "live_test_url": "https://demo15.domiup.com",
    "author": "Domiup",
    "price": 50,
    "currency": "EUR",
    "license": "OPL-1",
    "support": "domiup.contact@gmail.com",
    "website": "",
    "depends": [
        "purchase", "quality_control"
    ],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/ir.rule.xml",
        "data/assessment_criteria.xml",
        # "data/assessment_purchase_result.xml",
        # "data/assessment_purchase_template.xml",
        # "data/assessment_vendor_result.xml",
        "views/assessment_criteria.xml",
        "views/assessment_criteria_group.xml",
        # "views/assessment_purchase_result.xml",
        # "views/assessment_purchase_template.xml",
        "views/assessment_purchase.xml",
        "views/assessment_vendor_result.xml",
        "views/assessment_vendor.xml",
        "views/purchase_order.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner.xml",
        "wizards/assessment_refuse_reason.xml",
        "views/menu.xml",
    ],
    "demo": [],
    "assets": {
    },
    "test": [],
    "images": ["static/description/banner.png"],
    "installable": True,
    "active": False,
    "application": True,
}
