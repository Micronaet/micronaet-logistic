#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
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

import os
import sys
import logging
import odoo
from odoo import api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)


class AccountFiscalPosition(models.Model):
    """ Model name: AccountFiscalPosition
    """
    _inherit = 'account.fiscal.position'

    is_pfu = fields.Boolean('PFU refund',
        help='If checked all sale with this position go in report')


class StockPickingPfuExtractWizard(models.TransientModel):
    """ Model name: StockPicking
    """
    _name = 'stock.picking.pfu.extract.wizard'
    _description = 'Logistic manual operation'

    # -------------------------------------------------------------------------
    #                            COLUMNS:
    # -------------------------------------------------------------------------
    partner_id = fields.Many2one('res.partner', 'Supplier',  # required=True,
        domain="[('supplier', '=', True)]")
    from_date = fields.Date('From date >=', required=True)
    to_date = fields.Date('To date <', required=True)
    # -------------------------------------------------------------------------

    @api.model
    def get_data_domain(self, from_date, to_date):
        return [
            # Header
            ('delivery_id.date', '>=', from_date),
            ('delivery_id.date', '<', to_date),
            ('logistic_load_id', '!=', False), # Linked to order
            ('logistic_load_id.order_id.logistic_source', 'not in', (
                'refund', )),  # Not refund
            # TODO Order web only?
            ]
    @api.multi
    def extract_fiscal_excel_pfu_report(self, ):
        """ Extract fiscal report
        """
        move_pool = self.env['stock.move']
        excel_pool = self.env['excel.writer']
        company_pool = self.env['res.company']

        from_date = self.from_date
        to_date = self.to_date

        # Select all supplier used:
        company = company_pool.search([])[0]
        country_id = company.partner_id.country_id.id
        domain = self.get_data_domain(from_date, to_date)
        domain.extend([
            # ('logistic_load_id.order_id.partner_invoice_id.country_id', '=',
            #    country_id), # Only sold in Italy
            # ('dropship_manage', '=', False),

            # TODO on order:
            # '&',
            # ('logistic_source', 'not in', ('refund', )),

            '|',
            ('delivery_id.supplier_id.country_id', '=', False),
            ('delivery_id.supplier_id.country_id', '!=', country_id),
            ])

        # ---------------------------------------------------------------------
        #                           Collect data:
        # ---------------------------------------------------------------------
        # A. All stock move sale
        supplier_category_move = {}
        for move in move_pool.search(domain):
            supplier = move.delivery_id.supplier_id
            category = move.product_id.mmac_pfu.name or ''
            if not category: # Missed category product not in report
                continue

            if supplier not in supplier_category_move:
                supplier_category_move[supplier] = {}

            if category not in supplier_category_move[supplier]:
                supplier_category_move[supplier][category] = 0

            supplier_category_move[supplier][category] += move.product_uom_qty

        # Export only total grouped by RAEE mode:
        # ---------------------------------------------------------------------
        #                          EXTRACT EXCEL:
        # ---------------------------------------------------------------------
        # Excel file configuration:
        header = ('RAEE', 'Fornitore', 'Nazione', u'Q.tà')
        column_width = (5, 40, 25, 15)

        ws_name = 'PFU forniori esteri'

        # -----------------------------------------------------------------
        # Excel sheet creation:
        # -----------------------------------------------------------------
        excel_pool.create_worksheet(ws_name)
        excel_pool.column_width(ws_name, column_width)
        excel_pool.set_format()
        format_text = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'text': excel_pool.get_format('text'),
            'number': excel_pool.get_format('number'),
            }

        # ---------------------------------------------------------------------
        # Write detail:
        # ---------------------------------------------------------------------
        row = total = 0

        excel_pool.write_xls_line(ws_name, row, header, format_text['header'])
        for supplier in sorted(supplier_category_move, key=lambda x: x.name):
            for category in supplier_category_move[supplier]:
                row += 1
                subtotal = supplier_category_move[supplier][category]
                total += subtotal
                # Header write:
                excel_pool.write_xls_line(ws_name, row, [
                    category,
                    supplier.name,
                    supplier.country_id.name or '',
                    (subtotal, format_text['number']),
                    ], default_format=format_text['text'])

        # -----------------------------------------------------------------
        # Write total line:
        # -----------------------------------------------------------------
        # Total
        row += 1
        excel_pool.write_xls_line(ws_name, row, (
            'Totale:', total,
            ), default_format=format_text['number'], col=2)

        # ---------------------------------------------------------------------
        # Save file:
        # ---------------------------------------------------------------------
        return excel_pool.return_attachment('Report_Tax_PFU')

    @api.multi
    def extract_excel_pfu_report(self, ):
        """ Extract Excel PFU report
        """
        # Utility:
        def get_ipcode(supplier, product, ipcode_cache):
            """ Extract IP code for product
            """
            ipcode = ipcode_cache.get(product)
            if ipcode:
                return ipcode

            product_detail = [
                line for line in product.supplier_stock_ids if
                line.supplier_id == supplier]
            if product_detail:
                ipcode = product_detail[0].ipcode
                ipcode_cache[product] = ipcode
                return ipcode
            return ''

        move_pool = self.env['stock.move']
        excel_pool = self.env['excel.writer']

        from_date = self.from_date
        to_date = self.to_date
        supplier = self.partner_id

        domain = self.get_data_domain(from_date, to_date)

        # Sell Extra CEE:
        domain.append(
            # Linked to order
            ('logistic_load_id.order_id.partner_invoice_id.property_account_position_id.is_pfu', '=', True),
            )

        if supplier:
            domain.append(
                ('delivery_id.supplier_id', '=', supplier.id),
                )

        # ---------------------------------------------------------------------
        #                           Collect data:
        # ---------------------------------------------------------------------
        # A. All stock move sale
        supplier_category_move = {}
        for move in move_pool.search(domain):
            supplier = move.delivery_id.supplier_id
            product = move.product_id
            category = product.mmac_pfu.name or ''
            if not category:  # Missed category product not in report
                continue

            if supplier not in supplier_category_move:
                supplier_category_move[supplier] = {}

            if category not in supplier_category_move[supplier]:
                supplier_category_move[supplier][category] = []

            supplier_category_move[supplier][category].append(move)

        # ---------------------------------------------------------------------
        #                          EXTRACT EXCEL:
        # ---------------------------------------------------------------------
        # Excel file configuration:
        header = (
            'RAEE', 'Cod. Articolo', 'Cod. Forn.', 'Descrizione', u'Q.tà',
            'Doc Fornitore', 'Data Doc.', 'N. Fattura', 'N. Nostra fattura',
            'Data Doc.', 'ISO stato')

        column_width = (
            5, 15, 15, 45, 5,
            15, 12, 12, 15,
            10, 8,
            )

        # ---------------------------------------------------------------------
        # Write detail:
        # ---------------------------------------------------------------------
        ipcode_cache = {}
        setup_complete = False  # For initial setup:
        for supplier in sorted(supplier_category_move, key=lambda x: x.name):
            ws_name = supplier.name.strip()

            # -----------------------------------------------------------------
            # Excel sheet creation:
            # -----------------------------------------------------------------
            excel_pool.create_worksheet(ws_name)
            excel_pool.column_width(ws_name, column_width)
            if not setup_complete:  # First page only:
                setup_complete = True
                excel_pool.set_format()
                format_text = {
                    'title': excel_pool.get_format('title'),
                    'header': excel_pool.get_format('header'),
                    'text': excel_pool.get_format('text'),
                    'number': excel_pool.get_format('number'),
                    }

            # Header write:
            row = 0
            excel_pool.write_xls_line(ws_name, row, [
                u'Fornitore:',
                u'',
                supplier.name or '',
                supplier.sql_supplier_code or '',
                u'',
                u'Dalla data: %s' % from_date,
                u'',
                u'Alla data: %s' % to_date,
                ], default_format=format_text['title'])

            row += 2
            excel_pool.write_xls_line(
                ws_name, row, header,
                default_format=format_text['header'])

            total = 0
            for category in sorted(supplier_category_move[supplier]):
                subtotal = 0
                for move in sorted(
                        supplier_category_move[supplier][category],
                        key=lambda x: x.date):
                    row += 1

                    # Readability:
                    order = move.logistic_load_id.order_id
                    partner = order.partner_invoice_id
                    product = move.product_id
                    qty = move.product_uom_qty  # Delivered qty

                    # Get invoice reference:
                    invoice_date = ''
                    invoice_number = ''
                    for invoice in order.logistic_picking_ids:
                        invoice_date = invoice.invoice_date or ''
                        invoice_number = invoice.invoice_number or ''
                        if invoice_number:
                            break  # Stop when find one invoice!
                        else:
                            invoice_number = 'No fatt.: %s' % order.name

                    # ---------------------------------------------------------
                    #                    Excel writing:
                    # ---------------------------------------------------------
                    # Total operation:
                    total += qty
                    subtotal += qty

                    # ---------------------------------------------------------
                    # Write data line:
                    # ---------------------------------------------------------
                    excel_pool.write_xls_line(ws_name, row, (
                        category,  # product.mmac_pfu.name,
                        product.default_code,
                        get_ipcode(supplier, product, ipcode_cache),  # ipcode
                        product.name_extended,  # name,
                        (qty, format_text['number']),  # todo check if it's all
                        move.delivery_id.name,  # Delivery ref.
                        move.delivery_id.date,
                        '',  # Number supplier invoice
                        invoice_number,  # Our invoice
                        invoice_date[:10],  # Date doc,
                        partner.country_id.code or '??',  # ISO country
                        ), default_format=format_text['text'])
                row += 1
                excel_pool.write_xls_line(ws_name, row, (
                    subtotal,
                    ), default_format=format_text['number'], col=3)

            # -----------------------------------------------------------------
            # Write data line:
            # -----------------------------------------------------------------
            # Total
            row += 1
            excel_pool.write_xls_line(ws_name, row, (
                'Totale:', total,
                ), default_format=format_text['number'], col=2)

        # ---------------------------------------------------------------------
        # Save file:
        # ---------------------------------------------------------------------
        return excel_pool.return_attachment('Report_PFU')
