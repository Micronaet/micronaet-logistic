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
    'name': 'Tyres Logistic Management',
    'version': '1.0',
    'category': 'Logistic',
    'sequence': 5,
    'summary': 'Logistic Management, Sale, Supplier order and delivery',
    'website': 'https://micronaet.com',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'sales_team',
        'product',
        'account',
        'stock',
        'purchase',
        'queue_job',
        # 'confirm_dialog_wizard',  # Dialog message management

        # Report:
        'web',
        'web_editor',

        'product_folder_image',  # For image management
        'excel_export',  # Export in Excel
        'tyres_logistic_ddt',
        'logistic_product_supplier',  # Supplier purchase management
        'logistic_secure_payment',  # For auto go ahead when confirmed payment
        'tyres_logistic_carrier',  # Carrier management
        # 'mmac_odoo4', # Extra fields (loop reference)

        # 'logistic_stock_position', # Stock position
        # 'order_line_explode_kit', # Sale kit explode
        # 'order_line_change_product', # Replaced link product
        # 'product_default_supplier', # First supplier management
        # 'logistic_account_report', # DDT Report
        # 'logistic_purchase_export', # Export files
        # 'logistic_order_unification', # Order unification
        # 'l18n_it_fatturapa', # Fattura PA Management
        ],
    'data': [
        'security/logistic_group.xml',
        'security/ir.model.access.csv',

        # Data:
        'data/office_data.xml',

        # Views:
        'views/logistic_management_view.xml',
        'views/dropship_view.xml',
        'wizard/manual_operation_view.xml',  # Test events
        'wizard/status_extract_view.xml',  # Extract operation
        'wizard/fees_report_view.xml',  # Extract feed
        'wizard/revenue_report_view.xml',  # Statistic report
        'wizard/load_report_wizard.xml',  # Delivery report
        # 'views/fatturapa_view.xml',
        # 'views/account_parameter_view.xml', # XXX move in logistic_ddt
        ],
    'demo': [],
    'css': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    }
