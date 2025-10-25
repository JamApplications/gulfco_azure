# Copyright (C) 2022 - OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID


def _pre_init_hook(env):
    """Drop Odoo's default unique constraint on (barcode, company_id)"""
    print("\n\n ----Pre init hook---------------\n")
    env.cr.execute("""ALTER TABLE stock_location DROP CONSTRAINT IF EXISTS stock_location_barcode_company_uniq;""")
    env.cr.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'stock_location_barcode_company_uniq'
            ) THEN
                ALTER TABLE stock_location DROP CONSTRAINT stock_location_barcode_company_uniq;
            END IF;
        END
        $$;
    """)
