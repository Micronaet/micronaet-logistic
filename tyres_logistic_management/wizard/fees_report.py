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
from datetime import datetime, timedelta
import json
import requests

_logger = logging.getLogger(__name__)


class SaleOrderInherit(models.Model):
    """ Object to link all stock picking for Fees API call
    """
    _inherit = 'sale.order'

    # Server action:
    def pending_fees_order(self):
        """ Open pending sale order for corrispettivo
        """
        picking_pool = self.env['stock.picking']

        company = self.env.user.company_id

        # Duplicated code:
        now = datetime.now()
        min_date = '2026-07-07'  # Start using API procedure!

        now_date = now.strftime('%Y-%m-%d')  # Used in various part (to_date in API, Feed date)
        to_date = now_date
        interval_days = company.api_fees_from_days or 0
        if interval_days > 0:
            from_date = (now - timedelta(days=interval_days)).strftime('%Y-%m-%d')
            if from_date < min_date:
                from_date = min_date
        else:
            from_date = to_date  # No need to be corrected

        domain = [
            # Period:
            ('scheduled_date', '>=', '%s 00:00:00' % from_date),
            ('scheduled_date', '<=', '%s 23:59:59' % to_date),
            ('fees_api_id', '=', False),  # Unlinked
            ('is_fees', '=', True),  # Used only when extract
        ]

        # Collect order:
        order_ids = []
        pickings = picking_pool.search(domain)
        _logger.info('Found # {} picking'.format(len(pickings)))
        for picking in pickings:
            order_id = picking.sale_order_id.id
            if order_id:
                order_ids.append(order_id)

        tree_id = self.env.ref('sale.view_order_tree').id

        _logger.info('Found # {} order'.format(len(order_ids)))
        if order_ids:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Ordini da Corrispettivo aperti',
                'view_type': 'form',
                'view_mode': 'tree,form,graph,pivot',
                'res_model': 'sale.order',
                'view_id': tree_id,
                'views': [
                    (tree_id, 'tree'),
                    (False, 'form'),
                    (False, 'pivot'),
                    (False, 'graph'),
                ],
                'domain': [('id', 'in', order_ids)],
                'context': self.env.context,
                'target': 'current',  # 'new'
                'nodestroy': False,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Ordini da Corrispettivo non trovati',
                'view_type': 'form',
                'view_mode': 'tree,form,graph,pivot',
                'res_model': 'sale.order',
                'view_id': tree_id,
                'views': [
                    (tree_id, 'tree'),
                    (False, 'form'),
                    (False, 'pivot'),
                    (False, 'graph'),
                ],
                'domain': [('id', '=', 0)],
                'context': self.env.context,
                'target': 'current',  # 'new'
                'nodestroy': False,
            }

