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
import pdb
from odoo import fields, api, models
from odoo import tools
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class SaleOrder(models.AbstractModel):
    """ Sale Order Report action
    """
    _inherit = 'sale.order'

    @api.multi
    def partial_delivery_status_report(self):
        """ Extract partial order delivery report
        """
        line_pool = self.env['sale.order.line']
        excel_pool = self.env['excel.writer']

        # Domain generation:
        domain = [
            ('order_id.logistic_source', 'not in', ('internal', 'refund')),
            ('order_id.logistic_state', '=', 'pending'),
            # ('order_id.logistic_state', 'in', ('draft', 'order', 'delivering', 'pending')),
        ]

        # --------------------------------------------------------------------------------------------------------------
        #                       Excel Extract:
        # --------------------------------------------------------------------------------------------------------------
        ws_name = 'Consegne pendenti'
        excel_pool.create_worksheet(ws_name)

        # --------------------------------------------------------------------------------------------------------------
        # Format:
        # --------------------------------------------------------------------------------------------------------------
        excel_pool.set_format()
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')

        f_white_text = excel_pool.get_format('text_top')
        # f_green_text = excel_pool.get_format('bg_green')
        # f_yellow_text = excel_pool.get_format('bg_yellow')

        f_white_number = excel_pool.get_format('text_top_center')
        # f_green_number = excel_pool.get_format('bg_green_number')
        # f_yellow_number = excel_pool.get_format('bg_yellow_number')

        # --------------------------------------------------------------------------------------------------------------
        # Setup page:
        # --------------------------------------------------------------------------------------------------------------
        excel_pool.column_width(ws_name, [
            15, 45, 40, 20,
            15, 15, 15,
            60,
        ])

        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            'Consegne pendenti derivate da ordini in "Consegna Pentente"'], default_format=f_title)

        row += 1
        title = [
            'Codice', 'Descrizione', 'Ordine cliente', 'Origine',
            'Ordinati', 'Ricevuti', 'Da ricevere',
            'Dettaglio consegne',
        ]
        excel_pool.write_xls_line(ws_name, row, title, default_format=f_header)
        excel_pool.autofilter(ws_name, row, 0, row, len(title) - 1)
        excel_pool.freeze_panes(ws_name, 2, 1)

        # --------------------------------------------------------------------------------------------------------------
        # Read data
        # --------------------------------------------------------------------------------------------------------------
        lines = sorted(line_pool.search(domain), key=lambda l: (l.order_id.name, l.sequence))
        _logger.warning('Report status filter with: %s [Tot. %s]' % (domain, len(lines)))

        not_consider = ('PFU', )
        for line in lines:  # TODO sort?
            order = line.order_id
            logistic_received_qty = line.logistic_received_qty
            order_name = '{} del {}'.format(order.name, order.date_order)[:-9]

            if logistic_received_qty <= 0:
                continue
            template = line.product_id.product_tmpl_id
            default_code = template.default_code or ''

            if default_code in not_consider:
                # Remove not used product
                continue
            # KIT:
            # origin = line.origin_product_id.product_tmpl_id
            # 'x' if template.type == 'service' else '',

            # Load analysis:
            load_comment = []
            supplier = False
            for load in line.load_line_ids:
                supplier_name = load.delivery_id.supplier_id.name
                if supplier_name:
                    supplier = True
                load_comment.append('{} >> {}: q. {} Carico: {}'.format(
                    supplier_name or 'FELAPPI', (load.date or '')[:10], int(load.product_uom_qty), load.origin))
            if not supplier:
                _logger.warning('Jump line, supplier is internal')
                continue
            load_total = len(load_comment) or 1
            row += 1
            excel_pool.write_xls_line(ws_name, row, [
                template.default_code,
                line.name,
                '{} [{}]'.format(order_name, order.logistic_state),
                order.logistic_source,

                (int(line.product_uom_qty), f_white_number),
                (int(line.logistic_received_qty), f_white_number),
                (int(line.logistic_remain_qty), f_white_number),

                '\n'.join(load_comment),  # Supply detail (supplier, q., data)

                # Q. block:
                #line.logistic_covered_qty,
                #line.logistic_uncovered_qty,
                #line.logistic_purchase_qty,
                #line.logistic_delivered_qty,
                #line.logistic_undelivered_qty,
            ], default_format=f_white_text)
            excel_pool.row_height(ws_name, [row], height=16 * load_total)

        # ---------------------------------------------------------------------
        # Save file:
        # ---------------------------------------------------------------------
        return excel_pool.return_attachment('Ordini_pendenti')
