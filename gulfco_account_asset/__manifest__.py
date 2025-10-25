# -*- coding: utf-8 -*-
#############################################################################
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'GULFCO Asset Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Manage Company Fixed Assets',
    'description': """This module facilitates the creation and management of 
     fixed assets base on GULFCO requirments """,
    'author': "Elhamari",
    'company': 'JAMIT',
    'maintainer': 'JAMIT',
    'depends': ['account_asset'],
    'data': [
        #'security/hr_loan_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/res_config_settings_view.xml',
        'views/account_move_views.xml',
        'views/account_asset_transfer_views.xml',
        'wizard/asset_modify_views.xml',
        'wizard/asset_dispose_views.xml',
        'wizard/asset_freeze_views.xml',
        'views/account_asset_views.xml',
        'views/purchase_order_views.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