# API Object:
class LogisticFeesHeader(models.Model):
    """ Object to link all stock picking for Fees API call
    """
    _name = 'logistic.fees.api'
    _description = 'Fees API Document'
    _order = 'date desc'

    def scheduled_api_sync(self):
        """ Update via schedules
        """
        # Search only draft fees:
        fees = self.search([
            ('state', '=', 'draft'),
        ])
        _logger.info('Found Fees to sync: {}'.format(len(fees)))
        for fee in fees:
            fee.api_sync()
        return True

    def api_sync(self):
        """ Syncro with API to Account
        """
        sale_line_pool = self.env['sale.order.line']
        move_pool = self.env['stock.move']

        # Parameters for API call
        company = self.env.user.company_id

        url = company.api_root_url
        endpoint = 'CreateUncashedReceipts'
        location = '%s/%s' % (url, endpoint)
        token = company.api_token or company.api_get_token()

        fee = self
        # Call check:
        if fee.json_reply:
            _logger.error('Fee yet sent! No more API call!')
            return False

        # --------------------------------------------------------------------------------------------------------------
        # Create Payload:
        # --------------------------------------------------------------------------------------------------------------
        # Fees Parameters:
        team = fee.team_id
        channel = team.channel_ref

        api_fees = {  # Payload
            "Customer": team.team_code_ref, # es: "0000061" Intestatario della ricevuta non incassata
            "Payment": fee.payment_code, # es: "250" Codice della condizione di pagamento
            "Salesperson": channel, # es: "0062" Canale di vendita
            "IDReceipts": '{}'.format(fee.id),  # Identificativo univoco della ricevuta
            "TotalOdoo": 0.0,
            "Details": [],  # Righe dettaglio
        }
        master_total = 0.0
        for move in fee.move_ids:
            product = move.product_id
            qty = move.product_uom_qty
            total = qty * move.logistic_unload_id.price_unit

            # ----------------------------------------------------------------------------------------------------------
            # Get PFU integration:
            # ----------------------------------------------------------------------------------------------------------
            order_line_id = move.logistic_unload_id.id  # Sale order line
            if order_line_id:  # Search PFU linked to this line:
                # Search: linked SOL line, from stock move pointing the current SOL
                pfu_stock_moves = move_pool.search([
                    ('logistic_unload_id.mmac_pfu_line_id', '=', order_line_id),
                ])
                if pfu_stock_moves:
                    pfu_stock_move = pfu_stock_moves[0]
                    price_unit = pfu_stock_move.logistic_unload_id.price_unit  # From sale order line
                    total += pfu_stock_moves.product_uom_qty * price_unit  # Integrate PFU in total

            master_total += total  # Product + PFU (if present)
            api_fees['Details'].append(
                {
                    "LineType": 'S' if product.is_expence else 'M', # Row type ex: "M", Tipologia della riga
                    "Item": product.default_code or '', # ex: "VALVOLAMOTO113_ARGENTO",  Codice articolo
                    "Quantity": qty, # es: 3.0, # Quantità della riga
                    "Total": -total, # es: -10.0, # Totale (espresso in negativo)
                }
            )

        # Update master total:
        api_fees["TotalOdoo"] = master_total

        # --------------------------------------------------------------------------------------------------------------
        # Send via API
        # --------------------------------------------------------------------------------------------------------------
        json_dumps = json.dumps(api_fees)
        loop_times = 1

        while loop_times <= 2:  # Loop twice if token error (reload API key)
            loop_times += 1
            api_header = {
                'Authorization': 'bearer %s' % token,
                'accept': 'text/plain',
                'Content-Type': 'application/json',
            }
            # Send Corrispettivi:
            _logger.info(
                'Calling: %s\n'
                'JSON: %s [Attempt: %s]...' % (location, json_dumps, loop_times - 1))
            reply = requests.post(location, data=json_dumps, headers=api_header)
            if reply.ok:
                reply_json = reply.json()
                """ 
                "DocNo": NUMERO DOCUMENTO DELLA RICEVUTA, es: "000528",
                "DocumentDate": DATA DOCUMENTO, es: "2026-04-29T00:00:00",
                "PostingDate": DATA REGISTRAZIONE, es: "2026-04-29T00:00:00",
                "Customer": CLIENTE A CUI E’ INTESTATA LA RICEVUTA, es: "0000061",
                "Payment": ": CONDIZIONE DI PAGAMENTO, es: "025",
                "ExternalDocumentId": ID ODOO, es: "XXXXXXX",
                "TotalAmount": TOTALE IVATO, es: 1000,
                "ErrorDetails": ELENCO DELLE EVENTUALI RIGHE SCARTATE, es: [
                    {
                    "LineType": TIPOLOGIA DI RIGA, es: "M",
                    "Item": CODICE ARTICOLO, es: "VALVOLAMOTO113_ARGENTO",
                    "Quantity": QUANTITÀ, es: 3.0,
                    "Total": TOTALE IN NEGATIVO DELLA RIGA (VALORE PASSATO IN INPUT), es: -10.0,
                    "MSGError": MESSAGGIO DI ERRORE CHE INDICA IL MOTIVO PER CUI HO SCARTATO LA RIGA, es: "Articolo non"
                    }
                ]
                """

                _logger.info('SUCCESS: [Fees operation] Loaded correctly')
                # Update ODOO Fees with returned data:
                try:
                    fee.write({
                        'account_ref': reply_json['docNo'],
                        'account_date': reply_json['documentDate'][:10],
                        'error': reply_json['errorDetails'] or False,
                        'state': 'done',
                        'json_reply': reply.text,
                        'odoo_total': master_total,
                        'account_total': reply_json['totalAmount'],
                    })
                    _logger.error('ODOO Fee updated')
                except:
                    # Write only JSON call:
                    _logger.error('Error parse Fee reply')
                    fee.write({
                        'json_reply': reply.text,
                    })

                _logger.info('Corrispettivi datato oggi - Canale %s Pagamento %s, Esito OK\n' % (
                    api_fees['Customer'],
                    api_fees['Payment'],
                    ))
                break  # No other loop

            elif reply.status_code == 401:  # Token error
                _logger.error(
                    '[ERROR] API Fees operation: '
                    'Reload token...')
                token = company.api_get_token()
            else:  # Error not managed
                _logger.error(
                    '[ERROR] API Fees operation: '
                    'Errore non gestito:\n{}'.format(sys.exc_info()))
        return True

    # Header data:
    date = fields.Date(string='Data scontrino', required=True)
    state = fields.Selection([
        ('draft', 'Da sincronizzare'),
        ('done', 'Sincronizzato'),
        ('cancel', 'Annullato'),
        ('manual', 'Manuale'),
    ], string='Stato', required=True, default='draft')

    payment_term_id = fields.Many2one('account.payment.term', 'Pagamento')
    team_id = fields.Many2one('crm.team', 'Canale di vendita')
    payment_code = fields.Char('Codice pagamento', required=True, size=10)  # order.payment_term_id.account_ref

    odoo_total = fields.Float('Totale ODOO', digits=(16, 2))
    account_total = fields.Float('Totale Gestionale', digits=(16, 2))

    # Check:
    extra_date = fields.Text(
        'Date extra',
        help='Indica quali sono le date extra collegate allo scontrino, utilizzato anche per controllare '
             'scontrini ricorrenti che non verrebbero chiusi male (le date devono essere massimo di 3 gg. precedenti!')

    # From API:
    json_reply = fields.Text('Risposta JSON')
    force_account_ref = fields.Char('Numero forzato', help='Indicazione del numero scontrino forzato manualmente')
    account_ref = fields.Char(  # order.payment_term_id.account_ref
        'Rif. scontrino (gest.)', size=20,
        help='Riferimento scontrino definito dal gestionale (presente quando viene sincronizzato')
    account_date = fields.Date('Data scontrino (gest.)')
    error = fields.Boolean(
        'Con errore',
        help='Indica che la sincro ha dato qualche errore durante la procedura, utilizzata anche per segnalare '
             'eventuali date extra troppo indietro nel tempo (max -3 gg!)')


