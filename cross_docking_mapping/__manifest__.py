{
    "name": "Cross Docking Mapping",
    "version": "1.0",
    "depends": ["stock","stock_delivery", "base"],
    'author': "Plennix",
    'website': "https://www.plennix.com/",
    "category": "Warehouse",
    "description": "Module to manage cross docking mapping for delivery methods.",
    "data": [
        "security/ir.model.access.csv",
        "views/cross_docking_mapping_views.xml",
    ],
    "installable": True,
    "application": False,
}
