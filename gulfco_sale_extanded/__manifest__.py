
{
    "name": "Gulfco Sale Extended",
    "version": "3.2",
    'author': "Plennix",
    'website': "https://www.plennix.com/",
    "category": "Sales",
    "description": "Extends the Sale Order with custom Gulfco fields",
    "depends": ["sale_loyalty", "gulfco_product_customized_data","gulfco_customer_customized_data", "base","plnx_gulfco_sales_commission", "sales_team", "product", "account","stock_gl_account","gulfco_contact_registration_custom"],
    # total sale line field depends
    # "depends": ['gulfco_customer_customized_data','plnx_sales_team', 'sale', 'sale_stock', 'sales_team', 'sale_timesheet', 'sale_loyalty', 'sale_service', 'delivery', 'product', 'sale_purchase', 'sale_project', 'sale_management', 'sale_pdf_quote_builder', 'industry_fsm_stock', 'industry_fsm_sale', 'pos_sale', 'base', 'gulfco_product_customized_data', 'gulfco_sale_extanded'],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "data/ir_cron.xml",
        "report/tax_invoice_4_inch_report.xml",
        "views/sale_order_view.xml",
        "views/product.xml",
        "views/sale_order_report_template.xml",
        "views/account_move_view.xml",
        "views/customer_specification_views.xml",
        "views/res_partner.xml",
        "views/stock_package_type.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False
}
