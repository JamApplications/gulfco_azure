# -*- coding: utf-8 -*-
#############################################################################
#
#    # Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY # Technologies(<https://www.al-majid.com>).
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

{
    'name': "JAM Purchase IT",
    'version': '18.0',
    'category': "Purchase",
    'summary': """Purchase Workflow Changes""",
    'author': 'JAM',
    'company': 'JAM',
    'depends': ['gulfco_approval_custom'],
    'data': [
        'security/security.xml',
        'views/purchase.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
