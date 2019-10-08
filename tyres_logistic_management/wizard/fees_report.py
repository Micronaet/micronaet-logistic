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
            evaluation_date, mode='data')
        
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
            ]

        width = [
            6, 6, 20, 10, 15, 30, 25, 15, 40, 10, 10, 15, 10, 10, 10,
            ]    

        excel_pool.column_width(ws_name, width)

        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            'Corrispettivi e fatture del giorno: %s' % date,
            ], default_format=format_text['title'])

        row += 2
        excel_pool.write_xls_line(ws_name, row, header,             
            default_format=format_text['header'])            
        pages = {}
        for line in sorted(excel_row):
            row += 1
            
            # Readability: 
            mode = line[0] 
            fiscal = line[2]          
            order = line[6] 
            total = line[12]
            
            if mode == 'CORR.':
                page = 'Corrispettivo'
            else: # invoice:
                page = fiscal # Fiscal position

            if page not in pages:
                pages[page] = {}

            if order in pages[page]:
                pages[page][order][0] += total
            else:
                pages[page][order] = [total, line]

            excel_pool.write_xls_line(ws_name, row, line,
                default_format=format_text['text'])
        
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
            excel_pool.write_xls_line(ws_name, row, header,             
                default_format=format_text['header'])
            total = 0.0 # final total

            # Partial management:
            partial = 0.0
            previous_mode = False
            for order in sorted(pages[ws_name], 
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

                excel_pool.write_xls_line(ws_name, row, [
                    mode, # Mode
                    line[3], # Channel
                    line[4], # Date
                    line[5], # Customer
                    order,
                    line[9], # Payment
                    subtotal, 
                    line[13], # Type
                    line[14], # Agent             
                    ], default_format=format_text['text'])
            row += 1

            # -----------------------------------------------------------------
            # check last partial:
            # -----------------------------------------------------------------
            if previous_mode: # always present
                # Write partial
                excel_pool.write_xls_line(ws_name, row, [
                    'Parziale %s:' % previous_mode,
                    partial,
                    ], default_format=format_text['total'], col=5)   
                row += 1    

            excel_pool.write_xls_line(
                ws_name, row, ['Totale', total], format_text['total'], col=5)
                
        return excel_pool.return_attachment(filename)

    @api.multi
    def fees_extract_button(self):
        """ Account fees report
        """
        stock_pool = self.env['stock.picking']        
        stock_pool.csv_report_extract_accounting_fees(self.evaluation_date)

    # -------------------------------------------------------------------------
    #                               COLUMNS: 
    # -------------------------------------------------------------------------    
    evaluation_date = fields.Date('Date', required=True, 
        default=fields.Datetime.now())

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
