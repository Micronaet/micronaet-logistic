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
from odoo import api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class LogisticFeesExtractWizard(models.TransientModel):
    _name = 'logistic.fees.extract.wizard'
    _description = 'Fees extract report'

    # -------------------------------------------------------------------------
    #                               BUTTON EVENT:
    # -------------------------------------------------------------------------
    @api.multi
    def fees_report_button(self):
        """ Account fees report
        """
        stock_pool = self.env['stock.picking']
        excel_pool = self.env['excel.writer']

        evaluation_date = self.evaluation_date
        excel_row = stock_pool.csv_report_extract_accounting_fees(
            evaluation_date=self.evaluation_date,
            team_id=self.team_id.id,
            mode='data')

        date = evaluation_date.replace('-', '_')
        filename = 'consegnato_il_giorno_%s' % evaluation_date

        # ---------------------------------------------------------------------
        #                               BUTTON EVENT:
        # ---------------------------------------------------------------------
        ws_name = 'Consegnato giornaliero'
        excel_pool.create_worksheet(ws_name)

        excel_pool.set_format()
        format_text = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'text': excel_pool.get_format('text'),
            'number': excel_pool.get_format('number'),
            'total': excel_pool.get_format('text_total'),

            'red': excel_pool.get_format('text_red'),
            }

        header = [
            'Tipo',
            'Modo',
            'Pos. fisc.',
            'Canale',
            'Data',
            'Cliente',
            'Ordine',
            'SKU',
            'Descrizione',
            'Pagamento',
            'Contropartita',
            'Q.',
            'Totale',
            'Tipo',
            'Agente',
            'IVA',
            'Triang.',
            ]

        width = [
            6, 6, 20, 10, 15, 30, 25, 15, 40, 10, 11, 5, 12, 5, 10, 5, 10,
            ]

        excel_pool.column_width(ws_name, width)

        row = 0
        excel_pool.write_xls_line(
            ws_name, row,
            [
               'Corrispettivi e fatture del giorno: %s' % date,
            ], default_format=format_text['title'])

        row += 2
        excel_pool.write_xls_line(
            ws_name, row, header,
            default_format=format_text['header'])
        pages = {}
        check_page = {
            'lines': [],
            'total': {},
        }
        for line in sorted(excel_row):
            row += 1

            # Readability:
            mode = line[0]
            fiscal = line[2]
            order = line[6]
            total = line[12]

            # -----------------------------------------------------------------
            # Page management:
            # -----------------------------------------------------------------

            if mode == 'CORR.':
                page = 'Corrispettivo'
            else:  # invoice:
                page = fiscal  # Fiscal position
                # Check page only for invoice:
                if order not in check_page['total']:
                    check_page['total'][order] = 0.0
                    check_page['lines'].append(line)  # only once!
                check_page['total'][order] += total

            if page not in pages:
                pages[page] = {}

            if order in pages[page]:
                pages[page][order][0] += total
            else:
                pages[page][order] = [total, line]

            if line[12]:
                format_color = format_text['text']
            else:
                format_color = format_text['red']
            # Write formatted with color
            excel_pool.write_xls_line(
                ws_name, row, line,
                default_format=format_color)

        # ---------------------------------------------------------------------
        # Extra pages:
        # ---------------------------------------------------------------------
        header = [
            'Modo',
            'Canale',
            'Data',
            'Cliente',
            'Ordine',
            'Pagamento',
            'Totale',
            'Tipo',
            'Agente',
            ]

        width = [
            6, 10, 15, 30, 25, 10, 10, 10, 10,
            ]

        for ws_name in sorted(pages):
            excel_pool.create_worksheet(ws_name)
            excel_pool.column_width(ws_name, width)
            row = 0
            excel_pool.write_xls_line(
                ws_name, row, header,
                default_format=format_text['header'])
            total = 0.0  # final total

            # Partial management:
            partial = 0.0
            previous_mode = False
            for order in sorted(
                    pages[ws_name],
                    key=lambda x: (pages[ws_name][x][1][1], x)):
                row += 1
                subtotal, line = pages[ws_name][order]
                mode = line[1]

                total += subtotal
                partial += subtotal

                if previous_mode == False:
                    previous_mode = mode

                # -------------------------------------------------------------
                # Check partial:
                # -------------------------------------------------------------
                if previous_mode != mode:
                    # Write partial
                    excel_pool.write_xls_line(ws_name, row, [
                        'Parziale %s:' % previous_mode,
                        partial,
                        ], default_format=format_text['total'], col=5)
                    row += 1
                    previous_mode = mode
                    partial = 0.0

                if subtotal:
                    format_color = format_text['text']
                else:
                    format_color = format_text['red']

                excel_pool.write_xls_line(ws_name, row, [
                    mode,  # Mode
                    line[3],  # Channel
                    line[4],  # Date
                    line[5],  # Customer
                    order,
                    line[9],  # Payment
                    subtotal,
                    line[13],  # Type
                    line[14],  # Agent
                    ], default_format=format_color)
            row += 1

            # -----------------------------------------------------------------
            # check last partial:
            # -----------------------------------------------------------------
            if previous_mode:  # always present
                # Write partial
                excel_pool.write_xls_line(ws_name, row, [
                    'Parziale %s:' % previous_mode,
                    partial,
                    ], default_format=format_text['total'], col=5)
                row += 1

            excel_pool.write_xls_line(
                ws_name, row, ['Totale', total], format_text['total'], col=5)

        # ---------------------------------------------------------------------
        #                         Extra page:
        # ---------------------------------------------------------------------
        ws_name = 'Controllo fatturato'
        header = [
            'Modo',
            'Posizione fiscale',
            'Canale',
            'Data',
            'Cliente',
            'Agente',
            'Ordine',
            'Pagamento',
            'Triangol.',
            'Totale',
            'Totale trian.'
        ]

        width = [
            6, 25, 10, 15, 35, 10, 25, 10, 10, 10, 10,
        ]

        excel_pool.create_worksheet(ws_name)
        excel_pool.column_width(ws_name, width)
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, header,
            default_format=format_text['header'])
        triangle_total = master_total = 0.0  # final total
        for line in sorted(
                check_page['lines'],
                # key=lambda x: (check_page['lines'][x][1], x),
                ):
            (mode, market, fiscal_position, channel, date, partner, order,
             default_code, name, payment, account, qty, total, expense,
             agent, vat, triangle) = line

            # TODO bad, better use: .partner_private:
            if fiscal_position == 'B2C':
                # Remove B2C fiscal position
                continue
            row += 1

            order_total = check_page['total'][order]
            if vat:
                order_total += order_total * vat / 100.0
            if triangle:
                triangle_total += order_total

            master_total += order_total
            excel_pool.write_xls_line(ws_name, row, [
                mode,
                fiscal_position,
                channel,
                date,
                partner,
                agent,
                order,
                payment,
                triangle,
                (order_total, format_text['number']),
                (order_total, format_text['number']) if triangle else '',

            ], default_format=format_text['text'])
        # Total line:
        if check_page['lines']:
            row += 1
            excel_pool.write_xls_line(
                ws_name, row, ['Totale', master_total, triangle_total],
                format_text['total'], col=8)
        return excel_pool.return_attachment(filename)

    @api.multi
    def fees_extract_button(self):
        """ Account fees report
        """
        stock_pool = self.env['stock.picking']
        stock_pool.csv_report_extract_accounting_fees(
            evaluation_date=self.evaluation_date,
            team_id=self.team_id.id)

    # -------------------------------------------------------------------------
    #                               COLUMNS:
    # -------------------------------------------------------------------------
    evaluation_date = fields.Date(
        'Date', required=True,
        default=fields.Datetime.now())
    team_id = fields.Many2one(
        'crm.team', 'Team',
        help='Selezionando anche il team è possibile rigenerare un solo '
             'canale di vendita (usato nel caso di errori evitando così '
             'la generazione complessiva di tutti i corrispettivi '
             'giornalieri.')
