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
    'name': 'GULFCO PDC Customization',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'PDC Management',
    'description': """The user can manage PDC in the system""",
    'author': "Elhamari",
    'company': 'JAMIT',
    'maintainer': 'JAMIT',
    'depends': ['account_pdc'],
    'data': [
        'data/ir_cron.xml',
        'views/account_move.xml',
        'data/mail_template.xml',
    ],


    'demo': [],
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
