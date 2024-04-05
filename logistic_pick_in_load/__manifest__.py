# -*- coding: utf-8 -*-
#!/usr/bin/python
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2018 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

{
    'name': 'Picking in load',
    'version': '1.0',
    'category': 'Purchase',
    'sequence': 5,
    'summary': 'Picking, load document',
    # 'description': '',
    'website': 'https://micronaet.com',
    'depends': [
        'base',
        'product',
        'purchase',
        'mmac_base',
        'logistic_stock_position',  # Position on stock (for load)
        ],
    'data': [
        'views/picking_load_view.xml',
        'views/temp_picking_load_view.xml',
        ],
    'demo': [],
    'css': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    }
