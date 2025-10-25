from odoo import models, api
from odoo.exceptions import UserError

class AccountReport(models.Model):
    _inherit = 'account.report'
    def _report_custom_engine_compute_generic_vat_code_column(self, line_info, *args, **kwargs):
        codes = [
            "SR_Slocal_G_ABU", "SR_Dubai_G", "SR_BASE_SH_G", "SR_BASE_AJ_G", "SR_Base_G_UM", "SR_BASE_RAS_G", "SR_BASE_FJ_G",
            "SR_Slocal-G_abu1", "SR_Slocal-G_dubai_VAT", "SR_Slocal_VAT_S_G", "SR_VAT_G_AJ", "SR_VAT_G_UM", "SR_VAT_RAS_G",
            "SR_VAT_FJ_G", "SR_BASE_S_ABU", "SR_BASE_S_DUB", "SR_SH_BASE_S", "SR_BASE_AJ_S", "SR_UM_BASE_S", "SR_BASE_RAS_S",
            "SR_BASE_FJ_S", "SR_VAT_S_ABU", "SR_DUB_S_VAT", "SR_VAT_SH_S", "SR_VAT_AJ_S", "SR_VAT_UM_S", "SR_VAT_RAS_S",
            "SR_VAT_FJ_S", "SR_ABU_DM_BASE", "SR_BASE_DUB_DM", "SR_BASE_SH_DM", "SR_BASE_AJ_DM", "SR_BASE_UM_DM",
            "SR_BASE_RAS_DM", "SR_BASE_FJ_DM", "SR_VAT_ABU_DM", "SR_VAT_DUB_DM", "SR_VAT_SH_DM", "SR_VAT_AJ_DM",
            "SR_VAT_UM_DM", "SR_VAT_RAS_DM", "SR_VAT_FJ_DM", "TR", "TR_VAT", "RV_RCM", "RV_VAT_RCM", "ZERO_RATE_BASE_SA",
            "FZGCC_SA", "EX_G_SA", "EX_S_SA", "EXAMPT_SUPP_BASE_1", "REV_BASE_11", "REV_G_VAT", "GOODS_IMPORTED_BASE",
            "VAT_G_IMP", "CASHRMIT_BASE", "CARDRIMT_BASE", "INTERDIV_BASE", "INTERVAT_BASE", "ROTW_BASE", "POSBC_BASE",
            "FZON_BASE", "SA_LOC_BASE", "ORC_BASE", "FRZINTER_BASE", "SAREST_BASE", "SA_FRZ_BASE", "CASHRMIT_VAT_SA",
            "CRDRIMIT_VAT", "INTERDIV_VAT", "INTERVAT_VAT", "ROTW_VAT", "POSBC_VAT", "FZON_VAT", "SA_LOC_VAT", "ORC_VAT",
            "FRZINTER_VAT", "SAREDT_VAT", "SA_FRZ_VAT", "PUR_LOC_G_BASE", "PUR_LOC_S_BASE", "PUR_SS_BASE", "ORC_LOC_BASE",
            "PUR_TRD_TRX_BASE", "PUR_LOC_VAT_G", "PUR_LOC_VAT_S", "PUR_SS_VAT", "ORC_VAT_TRANS", "PUR_TRADE_VAT",
            "NON_DED_BASE", "NON_DED_BASE_OTH", "NON_DED_VAT", "NON_DED_VAT_OTH", "RES_BASE", "RECV_VAT", "REV_BASE",
            "REV_VAT", "GOOD_IMP_BASE", "GOODS_IMP_VAT", "PUR_ZER_BASE", "PUR_ZERO_VAT", "VAT_PUR_ZER", "EX_LOC_BASE",
            "EX_LOC_TAX", "PUR_OS_INTERDIV", "PUR_OS_RELATEDGM", "OS_FZML", "OS_LUR", "PUR_OS_FREIGHT", "PUR_OS_EMPPAY",
            "OS_PFZ_BASE", "PUR_OS_PRW_BASE", "PUR_OS_GOVT_BASE", "OS_Interdiv_VAT", "PUR_OS_RELATEDGM_VAT", "OS_FZML_VAT",
            "OS-LUR_VAT", "PUR_OS_FREIGHT_VAT", "PUR_OS_EMPPAY_VAT", "OS_PFZ_VAT", "PUR_OS_PRW_VAT", "PUR_OS_GOVT_VAT"
        ]
        mapping_formula ={}
        for code in codes:
            report_line_id = self.env['account.report.line'].search([('code','=',code)])
            balace_exprssion_formula = report_line_id.expression_ids.filtered(lambda exp:exp.label == 'balance').formula
            tag_names = [f"+{balace_exprssion_formula}", f"-{balace_exprssion_formula}"]
            tags = self.env['account.account.tag'].search([('name', 'in', tag_names)])
            taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
            ])
            vat_codes = list(set(taxes.mapped('vat_code')))
            nutralized_code = code.replace("-","_").lower()
            mapping_formula[nutralized_code]=', '.join(vat_codes)
        return mapping_formula

    def _report_custom_engine_compute_vat_code_column(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code': ', '.join(vat_codes) if vat_codes else ''}

    def _report_custom_engine_compute_vat_code_column_dubai(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code_dubai': ', '.join(vat_codes) if vat_codes else ''}

    def _report_custom_engine_compute_vat_code_column_sharjah(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code_sharjah': ', '.join(vat_codes) if vat_codes else ''}

    def _report_custom_engine_compute_vat_code_column_ajman(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code_ajman': ', '.join(vat_codes) if vat_codes else ''}

    def _report_custom_engine_compute_vat_code_column_umm_al_quwain(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code_umm_al_quwain': ', '.join(vat_codes) if vat_codes else ''}

    def _report_custom_engine_compute_vat_code_column_fujairah(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code_fujairah': ', '.join(vat_codes) if vat_codes else ''}

    def _report_custom_engine_compute_vat_code_column_ras_al_khaima(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code_ras_al_khaima': ', '.join(vat_codes) if vat_codes else ''}

    def _report_custom_engine_compute_vat_code_column_refunds(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code_refund': ', '.join(vat_codes) if vat_codes else ''}

    def _report_custom_engine_compute_vat_code_column_charge_provision(self, line_info, *args, **kwargs):
        formula = ''
        if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
            expressions = line_info.report_line_id.expression_ids
            if expressions:
                formula = expressions[0].formula or ''

        if not formula:
            return {'vat_code': ''}

        # Search for all tax tags with name matching formula (case-insensitive)
        tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])

        if not tags:
            return {'vat_code': ''}

        # Search for taxes whose repartition lines have these tags
        taxes = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
            ('vat_code', '!=', False),
        ])

        vat_codes = taxes.mapped('vat_code')
        vat_codes = list(set(vat_codes))

        return {'vat_code_charge_provision': ', '.join(vat_codes) if vat_codes else ''}


#     def _report_custom_engine_compute_vat_code_column(self, line_info, *args, **kwargs):
#         formula = ''
#         if hasattr(line_info, 'report_line_id') and line_info.report_line_id.exists():
#             expressions = line_info.report_line_id.expression_ids.filtered(lambda e: e.label == 'balance')
#             if expressions:
#                 formula = expressions[0].formula or ''

#         if not formula:
#             return {'vat_code': ''}
#         raise UserError(str(expressions.read()))
#         tags = self.env['account.account.tag'].search([('name', 'ilike', formula)])
#         if not tags:
#             return {'vat_code': ''}

#         taxes = self.env['account.tax'].search([
#             '|',
#             ('invoice_repartition_line_ids.tag_ids', 'in', tags.ids),
#             ('refund_repartition_line_ids.tag_ids', 'in', tags.ids),
#             ('vat_code', '!=', False),
#         ])

#         vat_codes = taxes.mapped('vat_code')
#         vat_codes = sorted(set(vat_codes))  # unique and sorted

#         # Option 1: Return first VAT code only
#         # vat_code_str = vat_codes[0] if vat_codes else ''

#         # Option 2: Return all VAT codes separated by commas
#         vat_code_str = ', '.join(vat_codes) if vat_codes else ''

#         return {'vat_code': vat_code_str, 'new_vat': "ali khan"}


# [
#     {
#         'id': 160,
#         'report_line_id': (
#             73,
#             'a. Abu Dhabi'
#         ),
#         'report_line_name': 'a. Abu Dhabi',
#         'label': 'balance',
#         'engine': 'tax_tags',
#         'formula': 'a. Abu Dhabi (Base)',
#         'subformula': False,
#         'date_scope': 'strict_range',
#         'figure_type': False,
#         'green_on_positive': True,
#         'blank_if_zero': False,
#         'auditable': True,
#         'carryover_target': False,
#         'display_name': 'a. Abu Dhabi [balance]',
#         'create_uid': (
#             1,
#             'OdooBot'
#         ),
#         'create_date': datetime.datetime(
#             2025,
#             1,
#             15,
#             12,
#             9,
#             36,
#             861635
#         ),
#         'write_uid': (
#             2,
#             'Administrator'
#         ),
#         'write_date': datetime.datetime(
#             2025,
#             5,
#             30,
#             6,
#             14,
#             9,
#             380260
#         )
#     },
#     {
#         'id': 161,
#         'report_line_id': (
#             74,
#             'b. Dubai'
#         ),
#         'report_line_name': 'b. Dubai',
#         'label': 'balance',
#         'engine': 'tax_tags',
#         'formula': 'b. Dubai (Base)',
#         'subformula': False,
#         'date_scope': 'strict_range',
#         'figure_type': False,
#         'green_on_positive': True,
#         'blank_if_zero': False,
#         'auditable': True,
#         'carryover_target': False,
#         'display_name': 'b. Dubai [balance]',
#         'create_uid': (
#             1,
#             'OdooBot'
#         ),
#         'create_date': datetime.datetime(
#             2025,
#             1,
#             15,
#             12,
#             9,
#             36,
#             861635
#         ),
#         'write_uid': (
#             1,
#             'OdooBot'
#         ),
#         'write_date': datetime.datetime(
#             2025,
#             5,
#             29,
#             10,
#             13,
#             29,
#             484276
#         )
#     },
#     {
#         'id': 162,
#         'report_line_id': (
#             75,
#             'c. Sharjah'
#         ),
#         'report_line_name': 'c. Sharjah',
#         'label': 'balance',
#         'engine': 'tax_tags',
#         'formula': 'c. Sharjah (Base)',
#         'subformula': False,
#         'date_scope': 'strict_range',
#         'figure_type': False,
#         'green_on_positive': True,
#         'blank_if_zero': False,
#         'auditable': True,
#         'carryover_target': False,
#         'display_name': 'c. Sharjah [balance]',
#         'create_uid': (
#             1,
#             'OdooBot'
#         ),
#         'create_date': datetime.datetime(
#             2025,
#             1,
#             15,
#             12,
#             9,
#             36,
#             861635
#         ),
#         'write_uid': (
#             1,
#             'OdooBot'
#         ),
#         'write_date': datetime.datetime(
#             2025,
#             5,
#             29,
#             10,
#             13,
#             29,
#             484276
#         )
#     },
#     {
#         'id': 163,
#         'report_line_id': (
#             76,
#             'd. Ajman'
#         ),
#         'report_line_name': 'd. Ajman',
#         'label': 'balance',
#         'engine': 'tax_tags',
#         'formula': 'd. Ajman (Base)',
#         'subformula': False,
#         'date_scope': 'strict_range',
#         'figure_type': False,
#         'green_on_positive': True,
#         'blank_if_zero': False,
#         'auditable': True,
#         'carryover_target': False,
#         'display_name': 'd. Ajman [balance]',
#         'create_uid': (
#             1,
#             'OdooBot'
#         ),
#         'create_date': datetime.datetime(
#             2025,
#             1,
#             15,
#             12,
#             9,
#             36,
#             861635
#         ),
#         'write_uid': (
#             1,
#             'OdooBot'
#         ),
#         'write_date': datetime.datetime(
#             2025,
#             5,
#             29,
#             10,
#             13,
#             29,
#             484276
#         )
#     }
# ]