class StockPickingInherit(models.Model):
    """ Model name: Stock picking Relations
    """

    _inherit = 'stock.picking'

    # Link fields:
    fees_api_id = fields.Many2one(
        'logistic.fees.api', 'Scontrino', ondelete='set null',
        help='Crea e collega lo scontrino al Picking Out che ha generato lo scarico effettivo')


class StockMoveInherit(models.Model):
    """ Model name: Stock move Relations
    """

    _inherit = 'stock.move'

    # Link fields:
    fees_api_id = fields.Many2one(
        'logistic.fees.api', 'Scontrino', ondelete='set null',
        help='Crea e collega lo scontrino alle righe magazzino che hanno generato lo scarico effettivo')


class LogisticFeesHeaderInerit(models.Model):
    """ Object to link all stock picking for Fees API call
    """
    _inherit = 'logistic.fees.api'

    picking_ids = fields.One2many('stock.picking', 'fees_api_id', string='Picking collegati')
    move_ids = fields.One2many('stock.move', 'fees_api_id', string='Movimenti collegati')


# Wizard:
class LogisticFeesExtractWizard(models.TransientModel):
    _name = 'logistic.fees.extract.wizard'
    _description = 'Fees extract report'

    # ------------------------------------------------------------------------------------------------------------------
    #                               BUTTON EVENT:
    # ------------------------------------------------------------------------------------------------------------------
    @api.multi
    def fees_report_button(self):
        """ Account fees report ["PRINT" button]
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

        # --------------------------------------------------------------------------------------------------------------
        #                               BUTTON EVENT:
        # --------------------------------------------------------------------------------------------------------------
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
            'Tipo', 'Modo', 'Pos. fisc.', 'Canale',
            'Data', 'Cliente', 'Ordine',
            'SKU', 'Descrizione',
            'Pagamento', 'Contropartita',
            'Q.', 'Totale',
            'Tipo', 'Agente', 'IVA', 'Triang.',
            ]
        width = [
            6, 6, 20, 10,
            15, 30, 25,
            15, 40,
            10, 11,
            5, 12,
            5, 10, 5, 10,
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

            # ----------------------------------------------------------------------------------------------------------
            # Page management:
            # ----------------------------------------------------------------------------------------------------------
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
            excel_pool.write_xls_line(ws_name, row, line, default_format=format_color)

        # --------------------------------------------------------------------------------------------------------------
        # Extra pages:
        # --------------------------------------------------------------------------------------------------------------
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
            excel_pool.write_xls_line(ws_name, row, header, default_format=format_text['header'])
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

                # ------------------------------------------------------------------------------------------------------
                # Check partial:
                # ------------------------------------------------------------------------------------------------------
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

            # ----------------------------------------------------------------------------------------------------------
            # check last partial:
            # ----------------------------------------------------------------------------------------------------------
            if previous_mode:  # always present
                # Write partial
                excel_pool.write_xls_line(ws_name, row, [
                    'Parziale %s:' % previous_mode,
                    partial,
                    ], default_format=format_text['total'], col=5)
                row += 1

            excel_pool.write_xls_line(
                ws_name, row, ['Totale', total], format_text['total'], col=5)

        # --------------------------------------------------------------------------------------------------------------
        #                         Extra page:
        # --------------------------------------------------------------------------------------------------------------
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
                ws_name, row, ['Totale', master_total, triangle_total], format_text['total'], col=8)
        return excel_pool.return_attachment(filename)


    @api.multi
    def fees_report_button_v2(self):
        """ Account fees report ["PRINT" button]
            Version 2.0
        """
        stock_pool = self.env['stock.picking']
        excel_pool = self.env['excel.writer']
        payment_pool = self.env['account.payment.term']

        # --------------------------------------------------------------------------------------------------------------
        # Preload payment terms
        # --------------------------------------------------------------------------------------------------------------
        payment_terms = {}
        for payment in payment_pool.search([]):
            payment_terms[payment.account_ref] = payment.name

        # Filename:
        evaluation_date = self.evaluation_date

        # Get collected data:
        excel_row = stock_pool.csv_report_extract_accounting_fees(
            evaluation_date=self.evaluation_date, team_id=self.team_id.id, mode='data')

        filename = 'consegnato_il_giorno_v2_%s' % evaluation_date.replace('-', '_')

        # --------------------------------------------------------------------------------------------------------------
        #                            First loop to collect data:
        # --------------------------------------------------------------------------------------------------------------
        pages = {
            'Corrispettivo': {},
            'B2C': {},
            'B2B SEPA': {},
            'B2B RID 14 gg': {},
        }
        check_page = {
            'lines': [],
            'total': {},
        }
        for line in sorted(excel_row):
            # Readability:
            mode = line[0]  # Document type: CORR. / FATT.
            customer_mode = line[1]  # b2b / b2c
            fiscal = line[2]
            order = line[6]
            payment_code = line[9]
            total = line[12]

            # ----------------------------------------------------------------------------------------------------------
            # Page management:
            # ----------------------------------------------------------------------------------------------------------
            if mode == 'CORR.':  # o FATT
                page = 'Corrispettivo'
            else:
                if customer_mode == 'b2c':
                    page = 'B2C'
                elif customer_mode == 'b2b':
                    if payment_code == '026':
                        page = 'B2B SEPA'
                    elif payment_code == '036':
                        page = 'B2B RID 14 gg'
                    else:
                        _logger.error('B2B not in 036 / 026 Payment code')
                        continue

                # Check page only for invoice:
                if order not in check_page['total']:
                    check_page['total'][order] = 0.0
                    check_page['lines'].append(line)  # only once!
                check_page['total'][order] += total

            if order in pages[page]:
                pages[page][order][0] += total
            else:
                pages[page][order] = [total, line]

        # --------------------------------------------------------------------------------------------------------------
        # Generate Excel pages:
        # --------------------------------------------------------------------------------------------------------------
        header = [
            'Modo', 'Canale', 'Data',
            'Pos. fiscale', 'Cliente', 'Ordine',
            'Cod. Pag.', 'Desc. Pag.', 'Totale',
            'Tipo', 'Agente',
            ]

        width = [
            6, 10, 15,
            20, 30, 25,
            10, 10, 20,
            10, 10,
            ]

        format_text = False  # Load when create first sheet!
        for ws_name in pages:
            excel_pool.create_worksheet(ws_name)

            # ----------------------------------------------------------------------------------------------------------
            # Format setup:
            # ----------------------------------------------------------------------------------------------------------
            if not format_text:
                excel_pool.set_format()
                format_text = {
                    'title': excel_pool.get_format('title'),
                    'header': excel_pool.get_format('header'),
                    'text': excel_pool.get_format('text'),
                    'number': excel_pool.get_format('number'),
                    'total': excel_pool.get_format('text_total'),
                    'red': excel_pool.get_format('text_red'),
                }

            excel_pool.column_width(ws_name, width)
            row = 0
            excel_pool.write_xls_line(ws_name, row, header, default_format=format_text['header'])
            excel_pool.autofilter(ws_name, row, 0, row, len(header) - 1)
            excel_pool.freeze_panes(ws_name, 4, 1)

            total = 0.0  # final total

            # Partial management:
            partial = 0.0
            previous_mode = False

            # ----------------------------------------------------------------------------------------------------------
            # Sort record:
            # ----------------------------------------------------------------------------------------------------------
            if ws_name == 'Corrispettivo':
                sorted_records = sorted(
                    pages[ws_name],
                    # Canale, Pagamento, Importo
                    key=lambda x: (pages[ws_name][x][1][3], pages[ws_name][x][1][9])
                )
            elif ws_name == 'B2C':
                sorted_records = sorted(
                    pages[ws_name],
                    # Pos. fiscale, Pagamento, Importo
                    key=lambda x: (pages[ws_name][x][1][2], pages[ws_name][x][1][9], pages[ws_name][x][0])
                )
            elif ws_name == 'B2B SEPA':
                sorted_records = sorted(
                    pages[ws_name],
                    key=lambda x: pages[ws_name][x][1][1]
                )
            else:  # ws_name == 'B2B RID 14 gg':
                sorted_records = sorted(
                    pages[ws_name],
                    key=lambda x: pages[ws_name][x][1][1]
                )

            # ----------------------------------------------------------------------------------------------------------
            # Write record lines:
            # ----------------------------------------------------------------------------------------------------------
            for order in sorted_records:
                row += 1
                subtotal, line = pages[ws_name][order]
                mode = line[1]

                total += subtotal
                partial += subtotal

                if previous_mode == False:
                    previous_mode = mode

                # ------------------------------------------------------------------------------------------------------
                # Check partial:
                # ------------------------------------------------------------------------------------------------------
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
                    mode,      # Mode
                    line[3],   # Channel
                    line[4],   # Date
                    line[2],   # Fiscal position
                    line[5],   # Customer
                    order,
                    line[9],   # Payment code
                    payment_terms.get(line[9], ''), # Payment desc.
                    subtotal,  # Subtotal
                    line[13],  # Type
                    line[14],  # Agent
                    ], default_format=format_color)
            row += 1

            # ----------------------------------------------------------------------------------------------------------
            # check last partial:
            # ----------------------------------------------------------------------------------------------------------
            if previous_mode:  # always present
                # Write partial
                excel_pool.write_xls_line(ws_name, row, [
                    'Parziale %s:' % previous_mode, partial,
                    ], default_format=format_text['total'], col=7)
                row += 1

            excel_pool.write_xls_line(ws_name, row, ['Totale', total], format_text['total'], col=7)

        return excel_pool.return_attachment(filename)


    @api.multi
    def fees_extract_button(self):
        """ Account fees report ["Estrai corrispettivi" Button]
        """
        stock_pool = self.env['stock.picking']
        stock_pool.csv_report_extract_accounting_fees(evaluation_date=self.evaluation_date, team_id=self.team_id.id)

    @api.multi
    def fees_extract_api_button(self):
        """ Force API call for account fees send ["Estrai corrispettivi API" Button]
        """
        stock_pool = self.env['stock.picking']
        stock_pool.csv_report_extract_accounting_fees(
            evaluation_date=self.evaluation_date, team_id=self.team_id.id, mode='API')

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
