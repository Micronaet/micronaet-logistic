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
import mimetypes
import pdb

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import http, api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
from odoo.http import request
import urllib.parse

# from tyres_auto_confirm.cron.auto_print.print_auto_confirmed import company_pool

_logger = logging.getLogger(__name__)

# ======================================================================================================================
#                                                 END POINT
# ======================================================================================================================
class StockPFUDownload(http.Controller):
    """ Add End point to download created document
    """
    @http.route('/tyres_pfu_extract/download/<path:filename>', type='http', auth="user")
    def download_pdf_file(self, filename, **kw):
        """ Download generated PFU file from Filesystem
        """
        # Decode filename:
        decoded_filename = urllib.parse.unquote_plus(filename)

        company_pool = request.env['res.company']
        companys = company_pool.sudo().search([])
        company = companys[0]
        pfu_folder = company._logistic_folder('PFU')
        fullname = os.path.join(pfu_folder, decoded_filename)
        if not os.path.exists(fullname):
            return request.not_found()

        try:
            mimetype, _ = mimetypes.guess_type(fullname)
            if not mimetype:
                mimetype = 'application/octet-stream'  # Generic MIME Type

            with open(fullname, 'rb') as f:
                file_content = f.read()

            headers = [
                ('Content-Type', mimetype),
                ('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(fullname)),
                ('Content-Length', len(file_content)),
            ]
            return request.make_response(file_content, headers)
        except Exception as e:
            return request.not_found(description='Errore nel download del file: {}'.format(e))


class AccountFiscalPosition(models.Model):
    """ Model name: AccountFiscalPosition
    """
    _inherit = 'account.fiscal.position'

    is_pfu = fields.Boolean('PFU refund',
        help='If checked all sale with this position go in report')

class StockPfuDocument(models.Model):
    """ Model name: Stock.PFU.document
    """
    _name = 'stock.pfu.document'
    _description = 'PFU Document'
    _order = 'date desc'
    _rec_name = 'filename'

    # todo remove action that remove also linked movement and remove also pfu_done information!
    @api.multi
    def unlink(self):
        """ Pre operation during delete file (assigned, restore undone quants and moves)
            File not removed for now
        """
        assigned_pool = self.env['stock.pfu.assigned']
        quant_pool = self.env['stock.picking.delivery.quant']
        move_pool = self.env['stock.move']

        quant_ids = []
        move_ids = []

        # For all file passed:
        _logger.info('Remove Excel files: # {}'.format(
            len(self)))

        for file in self:
            file_id = file.id
            # Search assigned linked to that file and collect:
            assigned_obj = assigned_pool.search([('file_id', '=', file_id)])

            for assigned in assigned_obj:
                quant_ids.append(assigned.quant_id.id)
                move_ids.append(assigned.move_id.id)

            # Delete assigned records:
            _logger.info('Remove assigned record linked to file {}: # {}'.format(
                file.filename,
                len(assigned_obj),
            ))
            assigned_obj.unlink()

        # --------------------------------------------------------------------------------------------------------------
        # Restore flag for not done full assigned:
        # --------------------------------------------------------------------------------------------------------------
        _logger.info('Mark as undone # {} quants credit'.format(len(quant_ids)))
        quant_pool.browse(quant_ids).write({'pfu_done': False})

        _logger.info('Mark as undone # {} sale debit'.format(len(move_ids)))
        move_pool.browse(move_ids).write({'pfu_done': False})

        _logger.info('Delete real record')
        return super(StockPfuDocument, self).unlink()

    @api.multi
    def return_filename_excel(self):
        """ Return file Excel generated
        """
        filename = self.filename
        download_url = '/tyres_pfu_extract/download/{}'.format(urllib.parse.quote_plus(filename))
        _logger.info('Generating return URL: {}'.format(download_url))

        try:
            # Return filename:
            return {
                'type': 'ir.actions.act_url',
                'url': download_url,
                'target': 'self',  # 'new'
            }
        except:
            _logger.error('Error opening Download file URL: {}'.format(download_url))
        return True

    date = fields.Date('Data', required=True)
    filename = fields.Char('Filename', size=180)
    user_id = fields.Many2one('res.users', 'Utente')


class StockPfuAssigned(models.Model):
    """ Model name: Stock.PFU.Assigned
    """
    _name = 'stock.pfu.assigned'
    _description = 'PFU Assigned'
    _order = 'date'

    # filename = fields.Char('Filename', size=100)
    quant_id = fields.Many2one(
        'stock.picking.delivery.quant', 'Carico', required=True,
        help='Carico di magazzino collegato')
    delivery_id = fields.Many2one('stock.picking.delivery', 'Doc. di carico', related='quant_id.order_id', store=True)
    supplier_id = fields.Many2one('res.partner', 'Fornitore', related='delivery_id.supplier_id', store=True)
    file_id = fields.Many2one('stock.pfu.document', 'File Excel')
    move_id = fields.Many2one('stock.move', 'Riga di carico', help='Riga ordine collegata al carico', required=True)
    product_qty = fields.Float('Quant.', digits=(16, 2), required=True)
    date = fields.Datetime('Data', required=True)
    alternative = fields.Boolean('Prod. alternativo')


class ResCompanyInherit(models.Model):
    """ Parameter
    """
    _inherit = 'res.company'

    pfu_debug = fields.Boolean(
        'Schede Debug', default=True, help='Aggiunte delle schede extra al file per informazioni di debug')
    pfu_month = fields.Integer(
        'Mesi PFU', default=6,
        help='Mesi per prendere in considerazione i carichi da magazzino interno, il report parte da -X mesi per '
             'le vendite e -X mesi fino a -1 mese per gli acquisti')


class StockPickingDeliveryQuantInherit(models.Model):
    """ Add relations to PFU
    """
    _inherit = 'stock.picking.delivery.quant'

    @api.multi
    def get_assigned_pfu_qty(self):
        """ Total PFU assigned to line
        """
        for record in self:
            record.assigned_pfu_qty = sum([r.product_qty for r in record.assigned_pfu_ids])

    assigned_pfu_ids = fields.One2many('stock.pfu.assigned', 'quant_id', 'Assegnazioni')
    assigned_pfu_qty = fields.Float('PFU totale assegnato', compute='get_assigned_pfu_qty')
    pfu_done = fields.Boolean(
        'PFU completo', help='Indica se la riga di carico ha ancora disponibilità o è stata usata tutta')


class StockMoveInherit(models.Model):
    """ Add relations to PFU
    """
    _inherit = 'stock.move'

    @api.multi
    def get_assigned_pfu_qty(self):
        """ Total PFU assigned to line
        """
        for record in self:
            record.assigned_pfu_qty = sum([r.product_qty for r in record.assigned_pfu_ids])

    assigned_pfu_ids = fields.One2many('stock.pfu.assigned', 'move_id', 'Assegnazioni')
    assigned_pfu_qty = fields.Float('PFU totale assegnato', compute='get_assigned_pfu_qty')
    pfu_done = fields.Boolean(
        'PFU completo', help='Indica se la riga ha ancora degli assegnamenti pendenti o è completa')

class StockPickingPfuExtractWizard(models.TransientModel):
    """ Model name: StockPicking
    """
    _name = 'stock.picking.pfu.extract.wizard'
    _description = 'Logistic manual operation'

    # ------------------------------------------------------------------------------------------------------------------
    #                            COLUMNS:
    # ------------------------------------------------------------------------------------------------------------------
    mode = fields.Selection([
        ('extra', 'Extra Italia'),
        ('internal', 'Da magazzino interno'),
        ], string='Modalità', default='extra', required=True)

    partner_id = fields.Many2one('res.partner', 'Fornitore', domain="[('supplier', '=', True)]")
    from_date = fields.Date('Dalla data >=')
    to_date = fields.Date('Alla data <')
    # ------------------------------------------------------------------------------------------------------------------

    @api.model
    def get_data_domain(self, from_date, to_date):
        return [
            # Header
            ('delivery_id.date', '>=', from_date),
            ('delivery_id.date', '<', to_date),

            ('logistic_load_id', '!=', False), # Linked to order
            ('logistic_load_id.order_id.logistic_source', 'not in', ('refund', )),  # Not refund
            ]

    @api.multi
    def extract_fiscal_excel_pfu_report(self, ):
        """ Button event: Extract fiscal report
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

        # --------------------------------------------------------------------------------------------------------------
        #                           Collect data:
        # --------------------------------------------------------------------------------------------------------------
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

    # ------------------------------------------------------------------------------------------------------------------
    # Utility:
    # ------------------------------------------------------------------------------------------------------------------
    @api.model
    def get_ipcode(self, supplier, product, ipcode_cache):
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

    @api.multi
    def extract_excel_pfu_company_report(self, ):
        """ Button event: Extract fiscal report from internal Stock
        """
        # Pool used:
        quant_pool = self.env['stock.picking.delivery.quant']
        move_pool = self.env['stock.move']
        excel_pool = self.env['excel.writer']
        assign_pool = self.env['stock.pfu.assigned']
        company_pool = self.env['res.company']

        # --------------------------------------------------------------------------------------------------------------
        # Setup date range:
        # --------------------------------------------------------------------------------------------------------------
        now_dt = datetime.now()
        now_text = str(now_dt)
        now_filename = str(now_text).replace(':', '').replace('-', '').replace(' ', '_').replace('.', '_')
        filename = 'PFU_{}.xlsx'.format(now_filename)
        companys = company_pool.search([])
        company = companys[0]
        pfu_folder = company._logistic_folder('PFU')
        fullname = os.path.join(pfu_folder, filename)

        # Create reference file:
        file_object = file_pool.create({
            'filename': filename,
            'date': now_text[:19],
            'user_id': self.env.user.id
            })
        file_id = file_object.id

        # Parameter from setup in Company
        period = company.pfu_month or 6
        debug_mode = company.pfu_debug

        this_month_start = now_dt.replace(day=1)
        sale_start = (this_month_start - relativedelta(months=period - 1)).strftime('%Y-%m-%d')  # -6 month
        # purchase_start = (this_month_start - relativedelta(months=period - 2)).strftime('%Y-%m-%d')  # -7 month

        purchase_start = sale_start # -6 month
        # -1 month (not used last month purchase, need FT ref.):
        purchase_end = (this_month_start - relativedelta(days=1)).strftime('%Y-%m-%d')

        title = 'Periodo stampa PFU: Vendite [{} - OGGI] Acquisti [{} - {}]'.format(
            sale_start, purchase_start, purchase_end,
            )
        _logger.warning(title)
        _logger.info('File PFU: {}'.format(fullname))

        # --------------------------------------------------------------------------------------------------------------
        #                           Collect data purchase stock load records:
        # --------------------------------------------------------------------------------------------------------------
        domain = [
            ('pfu_done', '=', False),  # Not completed

            # Delivery order range:
            ('order_id.date', '>=', purchase_start),
            ('order_id.date', '<=', purchase_end),
            # ('sale_order_id.logistic_source', 'not in', ('refund',)),  # Not refund
        ]

        # Collected data for product quants available
        quants_available = {}
        quants = sorted(quant_pool.search(domain), key=lambda x: x.create_date)
        _logger.warning('Found # {} quants'.format(len(quants)))
        for quant in quants:  # Last in First out
            if quant.sale_order_id and quant.sale_order_id.logistic_source == 'refund':  # Jump refund
                continue

            product = quant.product_id
            sku = product.default_code or ''
            if sku not in quants_available:
                quants_available[sku] = []
            available_qty = quant.product_qty - sum([r.product_qty for r in quant.assigned_pfu_ids])

            # Exclude all used:
            if available_qty <= 0:
                quant.pfu_done = True
                continue

            # Collect available quants:
            quants_available[sku].append([
                quant,
                quant.order_id.supplier_id,
                available_qty,  # Dispo available
                product,
            ])

        # --------------------------------------------------------------------------------------------------------------
        #                           Collect data from stock move:
        # --------------------------------------------------------------------------------------------------------------
        _logger.info('Start searching open PFU lines from date {}'.format(sale_start))
        domain = [
            # PFU not completed:
            ('pfu_done', '=', False),

            # Date Range:
            ('logistic_load_id.order_id.date_order', '>=', '{} 00:00:00'.format(sale_start)),
            # <= today

            # Purchased with partner for internal stock:
            ('logistic_purchase_id.order_id.partner_id.internal_stock', '=', True),  # Only partner that load int. Stock

            # Order filter:
            ('logistic_load_id', '!=', False), # Linked to order
            ('logistic_load_id.order_id.partner_invoice_id.property_account_position_id.is_pfu', '=', True),
            ('logistic_load_id.order_id.logistic_source', 'not in', ('refund', )),  # Not refund
        ]

        # A. All stock move sale
        extra_data = {
            'error': [],  # Error with PFU category
            'excluded': [],  # Not PFU move
            'uncovered': [],  # No quants to cover
            # 'pending': [],  # Not covered all
            'done': [],  # Yet covered all
        }
        supplier_category_move = {}
        moves = move_pool.search(domain)
        if not moves:
            raise exceptions.Warning('Nessun movimento nel periodo -{} mesi'.format(period))

        _logger.warning('Found # {} sale Extra from Interal stock lines'.format(len(moves)))
        for move in moves:
            # Check quantity covered:
            move_id = move.id
            product = move.product_id
            try:
                category = product.mmac_pfu.name or ''
            except:
                extra_data['error'].append(move_id)
                continue

            if not category:  # Missed category product not in report
                extra_data['excluded'].append(move_id)
                continue

            # ----------------------------------------------------------------------------------------------------------
            # X00 management:
            # ----------------------------------------------------------------------------------------------------------
            sku_real = product.default_code or ''

            if sku_real[-3:-2].upper() == 'X' and sku_real[-2:].isdigit():  # X00 Managed
                sku_alternative = sku_real[:-3]
                if sku_real not in quants_available and sku_alternative not in quants_available:
                    extra_data['uncovered'].append(move_id)
                    continue
                sku_loop = [(sku_real, False), (sku_alternative, False)]

            else:
                if sku_real not in quants_available:
                    extra_data['uncovered'].append(move_id)
                    continue
                sku_loop = [(sku_real, False)]

            # Loop for original product but also for alternative product if present:
            move_qty = move.product_uom_qty
            need_qty = move_qty - sum([r.product_qty for r in move.assigned_pfu_ids])

            # Check if yet covered:
            if need_qty <= 0:
                move.pfu_done = True
                extra_data['done'].append(move_id)
                continue  # Next product

            # ----------------------------------------------------------------------------------------------------------
            # Loop for check product and alternative product:
            # ----------------------------------------------------------------------------------------------------------
            status = 'uncovered'  # Nothing was assigned (default)
            for sku, alternative in sku_loop:
                if sku not in quants_available:
                    # Case X22 not present but without X22 is present
                    continue

<<<<<<< HEAD
                this_stock = product_cover_list[0]  # ID, supplier_id, q.
                found_quant, found_supplier, found_qty = this_stock
                if need_qty < found_qty:  # More than needed (not equal)
                    used_qty = need_qty
                    this_stock[2] -= need_qty
                    need_qty = 0
                else:  # Use all found, less/equal than needed
                    used_qty = found_qty
                    need_qty -= found_qty
                    found_quant.pfu_done = True  # No mode used
                    product_cover_list.pop(0)  # Remove first element

                # Create assign record:
                assign_pool.create({
                    'filename': filename,
                    'quant_id': found_quant.id,
                    # 'supplier_id'
                    'move_id': move_id,
                    'product_qty': used_qty,
                    'date': now_text,
                })
=======
                product_cover_list = quants_available[sku]
>>>>>>> pfu_internal_report

                # ------------------------------------------------------------------------------------------------------
                # Assign stock quant master loop:
                # ------------------------------------------------------------------------------------------------------
                while need_qty > 0:  # Loop when need qty present
                    if not product_cover_list:   # Covered all in previous loop (or empty)
                        break

                    this_stock = product_cover_list[0]  # ID, supplier_id, q. (take the first of the stack)
                    found_quant, found_supplier, found_qty, quant_product = this_stock
                    if need_qty < found_qty:  # More than needed (not equal)
                        used_qty = need_qty
                        this_stock[2] -= need_qty
                        need_qty = 0
                    else:  # Use all found, less/equal than needed
                        used_qty = found_qty
                        need_qty -= found_qty
                        found_quant.pfu_done = True  # No mode used
                        product_cover_list.pop(0)  # Remove first element

                    # Create assign record:
                    assign_pool.create({
                        'file_id': file_id,
                        # 'filename': filename,  # todo remove
                        'quant_id': found_quant.id,
                        # 'supplier_id'
                        'move_id': move_id,
                        'product_qty': used_qty,
                        'date': now_text,
                        'alternative': alternative,
                    })
                    status = 'partial'  # Not uncovered (something was assigned)

                    # --------------------------------------------------------------------------------------------------
                    #                             Prepare record for Excel:
                    # --------------------------------------------------------------------------------------------------
                    if found_supplier not in supplier_category_move:
                        supplier_category_move[found_supplier] = {}
                    if category not in supplier_category_move[found_supplier]:
                        supplier_category_move[found_supplier][category] = []
                    supplier_category_move[found_supplier][category].append((move, used_qty, found_quant, alternative))

                    # Exit check:
                    if need_qty <= 0:
                        move.pfu_done = True  # Mark as covered all
                        status = 'all'

            if status == 'uncovered':
                extra_data['uncovered'].append(move_id)  # continue on next move

        # --------------------------------------------------------------------------------------------------------------
        #                                              EXTRACT EXCEL:
        # --------------------------------------------------------------------------------------------------------------
        # Excel file configuration:
        header = (
            'RAEE', 'Cod. Articolo', 'Cod. Forn.', 'Descrizione', u'Q.tà',
            'Doc Fornitore', 'Data Doc.', 'N. Fattura', 'N. Nostra fattura',
            'Data Doc.', 'ISO stato', 'Alt.',)

        column_width = (
            5, 15, 15, 45, 5,
            15, 12, 12, 15,
            10, 8, 8
            )

        # ---------------------------------------------------------------------
        # Write detail:
        # ---------------------------------------------------------------------
        ipcode_cache = {}
        format_text = {}  # For initial setup:
        page_created = {}
        for supplier in sorted(supplier_category_move, key=lambda x: x.name):
            ws_name = supplier.name.strip()

            # -----------------------------------------------------------------
            # Excel sheet creation:
            # -----------------------------------------------------------------
            if ws_name in page_created:
                page_created[ws_name] += 1
                ws_name = '{} ({})'.format(ws_name, page_created[ws_name])
            else:
                page_created[ws_name] = 0

            excel_pool.create_worksheet(ws_name)
            excel_pool.column_width(ws_name, column_width)
            if not format_text:  # First page only:
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
                u'Vendite [{} - OGGI] Acquisti [{} - {}]'.format(
                    sale_start,
                    purchase_start,
                    purchase_end
                ),
                ], default_format=format_text['title'])

            row += 2
            excel_pool.write_xls_line(ws_name, row, header, default_format=format_text['header'])
            excel_pool.autofilter(ws_name, row, 0, row, len(header) - 1)

            total = 0
            for category in sorted(supplier_category_move[supplier]):
                subtotal = 0

                for move, qty, quant, alternative in sorted(
                        supplier_category_move[supplier][category], key=lambda x: x[0].date):
                    row += 1

                    # Readability:
                    order = move.logistic_load_id.order_id
                    partner = order.partner_invoice_id
                    product = move.product_id

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
                        self.get_ipcode(supplier, product, ipcode_cache),  # ipcode
                        product.name_extended,  # name,
                        (qty, format_text['number']),  # todo check if it's all
                        quant.order_id.name,  # Delivery ref.
                        quant.order_id.date,
                        '',  # Number supplier invoice
                        invoice_number,  # Our invoice
                        invoice_date[:10],  # Date doc,
                        partner.country_id.code or '??',  # ISO country
                        'X' if alternative else '',
                        ), default_format=format_text['text'])
                row += 1
                excel_pool.write_xls_line(ws_name, row, (subtotal, ), default_format=format_text['number'], col=3)

            # -----------------------------------------------------------------
            # Write data line:
            # -----------------------------------------------------------------
            # Total
            row += 1
            excel_pool.write_xls_line(ws_name, row, ('Totale:', total, ), default_format=format_text['number'], col=2)

        # --------------------------------------------------------------------------------------------------------------
        #                                      Extra pages:
        # --------------------------------------------------------------------------------------------------------------
        if debug_mode:
            # ----------------------------------------------------------------------------------------------------------
            # 1. Available from stock
            # ----------------------------------------------------------------------------------------------------------
            # Excel file configuration:
            header = (
                'Prodotto', 'Descrizione', 'Fornitore', 'Bolla Fornitore', 'Data', 'Q. disponibile')

            column_width = (
                20, 30, 30, 20, 12, 10
                )

            ws_name = u'Dispo tot. da Mag. int.'
            excel_pool.create_worksheet(ws_name)

            if not format_text:  # First page only:
                excel_pool.set_format()
                format_text = {
                    'title': excel_pool.get_format('title'),
                    'header': excel_pool.get_format('header'),
                    'text': excel_pool.get_format('text'),
                    'number': excel_pool.get_format('number'),
                }

            row = 0
            excel_pool.write_xls_line(ws_name, row, header, default_format=format_text['header'])
            excel_pool.column_width(ws_name, column_width)
            excel_pool.autofilter(ws_name, row, 0, row, len(header) - 1)

            for sku in quants_available:
                for quant, supplier, available, product in quants_available[sku]:
                    delivery = quant.order_id

                    row += 1
                    excel_pool.write_xls_line(ws_name, row, (
                        product.default_code,
                        self.get_ipcode(supplier, product, ipcode_cache),  # ipcode
                        # product.name_extended,  # name,
                        supplier.name or '',
                        delivery.name,  # Delivery ref.
                        delivery.date,
                        (available, format_text['number']),
                        '',  # Number supplier invoice
                    ), default_format=format_text['text'])

            # ----------------------------------------------------------------------------------------------------------
            # 2 and after: Log data pages:
            # ----------------------------------------------------------------------------------------------------------
            pages = {
                # 'error': u'[Errore Cat. PFU]',
                'excluded': u'[Movimenti esclusi da PFU]',  # Not PFU move
                'uncovered': u'[Vendite non coperte]',  # No quants to cover
                # 'pending': u'[Partialmente coperti]',  # Not covered all
                'done': u'[Coperti in precedenza]',  # Yet covered all
            }

            # Excel file configuration:
            header = (
                'RAEE', 'Fornitore', 'Cod. Articolo', 'Cod. Forn.', 'Descrizione', u'Q.tà', u'Residuo',
                'Doc Fornitore', 'Data Doc.', 'N. Fattura', 'N. Nostra fattura',
                'Data Doc.', 'ISO stato')

            column_width = (
                5, 30, 15, 15, 45, 5, 5,
                15, 12, 12, 15,
                10, 8,
                )

            for page in pages:
                # ------------------------------------------------------------------------------------------------------
                # Excel sheet creation:
                # ------------------------------------------------------------------------------------------------------
                ws_name = pages[page]
                excel_pool.create_worksheet(ws_name)
                excel_pool.column_width(ws_name, column_width)

                # Header write:
                row = 0
                excel_pool.write_xls_line(ws_name, row, header, default_format=format_text['header'])

                for move in move_pool.browse(extra_data[page]):  # Reload Move from IDs
                    # Readability:
                    product = move.product_id
                    category = product.mmac_pfu.name or ''
                    order = move.logistic_load_id.order_id
                    partner = order.partner_invoice_id
                    supplier = move.logistic_load_id.order_id.partner_id

                    # Get invoice reference:
                    invoice_date = ''
                    invoice_number = ''
                    for invoice in order.logistic_picking_ids:
                        invoice_date = invoice.invoice_date or ''
                        invoice_number = invoice.invoice_number or ''
                        if invoice_number:
                            break  # Stop when find one invoice!
                        else:
                            invoice_number = u'No fatt.: %s' % order.name

                    # ---------------------------------------------------------
                    # Write data line:
                    # ---------------------------------------------------------
                    row += 1
                    move_qty = move.product_uom_qty
                    remain_qty = move_qty - sum([r.product_qty for r in move.assigned_pfu_ids])  # move.assigned_pfu_qty
                    excel_pool.write_xls_line(ws_name, row, (
                        category,  # product.mmac_pfu.name,
                        '',
                        product.default_code,
                        self.get_ipcode(supplier, product, ipcode_cache),  # ipcode
                        product.name_extended,  # name,
                        (move_qty, format_text['number']),
                        (remain_qty, format_text['number']),
                        move.delivery_id.name,  # Delivery ref.
                        move.delivery_id.date,
                        '',  # Number supplier invoice
                        invoice_number,  # Our invoice
                        invoice_date[:10],  # Date doc,
                        partner.country_id.code or '??',  # ISO country
                        ), default_format=format_text['text'])

        # ---------------------------------------------------------------------
        # Save file:
        # ---------------------------------------------------------------------
        _logger.info('Exporting Excel: {}'.format(fullname))
        excel_pool.save_file_as(fullname)   # return excel_pool.return_attachment('Report_PFU')

        try:
            # Return filename:
            download_url = '/tyres_pfu_extract/download/{}'.format(urllib.parse.quote_plus(filename))
            _logger.info('Generating return URL: {}'.format(download_url))

            return {
                'type': 'ir.actions.act_url',
                'url': download_url,
                'target': 'self',  # 'new'
            }
        except:
            # Return file generated:
            _logger.info('Return Excel File: {}'.format(fullname))
            return file_object.return_filename_excel()

    @api.multi
    def extract_excel_pfu_report(self, ):
        """ Button event: Extract Excel PFU report
        """
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

        # --------------------------------------------------------------------------------------------------------------
        #                           Collect data:
        # --------------------------------------------------------------------------------------------------------------
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

        # --------------------------------------------------------------------------------------------------------------
        #                          EXTRACT EXCEL:
        # --------------------------------------------------------------------------------------------------------------
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
        setup_complete = False  # For initial setup:
        for supplier in sorted(supplier_category_move, key=lambda x: x.name):
            ipcode_cache = {}
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
                        self.get_ipcode(supplier, product, ipcode_cache),  # ipcode
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
