{
    "name": "Purchase Demand Planning",
    "version": "18.0.0.0.1",
    "category": "MRP",
    "website": "https://www.plennix.com/",
    "author": "Plennix",
    "depends": ["mrp_mps", "purchase", "gulfco_product_customized_data", "asn_request", "purchase_request","gulfco_vendor_customized_data"],
    "data": [
        "security/ir.model.access.csv",
        "data/order_analysis_sequence.xml",
        "data/order_analysis_server_actions.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/product_supplieinfo_view.xml",
        "views/stock_location_views.xml",
        "views/demand_plannings_views.xml",
        "views/purchase_request_view.xml",
        # "views/demand_planning_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'gulfco_demand_planning/static/src/components/SaveToOrderQtyTrigger.js',
            'gulfco_demand_planning/static/src/components/SaveToOrderQtyTrigger.xml',
            'gulfco_demand_planning/static/src/**/*',
        ],
    },
    "installable": True,

}
