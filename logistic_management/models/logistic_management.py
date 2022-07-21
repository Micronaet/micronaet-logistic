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
import pdb
import sys
import logging
import odoo
from odoo import api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """ Model name: Res Company
    """

    _inherit = 'res.company'

    # -------------------------------------------------------------------------
    # Parameters:
    # -------------------------------------------------------------------------
    # Database structure:
    _logistic_folder_db = {
            'ddt': {
                'default': ('DDT', 'Originali'),
                'history': ('DDT', 'Storico'),
                'supplier': ('DDT', 'Fornitori'),
                'daily': ('DDT', 'Giornalieri')
                },

            'invoice': {
                'default': ('Invoice', 'Originali'),
                'history': ('Invoice', 'Storico'),
                'xml': ('Invoice', 'XML'),
                },

            'bf': {
                'default': 'BF',
                },

            'images': {
                'default': 'images',
                },

            'corrispettivi': {
                'default': 'Corrispettivi',
                }
            }

    # Get path name:
    @api.model
    def _logistic_folder(self, document, mode='default', extra=False):
        """ Return full path of folder request:
        """
        # Get master path:
        folder_block = self._logistic_folder_db[document][mode]

        # Manage extra path:
        if extra:
            if type(extra) == str:
                extra = [extra]
            elif type(extra) == tuple:
                extra = list(extra)
            folder_block = list(folder_block).extend(extra)
        return self.get_subfolder_from_root(folder_block)

    @api.model
    def get_subfolder_from_root(self, name):
        """ Get subfolder from root
            if str only one folder, instead multipath
        """
        try:
            if type(name) == str:
                name = (name, )
            folder = os.path.expanduser(
                os.path.join(self.logistic_root_folder, *name))

            # Create in not present
            os.system('mkdir -p %s' % folder)
        except:
            raise odoo.exceptions.Warning(
                _('Error creating output folder (check param)'))
        return folder

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    # Logistic parameters:
    logistic_assign_mode = fields.Selection([
        ('first_available', 'First available'),
        # ('better_available', 'Better available'),
        ], 'Assign stock mode', default='first_available',
        help='Assign stock mode to order line (first available or better)',
        required=True,
        )
    logistic_order_sort = fields.Selection([
        ('create_date', 'Create date'),
        ('validity_date', 'Validity date'),
        ], 'Order sort', default='create_date',
        help='Sort order to assign stock availability',
        required=True,
        )
    logistic_location_id = fields.Many2one(
        'stock.location', 'Stock Location IN',
        help='Stock location for q. created',
        required=True,
        )

    # Pick type for load / unload:
    logistic_pick_in_type_id = fields.Many2one(
        'stock.picking.type', 'Pick in type',
        help='Picking in type for load documents',
        required=True,
        )
    logistic_pick_out_type_id = fields.Many2one(
        'stock.picking.type', 'Pick out type',
        help='Picking in type for unload documents',
        required=True,
        )
    logistic_root_folder = fields.Text(
        'Output root folder',
        help='Master root folder for output',
        required=True,
        )

    unificate_period = fields.Float(
        'Unificate period H.', default=24,
        help='Check order before hours selected for unification process',
        )


class ProductTemplate(models.Model):
    """ Template add fields
    """
    _inherit = 'product.template'

    @api.model
    def _get_root_image_folder(self):
        """ Use filestrore folder and subfolder images
        """
        company_pool = self.env['res.company']
        companys = company_pool.search([])
        return companys[0]._logistic_folder('images')

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    is_expence = fields.Boolean('Expense product',
        help='Expense product is not order and produced')
    is_refund = fields.Boolean('Refund product',
        help='Refund product use for mark value for total')


class PurchaseOrder(models.Model):
    """ Model name: Sale Order
    """

    _inherit = 'purchase.order'

    # -------------------------------------------------------------------------
    #                           UTILITY:
    # -------------------------------------------------------------------------
    @api.model
    def return_purchase_order_list_view(self, purchase_ids):
        """ Return purchase order tree from ids
        """
        model_pool = self.env['ir.model.data']
        tree_view_id = form_view_id = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase order selected:'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'purchase.order',
            'view_id': tree_view_id,
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('id', 'in', purchase_ids)],
            'context': self.env.context,
            'target': 'current',
            'nodestroy': False,
            }

    @api.model
    def check_order_confirmed_done(self, purchase_ids=None):
        """ Check passed purchase IDs passed or all confirmed order
            if not present
        """

        if purchase_ids:
            purchases = self.browse(purchase_ids)
        else:
            purchases = self.search([('logistic_state', '=', 'confirmed')])

        for purchase in purchases:
            done = True

            for line in purchase.order_line:
                if line.logistic_undelivered_qty > 0:
                    done = False
                    break
            # Update if all line hasn't undelivered qty
            if done:
                purchase.logistic_state = 'done'
        return True

    # -------------------------------------------------------------------------
    #                            BUTTON:
    # -------------------------------------------------------------------------
    @api.multi
    def open_purchase_line(self):
        """ Open purchase line detail view:
        """
        model_pool = self.env['ir.model.data']
        tree_view_id = model_pool.get_object_reference(
            'logistic_management', 'view_purchase_order_line_tree')[1]
        form_view_id = model_pool.get_object_reference(
            'logistic_management', 'view_purchase_order_line_form')[1]

        line_ids = [item.id for item in self.order_line]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase line'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'res_id': 1,
            'res_model': 'purchase.order.line',
            'view_id': tree_view_id,
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('id', 'in', line_ids)],
            'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    # Workflow button:
    @api.multi
    def set_logistic_state_confirmed(self):
        """ Set order as confirmed
        """
        # Export if needed the purchase order:
        self.export_purchase_order()
        now = fields.Datetime.now()

        return self.write({
            'logistic_state': 'confirmed',
            'date_planned': now,
            })

    # -------------------------------------------------------------------------
    #                                COLUMNS:
    # -------------------------------------------------------------------------
    logistic_state = fields.Selection([
        ('draft', 'Order draft'),  # Draft purchase
        ('confirmed', 'Confirmed'),  # Purchase confirmed
        ('done', 'Done'),  # All loaded in stock
        ], 'Logistic state', default='draft',
        )


class PurchaseOrderLine(models.Model):
    """ Model name: Purchase Order Line
    """

    _inherit = 'purchase.order.line'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    # RELATIONAL FIELDS:
    logistic_sale_id = fields.Many2one(
        'sale.order.line', 'Link to generator',
        help='Link generator sale order line: one customer line=one purchase',
        index=True, ondelete='set null',
        )


class StockMoveIn(models.Model):
    """ Model name: Stock Move
    """

    _inherit = 'stock.move'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    # TODO Need index?
    # USED STOCK: Linked used
    # Moved in stock.quant:
    #logistic_assigned_id = fields.Many2one(
    #    'sale.order.line', 'Link covered to generator',
    #    help='Link to sale line the assigned qty',
    #    index=True, ondelete='cascade',  # remove stock move when delete order
    #    )

    # Direct link to sale order line (generated from purchase order):
    logistic_refund_id = fields.Many2one(
        'sale.order.line', 'Link refund to sale',
        help='Link pick refund line to original sale line',
        index=True, ondelete='set null',
        )

    # Direct link to sale order line (generated from purchase order):
    logistic_load_id = fields.Many2one(
        'sale.order.line', 'Link load to sale',
        help='Link pick in line to original sale line (bypass purchase)',
        index=True, ondelete='set null',
        )

    # DELIVER: Pick out
    logistic_unload_id = fields.Many2one(
        'sale.order.line', 'Link unload to sale',
        help='Link pick out line to sale order',
        index=True, ondelete='set null',
        )

    # SUPPLIER ORDER: Purchase management:
    logistic_purchase_id = fields.Many2one(
        'purchase.order.line', 'Link load to purchase',
        help='Link pick in line to generat purchase line',
        index=True, ondelete='set null',
        )

    # LOAD WITHOUT SUPPLIER: Load management:
    logistic_quant_id = fields.Many2one(
        'stock.quant', 'Stock quant',
        help='Link to stock quant generated (load / unoad data).',
        index=True, ondelete='cascade',
        )


class PurchaseOrderLine(models.Model):
    """ Model name: Purchase Order Line
    """

    _inherit = 'purchase.order.line'

    # -------------------------------------------------------------------------
    # Function fields:
    # -------------------------------------------------------------------------
    #@api.depends('load_line_ids', )
    @api.multi
    def _get_logistic_status_field(self):
        """ Manage all data for logistic situation in sale order:
        """
        _logger.warning('Update logistic qty fields now')
        for line in self:
            logistic_delivered_qty = 0.0
            for move in line.load_line_ids:
                logistic_delivered_qty += move.product_uom_qty
            # Generate data for fields:
            line.logistic_delivered_qty = logistic_delivered_qty
            line.logistic_undelivered_qty = \
                line.product_qty - logistic_delivered_qty

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    # COMPUTED:
    logistic_delivered_qty = fields.Float(
        'Delivered qty', digits=dp.get_precision('Product Price'),
        help='Qty delivered with load documents',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )
    logistic_undelivered_qty = fields.Float(
        'Undelivered qty', digits=dp.get_precision('Product Price'),
        help='Qty undelivered, remain to load',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )

    # TODO logistic state?

    # RELATIONAL:
    load_line_ids = fields.One2many(
        'stock.move', 'logistic_purchase_id', 'Linked load to purchase',
        help='Load linked to this purchase line',
        )


class StockPicking(models.Model):
    """ Model name: Stock picking
    """

    _inherit = 'stock.picking'

    # -------------------------------------------------------------------------
    # Override function
    # -------------------------------------------------------------------------
    # XXX Override original procedure un l18n_it_fatturapa:
    @api.multi
    def fatturapa_get_details(self):
        """ Extract line detail sumary
        """
        self.ensure_one()
        picking = self[0]

        # Result dict:
        detail_table = {}
        vat_table = {}
        ddt_reference = {}
        # todo order?

        # XXX Always present and one only!
        ddt_number = (picking.ddt_number or '').split('/')[-1]
        ddt_date = picking.ddt_date

        i = 0
        for move in picking.move_lines_for_report():
            # Parameters:
            price = float(move[7])  # price_reduce from sale order line
            qty = float(move[1])  # q. from sale order line
            subtotal = float(move[9])
            vat = move[3].amount
            subtotal_vat = float(move[10]) - subtotal  # XXX check approx!
            name = move[16].name

            # -----------------------------------------------------------------
            # Detail data:
            # -----------------------------------------------------------------
            i += 1
            # todo remove from here: self.qweb_format_float(
            detail_table[str(i)] = {
                'mode': '',  # No mode = product line (else SC, PR, AB, AC)
                'discount': '',  # No discount
                'nature': '',  # No nature (always 22)
                'product': move[0],  # Browse
                'price': self.qweb_format_float(price, decimal=6),
                'qty': self.qweb_format_float(qty),
                'vat': self.qweb_format_float(vat),  # %
                'retention': '',  # No retention
                'subtotal': self.qweb_format_float(subtotal),  # VAT excluded
                'name': name,
                }

            # -----------------------------------------------------------------
            # Vat data:
            # -----------------------------------------------------------------
            if vat in vat_table:
                vat_table[vat][0] += subtotal
                vat_table[vat][1] += subtotal_vat
            else:
                vat_table[vat] = [
                    subtotal,  # Subtotal
                    subtotal_vat,  # VAT total
                    '',  # Nature
                    '',  # Extra expense
                    '',  # Round
                    ]

            # -----------------------------------------------------------------
            # DDT reference:
            # -----------------------------------------------------------------
            if ddt_number in ddt_reference:
                ddt_reference[ddt_number][0].append(str(i))
            else:
                ddt_reference[ddt_number] = [
                    [str(i), ], ddt_date]

        # TODO remove from here format float
        for vat in vat_table:
            vat_table[vat][0] = self.qweb_format_float(vat_table[vat][0])
            vat_table[vat][1] = self.qweb_format_float(vat_table[vat][1])
        return detail_table, vat_table, ddt_reference

    @api.multi
    def refund_confirm_state_event(self):
        """ Confirm operation (will be overrided)
        """
        # Confirm document and export in files:
        self.workflow_ready_to_done_done_picking()
        return True

    # -------------------------------------------------------------------------
    # Extract Excel:
    # -------------------------------------------------------------------------
    @api.model
    def excel_report_extract_accounting_fees(self, evaluation_date=False):
        """ Extract file account fees
        """
        # Pool used:
        excel_pool = self.env['excel.writer']
        company_pool = self.env['res.company']

        companys = company_pool.search([])
        fees_path = companys[0]._logistic_folder('corrispettivi')

        # Period current date:
        if evaluation_date: # use evaluation
            now_dt = datetime.strptime(evaluation_date, '%Y-%m-%d')
        else:  # use now
            now_dt = datetime.now()
        _logger.warning('Account Fees evalutation: %s' % now_dt)

        from_date = now_dt.strftime('%Y-%m-01')
        now_dt += relativedelta(months=1)
        to_date = now_dt.strftime('%Y-%m-01')

        # Picking not invoiced (DDT and Refund):
        pickings = self.search([
            # Period:
            ('ddt_date', '>=', from_date),
            ('ddt_date', '<', to_date),

            # Not invoiced (only DDT):
            ('ddt_number', '!=', False),
            # ('invoice_number', '=', False),
            ])

        # ---------------------------------------------------------------------
        # Collect picking grouped by fiscal position:
        # ---------------------------------------------------------------------
        fiscal_pickings = {
            'Fatturato': [],
        }
        for picking in pickings:
            if picking.invoice_number:
               fiscal_pickings['Fatturato'].append(picking)
               continue  # No page creation

            try:
                fiscal_position = picking.sale_order_id.fiscal_position_id
                country_code = fiscal_position.country_id.code
                ws_name = 'Pos. {}'.format(country_code or 'senza codice')
            except:
                ws_name = 'Pos. non trovata'
            if ws_name not in fiscal_pickings:
                fiscal_pickings[ws_name] = []
                excel_pool.create_worksheet(ws_name)
            fiscal_pickings[ws_name].append(picking)

        # Add extra sheet for manage remain invoice (last page):
        ws_invoice = 'Fatturato'
        excel_pool.create_worksheet(ws_invoice)

        # ---------------------------------------------------------------------
        # Format:
        # ---------------------------------------------------------------------
        excel_pool.set_format()
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        f_text_black = excel_pool.get_format('text')
        f_text_red = excel_pool.get_format('text_red')
        f_number_black = excel_pool.get_format('number')
        f_number_red = excel_pool.get_format('number_red')
        # f_green_text = excel_pool.get_format('bg_green')
        # f_yellow_text = excel_pool.get_format('bg_yellow')
        # f_green_number = excel_pool.get_format('bg_green_number')
        # f_yellow_number = excel_pool.get_format('bg_yellow_number')

        # ---------------------------------------------------------------------
        # Setup page: Fatturato
        # ---------------------------------------------------------------------
        excel_pool.column_width(ws_invoice, [
            15, 15, 25, 15, 15,
            20, 30, 25,
            10, 10, 10,
            ])

        row_invoice = 0
        excel_pool.write_xls_line(ws_invoice, row_invoice, [
             'Fatture del periodo: [%s - %s]' % (from_date, to_date)
             ], default_format=f_title)

        row_invoice += 1
        excel_pool.write_xls_line(ws_invoice, row_invoice, [
             'Data', 'Data X', 'Ordine', 'Picking', 'Stato',
             'Fattura', 'Cliente', 'Posizione fiscale',
             'Imponibile', 'IVA', 'Totale',
             ], default_format=f_header)

        total_invoice = {
            'amount': 0.0,
            'vat': 0.0,
            'total': 0.0,
            }

        # ---------------------------------------------------------------------
        # Setup page: Corrispettivo
        # ---------------------------------------------------------------------
        fees_header = [
             'Data', 'Data X', 'Ordine', 'Picking', 'Stato',
             'Cliente', 'Posizione fiscale',
             'Imponibile', 'IVA', 'Totale',
             ]

        for ws_name in fiscal_pickings:
            # Setup WS
            excel_pool.column_width(ws_name, [
                15, 15, 25, 15, 15, 30, 25,
                10, 10, 10,
            ])

            row = 0
            excel_pool.write_xls_line(ws_name, row, [
                'Corrispettivi %s del periodo: [%s - %s]' % (
                    ws_name, from_date, to_date)
            ], default_format=f_title)

            row += 1
            excel_pool.write_xls_line(
                ws_name, row, fees_header, default_format=f_header)

            # Reset total for every page / fiscal position:
            total = {
                'amount': 0.0,
                'vat': 0.0,
                'total': 0.0,
            }
            for picking in fiscal_pickings[ws_name]:
                # Readability:
                order = picking.sale_order_id
                partner = order.partner_id
                stock_mode = picking.stock_mode  # in: refund, out: DDT

                if stock_mode == 'in':
                    sign = -1.0
                    f_number = f_number_red
                    f_text = f_text_red
                else:
                    f_number = f_number_black
                    f_text = f_text_black
                    sign = +1.0

                subtotal = { # common subtotal
                    'amount': 0.0,
                    'vat': 0.0,
                    'total': 0.0,
                    }

                if picking.invoice_number:
                    row_invoice += 1
                    for move in picking.move_lines_for_report():
                        # Total without VAT:
                        subtotal['amount'] += sign * float(move[9])
                        # VAT Total:
                        subtotal['vat'] += sign * float(move[6])
                        # Total with VAT
                        subtotal['total'] += sign * float(move[10])

                    # Update total:
                    total_invoice['amount'] += subtotal['amount']
                    total_invoice['vat'] += subtotal['vat']
                    total_invoice['total'] += subtotal['total']

                    excel_pool.write_xls_line(ws_invoice, row_invoice, (
                        picking.ddt_date,
                        order.x_ddt_date,
                        picking.ddt_number if stock_mode == 'in' else
                        order.name,
                        picking.name,
                        '' if stock_mode == 'in' else order.logistic_state,
                        picking.invoice_number,
                        partner.name,
                        partner.property_account_position_id.name,
                        (subtotal['amount'], f_number),
                        (subtotal['vat'], f_number),
                        (subtotal['total'], f_number),
                        ), default_format=f_text)

                else:  # No invoice:
                    row += 1
                    for move in picking.move_lines_for_report():
                        # Total without VAT:
                        subtotal['amount'] += sign * float(move[9])
                        # VAT Total
                        subtotal['vat'] += sign * float(move[6])
                        # Total with VAT
                        subtotal['total'] += sign * float(move[10])

                    # Update total:
                    total['amount'] += subtotal['amount']
                    total['vat'] += subtotal['vat']
                    total['total'] += subtotal['total']

                    excel_pool.write_xls_line(ws_name, row, (
                        picking.ddt_date,
                        order.x_ddt_date,
                        picking.ddt_number if stock_mode == 'in' else
                        order.name,
                        picking.name,
                        '' if stock_mode == 'in' else order.logistic_state,
                        partner.name,
                        partner.property_account_position_id.name,  # Fiscal p.
                        (subtotal['amount'], f_number),
                        (subtotal['vat'], f_number),
                        (subtotal['total'], f_number),
                        ), default_format=f_text)

            # -----------------------------------------------------------------
            # Totals:
            # -----------------------------------------------------------------
            if ws_name != 'Fatturato':
                # 1. Corrispettivi:
                row += 1
                excel_pool.write_xls_line(ws_name, row, (
                    'Totali:',
                    (total['amount'], f_number_black),
                    (total['vat'], f_number_black),
                    (total['total'], f_number_black),
                    ), default_format=f_header, col=6)

        # 2. Invoice:
        row_invoice += 1
        excel_pool.write_xls_line(ws_invoice, row_invoice, (
            'Totali:',
            (total_invoice['amount'], f_number_black),
            (total_invoice['vat'], f_number_black),
            (total_invoice['total'], f_number_black),
            ), default_format=f_header, col=7)

        # ---------------------------------------------------------------------
        # Define filename and save:
        # ---------------------------------------------------------------------
        filename = os.path.join(fees_path, '%s_%s_corrispettivi.xlsx' % (
            from_date[:4], from_date[5:7]))
        excel_pool.save_file_as(filename)
        return True

    # -------------------------------------------------------------------------
    # Override path function:
    # -------------------------------------------------------------------------
    # Path: DDT, Invoice (module: logistic_account_report)
    @api.multi
    def get_default_folder_path(self):
        """ Override default extract DDT function:
        """
        companys = self.env['res.company'].search([])
        return companys[0]._logistic_folder('ddt')

    @api.multi
    def get_default_folder_invoice_path(self):
        """ Override default extract Invoice function:
        """
        companys = self.env['res.company'].search([])
        return companys[0]._logistic_folder('invoice')

    # Path: XML Invoice
    @api.multi
    def get_default_folder_xml_invoice(self):
        """ Override default extract XML Invoice
        """
        companys = self.env['res.company'].search([])
        return companys[0]._logistic_folder('invoice', 'xml')

    # -------------------------------------------------------------------------
    #                                   UTILITY:
    # -------------------------------------------------------------------------
    @api.model
    def qweb_format_float(self, value, decimal=2, length=10):
        """ Format float value
        """
        if type(value) != float:
            return value

        format_mask = '%%%s.%sf' % (length, decimal)
        return (format_mask % value).strip()

    # TODO Not used, remove?!?
    @api.model
    def workflow_ready_to_done_all_done_picking(self):
        """ Confirm draft picking documents
        """
        pickings = self.search([
            ('state', '=', 'draft'),
            # TODO out document! (),
            ])
        return pickings.workflow_ready_to_done_done_picking()

    # Export Excel file with loaded picking:
    @api.multi
    def export_excel_picking_report(self):
        """ Export excel picking data
            line
        """
        self.ensure_one()
        excel_pool = self.env['excel.writer']
        companys = self.env['res.company'].search([])
        folder = companys[0]._logistic_folder('bf')

        ws_name = 'Carichi'
        excel_pool.create_worksheet(ws_name)

        # ---------------------------------------------------------------------
        # Format:
        # ---------------------------------------------------------------------
        excel_pool.set_format()
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')

        f_white_text = excel_pool.get_format('text')
        f_green_text = excel_pool.get_format('bg_green')
        f_yellow_text = excel_pool.get_format('bg_yellow')

        f_white_number = excel_pool.get_format('number')
        f_green_number = excel_pool.get_format('bg_green_number')
        f_yellow_number = excel_pool.get_format('bg_yellow_number')

        # ---------------------------------------------------------------------
        # Setup page:
        # ---------------------------------------------------------------------
        excel_pool.column_width(ws_name, [
            20, 20, 20, 25, 10, 10, 20,
            ])

        # ---------------------------------------------------------------------
        # Extra data:
        # ---------------------------------------------------------------------
        now = fields.Datetime.now()

        # for picking in self:
        picking = self
        partner = picking.partner_id.name
        origin = picking.origin
        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            'Fornitore: %s Documento di origine: %s [%s]' % (
                partner,
                origin,
                now,
                )], default_format=f_title)
        row += 1
        excel_pool.write_xls_line(ws_name, row, [
             'Foto', 'Codice', 'Nome', 'Ordine', 'Stato', 'Q.', 'Posizione'
             ], default_format=f_header)
        for move in picking.move_lines:
            row += 1
            product = move.product_id
            template = product.product_tmpl_id
            sale_line = move.logistic_load_id
            order = sale_line.order_id
            if order:
                if order.logistic_state == 'pending':
                    f_text = f_yellow_text
                    f_number = f_yellow_number
                else: # done
                    f_text = f_green_text
                    f_number = f_green_number
                slot_name = move.slot_id.name

            else:
                f_text = f_white_text
                f_number = f_white_number
                slot_name = product.default_slot_id.name \
                    if product.default_slot_id else 'Manca per il prodotto'

            excel_pool.write_xls_line(ws_name, row, [
                 '',
                 template.default_code,
                 template.name,

                 order.name if order else _('MAGAZZINO'),
                 order.logistic_state if order else '',

                 (move.product_uom_qty, f_number),
                 slot_name,
                 ], default_format=f_text)

        # ---------------------------------------------------------------------
        # Save file:
        # ---------------------------------------------------------------------
        filename = 'BF_%s_%s.xlsx' % (
                partner,
                origin
                )
        filename = filename.replace(
            ':', '_').replace(' ', '').replace('[', '_').replace(']', '')
        # now = now.replace(':', '_').replace('-', '_')
        fullname = os.path.join(folder, filename)

        excel_pool.save_file_as(fullname)
        return True

    # -------------------------------------------------------------------------
    #                                   BUTTON:
    # -------------------------------------------------------------------------
    @api.multi
    def workflow_ready_to_done_done_picking(self):
        """ Confirm draft picking documents
        """
        # ---------------------------------------------------------------------
        # Confirm picking for DDT and Invoice:
        # ---------------------------------------------------------------------
        ddt_ids = []  # For extra operation after
        invoice_ids = []  # For extra operation after
        for picking in self:
            partner = picking.partner_id
            order = picking.sale_order_id
            if not order:
                _logger.error('Picking without order linked')

            # Need invoice check:
            need_invoice = order.fiscal_position_id.need_invoice or \
                partner.need_invoice

            # Assign always DDT number:
            picking.assign_ddt_number()
            ddt_ids.append(picking.id)

            # Invoice procedure (check rules):
            # 03/02/2022 Removed assign invoice number:
            # if need_invoice:
            #    picking.assign_invoice_number()
            #    invoice_ids.append(picking.id)

            picking.write({
                'state': 'done',  # TODO needed?
                })

        # ---------------------------------------------------------------------
        # DDT extra operations: (require reload)
        # ---------------------------------------------------------------------
        companys = self.env['res.company'].search([])
        folder = companys[0]._logistic_folder('ddt')
        history_folder = companys[0]._logistic_folder('ddt', 'history')
        supplier_folder = companys[0]._logistic_folder('ddt', 'supplier')
        daily_folder = companys[0]._logistic_folder('ddt', 'daily')

        # Reload picking data:
        for picking in self.browse(ddt_ids):
            sale_order = picking.sale_order_id
            # TODO Sanitize:
            supplier_name = \
                sale_order.default_supplier_id.name or 'NESSUNO'
            supplier_name = supplier_name.replace(' ', '')

            # -----------------------------------------------------------------
            #                 DDT Extract:
            # -----------------------------------------------------------------
            # 1. DDT Extract procedure:
            # -----------------------------------------------------------------
            original_fullname = picking.extract_account_ddt_report()

            # -----------------------------------------------------------------
            # 2. DDT Symlink procedure:
            # -----------------------------------------------------------------
            original_base = os.path.basename(original_fullname)

            # A. History folder:
            date = picking.scheduled_date
            month_path = os.path.join(history_folder, date[:4], date[5:7])
            os.system('mkdir -p %s' % month_path)
            symlink = os.system('ln -s "%s" "%s"' % (
                original_fullname,
                os.path.join(month_path, original_base)
                ))

            # B. Supplier folder:
            # TODO sanitize name!
            if supplier_name:  # NC no Supplier link!
                supplier_path = os.path.join(supplier_folder, supplier_name)
                os.system('mkdir -p %s' % supplier_path)
                symlink = os.system('ln -s "%s" "%s"' % (
                    original_fullname,
                    os.path.join(supplier_path, original_base)
                    ))
            else:
                _logger.warning('No supplier link generated!')

            # 3. DDT Print procedure:
            today = fields.Datetime.now()[:10].replace(
                '/', '_').replace('-', '_')
            daily_path = os.path.join(daily_folder, today)
            os.system('mkdir -p %s' % daily_path)
            symlink = os.system('ln -s "%s" "%s"' % (
                original_fullname,
                os.path.join(
                    daily_path,
                    '%s_%s' % (
                        supplier_name,
                        original_base,
                        )
                    )
                ))

        # ---------------------------------------------------------------------
        # Invoice extra operations: (require reload)
        # ---------------------------------------------------------------------
        folder = companys[0]._logistic_folder('invoice')
        history_folder = companys[0]._logistic_folder('invoice', 'history')

        '''
        # 03/02/2022: removed also Fattura PA:
        for picking in self.browse(invoice_ids):
            # =================================================================
            #                 Invoice Extract:
            # -----------------------------------------------------------------
            # 16/09/2021 No more printed from now:

            # 1. Invoice Extract procedure:
            # original_fullname = picking.extract_account_invoice_report()

            # 2. Invoice Symlink procedure:
            # original_base = os.path.basename(original_fullname)
            # date = picking.scheduled_date
            # month_path = os.path.join(history_folder, date[:4], date[5:7])
            # os.system('mkdir -p %s' % month_path)
            # symlink = os.system('ln -s "%s" "%s"' % (
            #    original_fullname,
            #    os.path.join(month_path, original_base)
            #    ))
            # =================================================================

            # 3. Invoice Print procedure:
            # todo

            # 4. Extract electronic invoice:
            
            # picking.extract_account_electronic_invoice()
        '''

    @api.model
    def move_lines_for_report_total(self):
        """ Generate Total collect data for report purposes
        """
        self.ensure_one()

        res = {
            'total': 0.0,  # net + vat
            'net': 0.0,
            'vat': 0.0,

            'vat_text': '',  # VAT description
            }

        for line in self.move_lines_for_report():
            print(line)
            if not res['vat_text'] and line[3]:
                res['vat_text'] = line[3].name

            net = float(line[9])
            total = float(line[10])
            res['total'] += total
            res['net'] += net
            res['vat'] += total - net

        for key in res:
            if key != 'vat_text':
                res[key] = self.qweb_format_float(res[key])
        return res

    @api.model
    def get_refund_product_price(self, line):
        """ Generate 3 use data:
            Tax, Unit net, Net, VAT, Total for product refund passed in line
        """
        product = line.product_id
        partner = self.partner_id
        position = partner.property_account_position_id

        taxes = product.taxes_id[0]  # product
        for replace in position.tax_ids:
            if replace.tax_src_id == taxes:
                taxes = replace.tax_dest_id
        vat_rate = taxes.amount
        q = line.product_uom_qty
        total = line.price_unit * q
        if vat_rate:
            net = (total * 100.0) / (100.0 + vat_rate)
            vat = total - net
        else:
            vat = 0
            net = total

        # Tax obj, Unit price net, Net total, VAT total, Total amount
        return taxes[0], net / q if q else 0.0, net, vat, total

    @api.model
    def move_lines_for_report(self):
        """ Generate a list of record depend on OC, KIT and 2 substitution mode
            Return list of: product, line
        """
        self.ensure_one()

        refund_line = {}  # Move line with refund product
        res = []
        kit_add = []  # Kit yet added
        last_order = False
        sorted_lines = sorted(self.move_lines, key=lambda x: (
            x.logistic_unload_id.unification_origin_id,
            x.id,
            ))
        if not sorted_lines:
            return res

        # DDT or RC header text:
        header_picking = sorted_lines[0].picking_id
        ddt_reference = _('%s del %s') % (
            sorted_lines[0].picking_id.ddt_number,
            sorted_lines[0].picking_id.ddt_date,
            )

        # total = []
        refund_kit = []  # Kit will be printed once!
        for line in sorted_lines:
            move_product = line.product_id
            picking = line.picking_id
            # 28/06/2022 introducing new approx decimal on unit price:
            # > Approx 2 to 6 after this date
            if picking.create_date >= '2022-06-28':
                approx_unit = 6
            else:
                approx_unit = 2

            if picking.stock_mode == 'in':  # Refund
                if move_product.is_refund:
                    refund_line[line] = self.get_refund_product_price(line)
                # Kit component?
                if line.logistic_refund_id.kit_line_id:
                    if line.logistic_refund_id.kit_line_id not in refund_kit:
                        sale_line = line.logistic_refund_id.kit_line_id
                        refund_kit.append(line.logistic_refund_id.kit_line_id)
                    else:
                        continue  # Kit yet printed
                else:  # Product line
                    sale_line = line.logistic_refund_id

            else:  # DDT:
                sale_line = line.logistic_unload_id

            if sale_line.kit_line_id:
                # Kit exploded line not used:
                continue

            # Similar / Alternative case:
            quantity = int(sale_line.product_uom_qty)
            if line in refund_line:
                original_product = move_product
                replaced_product = False
                quantity = int(line.product_uom_qty)
            elif sale_line.origin_product_id:
                original_product = sale_line.origin_product_id
                replaced_product = sale_line.product_id
            else:
                original_product = sale_line.product_id
                replaced_product = False

            # Use move product if not present original:
            if not original_product:
                original_product = move_product

            # -----------------------------------------------------------------
            # Order reference:
            # -----------------------------------------------------------------
            if not sale_line.unification_origin_id:  # Merged
                current_order = picking.sale_order_id
            else:  # Original:
                current_order = sale_line.unification_origin_id

            if not last_order or current_order != last_order:
                last_order = current_order
                write_order = '%s del %s' % (
                    current_order.name,
                    current_order.date_order,
                    )
            else:
                write_order = ''

            # -----------------------------------------------------------------
            # Line record:
            # -----------------------------------------------------------------
            # Extract if present refund 3 total (used for force)
            (refund_tax, refund_unit_net, refund_net, refund_vat, refund_total
             ) = refund_line.get(line, (False, False, False, False, False))

            res.append((
                original_product,  # 0. Product browse
                quantity,  # 1. XXX Note: Not stock.move q
                replaced_product,  # 2. Replaced product

                # todo price_subtotal (use stock.move or sale.order.line?
                refund_tax or sale_line.tax_id,  # XXX 3. Sale tax

                # -------------------------------------------------------------
                # Unit:
                # -------------------------------------------------------------
                self.qweb_format_float(
                    sale_line.price_unit, decimal=approx_unit,
                    ),  # 4. Unit no discount
                self.qweb_format_float(
                    sale_line.price_reduce, decimal=approx_unit,
                    ),  # 5. Unit discounted
                refund_vat or self.qweb_format_float(
                    sale_line.price_tax, decimal=2,
                    ),  # XXX 6. VAT Total

                # -------------------------------------------------------------
                # Price net price:
                # -------------------------------------------------------------
                # XXX 7. Unit no VAT
                refund_unit_net or self.qweb_format_float(
                    sale_line.price_reduce_taxexcl, decimal=approx_unit),
                # 8. Unit+VAT=price_unit-red
                self.qweb_format_float(
                    sale_line.price_reduce_taxinc, decimal=approx_unit),

                # -------------------------------------------------------------
                # Total:
                # -------------------------------------------------------------
                refund_net or self.qweb_format_float(
                    sale_line.price_subtotal),  # XXX 9. Tot without VAT
                refund_total or self.qweb_format_float(
                    sale_line.price_total),  # XXX 10. Tot With VAT

                # -------------------------------------------------------------
                # Amount invoiced:
                # -------------------------------------------------------------
                self.qweb_format_float(
                    sale_line.amt_to_invoice),  # 11. Not used
                self.qweb_format_float(
                    sale_line.amt_invoiced),  # 12. Not used

                # Discount (XXX not used):
                self.qweb_format_float(
                    sale_line.discount),  # 13. not used for now

                write_order,  # 14
                ddt_reference,  # 15
                sale_line,  # 16 For every extra reference
                ))
            ddt_reference = ''  # only first line print DDT reference
        _logger.warning('>>> Picking line: %s ' % (res, ))
        _logger.warning(res)
        return res

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    sale_order_id = fields.Many2one(
        'sale.order', 'Sale order', help='Sale order generator')


class ResPartner(models.Model):
    """ Model name: Res Partner
    """

    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    need_invoice = fields.Boolean('Always invoice')
    # sql_customer_code = fields.Char('SQL customer code', size=20)
    # sql_supplier_code = fields.Char('SQL supplier code', size=20)


class AccountFiscalPosition(models.Model):
    """ Model name: Account Fiscal Position
    """

    _inherit = 'account.fiscal.position'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    need_invoice = fields.Boolean('Always invoice')


class StockQuant(models.Model):
    """ Model name: Stock quant
    """

    _inherit = 'stock.quant'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    logistic_assigned_id = fields.Many2one(
        'sale.order.line', 'Link covered to generator',
        help='Link to sale line the assigned qty',
        index=True, ondelete='cascade',  # remove stock move when delete order
        )


class SaleOrder(models.Model):
    """ Model name: Sale Order
    """

    _inherit = 'sale.order'

    # -------------------------------------------------------------------------
    #                           BUTTON EVENTS:
    # -------------------------------------------------------------------------
    # Extra operation before WF
    @api.multi
    def return_order_line_list_view(self):
        """ Return order line in a tree view
        """
        line_ids = self[0].order_line.mapped('id')
        return self.env['sale.order.line'].return_order_line_list_view(
            line_ids)

    # -------------------------------------------------------------------------
    #                           UTILITY:
    # -------------------------------------------------------------------------
    @api.multi  # XXX not api.one?!?
    def logistic_check_and_set_ready(self):
        """ Check if all line are in ready state (excluding unused)
        """
        order_ids = []
        for order in self:
            line_state = set(order.order_line.mapped('logistic_state'))
            line_state.discard('unused')  # remove kit line (exploded)
            line_state.discard('done')  # if some line are in done (multidelivery)
            if tuple(line_state) == ('ready', ): # All ready
                order.write({
                    'logistic_state': 'ready',
                    })
                order_ids.append(order.id)
        _logger.warning('Closed because ready # %s order' % len(order_ids))
        return order_ids

    @api.multi
    def logistic_check_and_set_delivering(self):
        """ Check if all line are in done state (excluding unused)
        """
        for order in self:
            line_state = set(order.order_line.mapped('logistic_state'))
            line_state.discard('unused') # remove kit line (exploded)
            if tuple(line_state) == ('done', ):  # All done
                order.write({
                    'logistic_state': 'delivering',  # XXX ex done
                    })
        return True

    # Extra operation before WF
    @api.model
    def return_order_list_view(self, order_ids):
        """ Utility for return selected order in tree view
        """
        tree_view_id = form_view_id = False
        _logger.info('Return order tree view [# %s]' % len(order_ids))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order confirmed'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'res_id': 1,
            'res_model': 'sale.order',
            'view_id': tree_view_id,
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('id', 'in', order_ids)],
            'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    @api.model
    def check_exploded_product_kit(self):
        """ Check if there's kit in product, launch explode operation
        """
        log_message = True # TODO change
        line_pool = self.env['sale.order.line']
        template_pool = self.env['product.template']

        lines = line_pool.search([
            ('order_id.logistic_state', '=', 'draft'),  # Draft order
            # '|', ('product_id.default_code', '=ilike', '%#%'),
            ('product_id.product_tmpl_id.default_code', '=ilike', '%#%'),  # Kit code
            # TODO replace with: ('is__kit', '=', True),
            ])
        _logger.info('New order: check explode kit [# %s]' % len(lines))

        template_ids = []  # ID of template checked
        update_ids = []  # ID of template updated
        for line in lines:
            template = line.product_id.product_tmpl_id
            if template.id in template_ids:
                continue
            template_ids.append(template.id)

            if '#' not in template.default_code: # Not a kit
                continue

            code_part = template.default_code.split('#')
            if len(code_part) != len(template.component_ids):
                try:
                    update_ids.append(template.id)
                    template.explode_kit_from_name()
                except:
                    pass
            else:
                template.is_kit = True

        # Reload product updated:
        templates = template_pool.browse(update_ids)  # Updated kit
        res = ''
        for template in templates:
            code_part = template.default_code.split('#')
            if len(code_part) != len(template.component_ids):
                res += '%s<br/>' % template.default_code

        if log_message and res:
            mail_pool = self.env['mail.thread']
            body = _(
                '''<div class="o_mail_notification">
                    Kit not correct exploded:<br/>
                    %s
                    </div>
                ''') % res

            mail_pool.sudo().message_post(
            #mail_pool.message_post(
                body=body,
                message_type='notification',
                subject=_('Kit not found'),
                )
        return True

    @api.model
    def check_product_first_supplier(self):
        """ Update product without first supplier:
        """
        log_message = True # TODO change
        line_pool = self.env['sale.order.line']
        template_pool = self.env['product.template']

        lines = line_pool.search([
            ('order_id.logistic_state', '=', 'draft'),  # Draft order
            ('product_id.default_supplier_id', '=', False),  # No first supplier
            ('product_id.is_kit', '=', False),  # No kit line
            ('product_id.type', '!=', 'service'),  # No service product
            ])
        _logger.info('New order: generate first supplier [# %s]' % len(lines))
        template_ids = []
        update_ids = []
        for line in lines:
            template = line.product_id.product_tmpl_id
            if template.id in template_ids:
                continue
            template_ids.append(template.id)
            try:
                update_ids.append(template.id)
                template.get_default_supplier_from_code()
            except:
                pass

        # Check updated record:
        templates = template_pool.search([
            ('id', 'in', update_ids),  # Updated lines:
            ('default_supplier_id', '=', False),  # Not updated
            ])
        res = ''
        for template in templates:
            res += '%s<br/>' % template.default_code

        if log_message and res:
            mail_pool = self.env['mail.thread']
            body = _(
                '''<div class="o_mail_notification">
                    First supplier not found:<br/>
                    %s
                    </div>''') % res

            mail_pool.sudo().message_post(
                body=body,
                message_type='notification',
                subject=_('Default supplier not found'),
                )
        return True

    def check_empty_orders(self):
        """ Mark empty order as unused
        """
        orders = self.search([
            ('logistic_state', '=', 'draft'),  # Insert order
            ('order_line', '=', False),  # Without line
            ])
        _logger.info('New order: Empty order [# %s]' % len(orders))

        return orders.write({
            'logistic_state': 'error',
            })

    def check_product_service(self):
        """ Update line with service to ready state
        """
        line_pool = self.env['sale.order.line']
        lines = line_pool.search([
            ('order_id.logistic_state', '=', 'draft'),  # Draft order
            ('logistic_state', '=', 'draft'),  # Draft line
            ('product_id.type', '=', 'service'),  # Direct ready
            ('product_id.is_expence', '=', True),  # Direct ready
            # ('kit_line_id', '=', False),  # Not the kit line (service = mrp)
            ])
        _logger.info('New order: Check product-service [# %s]' % len(lines))
        return lines.write({
            'logistic_state': 'ready',  # immediately ready
            })

    # Sale order mark default supplier:
    @api.model
    def mark_default_supplier_order(self, order_ids):
        """ Mark default supplier
        """
        for order in self.browse(order_ids):
            supplier_total = {}
            for line in order.order_line:
                product = line.product_id

                # -------------------------------------------------------------
                # No dropship clause (check before expence):
                # -------------------------------------------------------------
                # Internal = Company supplier: XXX not considered
                #if line.mrp_state:

                # -------------------------------------------------------------
                # Jump line:
                # -------------------------------------------------------------
                # Expence product: (service # TODO after only is_expence)
                if product.type == 'service' or product.is_expence:
                    continue

                # Kit line:
                if line.logistic_state == 'unused':
                    continue

                # -------------------------------------------------------------
                # Supplier check:
                # -------------------------------------------------------------
                supplier_id = product.default_supplier_id.id
                if supplier_id not in supplier_total:
                    supplier_total[supplier_id] = 1
                else:
                    supplier_total[supplier_id] += 1

            if supplier_total:
                better_supplier = sorted(
                    supplier_total,
                    key=lambda x: supplier_total[x], reverse=True,
                    )
                order.default_supplier_id = better_supplier[0]
        return True

    @api.model
    def sale_order_unificate_same_partner(self, order_touched_ids):
        """ Unifcate procedure if order has yet present order for same partner
        """
        from datetime import datetime, timedelta

        company_pool = self.env['res.company']
        unificate_period_min = company_pool.search(
            [])[0].unificate_period * 60.0

        from_period = (datetime.utcnow() - timedelta(
            minutes=unificate_period_min)).strftime('%Y-%m-%d %H:%M:%S')

        moved_ids = []
        for order in self.browse(order_touched_ids):
            order_destination = self.search([
                ('partner_id', '=', order.partner_id.id),  # This partner
                ('payment_term_id', '=', order.payment_term_id.id),  # Payment
                ('date_order', '>=', from_period),  # In period range
                ('logistic_state', 'in', ('pending', )),  # TODO other selection?
                ('id', '!=', order.id),  # Not this
                ('order_destination_id', '=', False),  # Not unificated
                ])

            if not order_destination:
                continue

            # TODO manage more than one warning?
            order_destination = order_destination[0] # Take first
            _logger.warning('Order linked: %s > %s' % (
                order.name,
                order_destination.name,
                ))

            # Setup for duplication:
            order.write({
                'order_destination_id': order_destination.id,
                'logistic_state': 'unificated',
                })

            moved_ids.append(order.id)

        # Run after for upadte process (destination field):
        for order in self.browse(moved_ids):
            order.migrate_to_destination_button()
        return True

    # -------------------------------------------------------------------------
    #                   WORKFLOW: [LOGISTIC OPERATION TRIGGER]
    # -------------------------------------------------------------------------
    # A. Logistic phase 1: Check secure payment:
    # -------------------------------------------------------------------------
    @api.model
    def force_workflow_draft_to_payment(self, order_ids):
        """ Call original action from externally
        """
        return self.with_context(force_order_ids=order_ids).workflow_draft_to_payment()

    # -------------------------------------------------------------------------
    # A. Logistic phase 1: Check secure payment:
    # -------------------------------------------------------------------------
    @api.model
    def workflow_draft_to_payment(self):
        """ Assign logistic_state to secure order
        """
        _logger.info('New order: Start analysis')
        # ---------------------------------------------------------------------
        #                               Pre operations:
        # ---------------------------------------------------------------------
        # Empty orders:
        _logger.info('Check: Mark error state for empty orders')
        self.check_empty_orders()  # Order without line

        # Payment article (not kit now):
        _logger.info('Check: Mark service line to ready (not worked product)')
        self.check_product_service()  # Line with service article (not used)

        # Explode kit if present (create also product service):
        _logger.info('Check: Explode product kit (if # in default_code)')
        self.check_exploded_product_kit()

        # Update supplier if present:
        _logger.info('Check: Generate first supplier if not present')
        self.check_product_first_supplier()

        # ---------------------------------------------------------------------
        # Start order payment check:
        # ---------------------------------------------------------------------
        domain = [
            ('logistic_state', '=', 'draft'),  # new order
            ]
        force_order_ids = self.env.context.get('force_order_ids')
        if force_order_ids:
            domain.append(('id', 'in', force_order_ids))
        orders = self.search(domain)
        _logger.info('New order: Selection [# %s]' % len(orders))

        # Search new order:
        payment_order = []
        for order in orders:
            # -----------------------------------------------------------------
            # 1. Marked as done (script or in form)
            # -----------------------------------------------------------------
            if order.payment_done:
                payment_order.append(order)
                continue

            # -----------------------------------------------------------------
            # 2. Secure market (sale team):
            # -----------------------------------------------------------------
            try:  # error if not present
                if order.team_id.secure_payment:
                    payment_order.append(order)
                    continue
            except:
                pass

            # -----------------------------------------------------------------
            # 3. Secure payment in fiscal position
            # -----------------------------------------------------------------
            try:  # problem in not present
                position = order.partner_id.property_account_position_id
                payment = order.payment_term_id
                if payment and payment in [
                        secure.payment_id for secure in position.secure_ids]:
                    payment_order.append(order)
                    continue
            except:
                pass

        # ---------------------------------------------------------------------
        # Update state: order >> payment
        # ---------------------------------------------------------------------
        select_ids = []
        for order in payment_order:
            select_ids.append(order.id)
            order.payment_done = True
            order.logistic_state = 'payment'

        # Return view tree:
        return self.return_order_list_view(select_ids)

    # -------------------------------------------------------------------------
    # B. Logistic phase 2: payment > order
    # -------------------------------------------------------------------------
    @api.model
    def force_workflow_payment_to_order(self, order_ids):
        """ Confirm payment order (before expand kit)
        """
        return self.with_context(force_order_ids=order_ids).workflow_payment_to_order()

    @api.model
    def workflow_payment_to_order(self):
        """ Confirm payment order (before expand kit)
        """
        domain = [
            ('logistic_state', '=', 'payment'),
            ]
        force_order_ids = self.env.context.get('force_order_ids')
        if force_order_ids:
            domain.append(('id', 'in', force_order_ids))
        orders = self.search(domain)
        selected_ids = []
        for order in orders:
            selected_ids.append(order.id)
            # A. Generate sub-elements from kit:
            order.explode_kit_in_order_line()

            # C. Became real order:
            order.logistic_state = 'order'

        # Update default supplier for exploded component:

        # Return view:
        return self.return_order_list_view(selected_ids)

    # State (sort of workflow):
    # TODO
    # dropshipping = fields.Boolean('Dropshipping',
    #    help='All order will be managed externally')

    # -------------------------------------------------------------------------
    # B. Logistic delivery phase: ready > done
    # -------------------------------------------------------------------------
    @api.model
    def force_workflow_ready_to_done_draft_picking(self, order_ids,  limit=False):
        """ Forced procedure: Confirm payment order (before expand kit)
        """
        return self.with_context(force_order_ids=order_ids).workflow_ready_to_done_draft_picking(limit=limit)

    @api.model
    def workflow_ready_to_done_draft_picking(self, limit=False):
        """ Confirm payment order (before expand kit)
        """
        now = fields.Datetime.now()

        # Pool used:
        picking_pool = self.env['stock.picking']
        move_pool = self.env['stock.move']
        company_pool = self.env['res.company']

        # ---------------------------------------------------------------------
        # Parameters:
        # ---------------------------------------------------------------------
        company = company_pool.search([])[0]
        logistic_pick_out_type = company.logistic_pick_out_type_id

        logistic_pick_out_type_id = logistic_pick_out_type.id
        location_from = logistic_pick_out_type.default_location_src_id.id
        location_to = logistic_pick_out_type.default_location_dest_id.id

        # ---------------------------------------------------------------------
        # Select order to prepare:
        # ---------------------------------------------------------------------
        domain = [
            ('logistic_state', '=', 'ready'),
            ]
        force_order_ids = self.env.context.get('force_order_ids')
        if force_order_ids:
            domain.append(('id', 'in', force_order_ids))

        if limit:
            _logger.warning('Limited export: %s' % limit)
            orders = self.search(domain, limit=limit)
        else:
            orders = self.search(domain)

        verbose_order = len(orders)

        # ddt_list = []
        # invoice_list = []
        picking_ids = []  # return value
        i = 0
        for order in orders:
            i += 1
            _logger.warning('Generate pick out from order: %s / %s' % (
                i, verbose_order))

            # Create picking document:
            partner = order.partner_id
            name = order.name  # same as order_ref
            origin = _('%s [%s]') % (order.name, order.create_date[:10])

            picking = picking_pool.create({
                'sale_order_id': order.id,  # Link to order
                'partner_id': partner.id,
                'scheduled_date': now,
                'origin': origin,
                # 'move_type': 'direct',
                'picking_type_id': logistic_pick_out_type_id,
                'group_id': False,
                'location_id': location_from,
                'location_dest_id': location_to,
                # 'priority': 1,
                'state': 'draft',  # XXX To do manage done phase (for invoice)!!
                })
            picking_ids.append(picking.id)

            for line in order.order_line:
                product = line.product_id

                # =============================================================
                # Speed up (check if yet delivered):
                # -------------------------------------------------------------
                # TODO check if there's another cases: service, kit, etc.
                if line.delivered_line_ids:
                    product_qty = line.logistic_undelivered_qty
                else:
                    product_qty = line.product_uom_qty

                # Update line status:
                line.write({'logistic_state': 'done', })
                # =============================================================

                # -------------------------------------------------------------
                # Create movement (not load stock):
                # -------------------------------------------------------------
                # TODO Check kit!!
                move_pool.create({
                    'company_id': company.id,
                    'partner_id': partner.id,
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'name': product.name or ' ',
                    'date': now,
                    'date_expected': now,
                    'location_id': location_from,
                    'location_dest_id': location_to,
                    'product_uom_qty': product_qty,
                    'product_uom': product.uom_id.id,
                    'state': 'done',
                    'origin': origin,
                    'price_unit': product.standard_price,

                    # Sale order line link:
                    'logistic_unload_id': line.id,

                    # group_id
                    # reference'
                    # sale_line_id
                    # procure_method,
                    #'product_qty': select_qty,
                    })
            # TODO check if DDT / INVOICE document:

        # ---------------------------------------------------------------------
        # Confirm picking (DDT and INVOICE)
        # ---------------------------------------------------------------------
        picking_pool.browse(picking_ids).workflow_ready_to_done_done_picking()

        # ---------------------------------------------------------------------
        # Order status:
        # ---------------------------------------------------------------------
        # Change status order ready > done
        orders.logistic_check_and_set_delivering()

        # Different return value if called with limit:
        if limit:
            _logger.warning('Check other order remain: %s' % limit)
            orders = self.search([
                ('logistic_state', '=', 'ready'),
                ], limit=limit) # keep limit instead of search all
            return orders or False

        return picking_ids

    # -------------------------------------------------------------------------
    # C. delivering > done
    # -------------------------------------------------------------------------
    @api.multi
    def wf_set_order_as_done(self):
        """ Set order as done (from delivering)
        """
        self.ensure_one()
        self.logistic_state = 'done'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    default_supplier_id = fields.Many2one(
        'res.partner', 'Default supplier', domain="[('supplier', '=', True)]")
    logistic_picking_ids = fields.One2many(
        'stock.picking', 'sale_order_id', 'Picking')

    logistic_state = fields.Selection([
        ('draft', 'Order draft'),  # Draft, new order received
        ('payment', 'Payment confirmed'),  # Payment confirmed

        # Start automation:
        ('order', 'Order confirmed'),  # Quotation transformed in order
        ('pending', 'Pending delivery'),  # Waiting for delivery
        ('ready', 'Ready'),  # Ready for transfer
        ('delivering', 'Delivering'),  # In delivering phase
        ('done', 'Done'),  # Delivered or closed XXX manage partial delivery
        ('dropshipped', 'Dropshipped'),  # Order dropshipped
        ('unificated', 'Unificated'),  # Unificated with another

        ('error', 'Error order'),  # Order without line
        ('cancel', 'Cancel'),  # Removed order
        ], 'Logistic state', default='draft',
        )


class SaleOrderLine(models.Model):
    """ Model name: Sale Order Line
    """

    _inherit = 'sale.order.line'

    # -------------------------------------------------------------------------
    #                           UTILITY:
    # -------------------------------------------------------------------------
    @api.model
    def logistic_check_ready_order(self, sale_lines=None):
        """ Mask as done sale order with all ready lines
            if not present find all order in pending state
        """
        order_pool = self.env['sale.order']
        if sale_lines:
            # Start from sale order line:
            order_checked = []
            for line in sale_lines:
                order = line.order_id
                if order in order_checked:
                    continue
                # Check sale.order logistic status (once):
                order.logistic_check_and_set_ready()
                order_checked.append(order)
        else:
            # Check pending order:
            orders = order_pool.search([('logistic_state', '=', 'pending')])
            return orders.logistic_check_and_set_ready()  # IDs order updated
        return True

    @api.model
    def return_order_line_list_view(self, line_ids):
        """ Return order line tree view (selected)
        """
        # Gef view
        model_pool = self.env['ir.model.data']
        tree_view_id = model_pool.get_object_reference(
            'logistic_management', 'view_sale_order_line_logistic_tree')[1]
        form_view_id = model_pool.get_object_reference(
            'logistic_management', 'view_sale_order_line_logistic_form')[1]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Updated lines'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'res_id': 1,
            'res_model': 'sale.order.line',
            'view_id': tree_view_id,
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('id', 'in', line_ids)],
            'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    # -------------------------------------------------------------------------
    #                           BUTTON EVENT:
    # -------------------------------------------------------------------------
    @api.multi
    def chain_broken_purchase_line(self):
        """ Order undo line:
            If product ordered to supplier not delivered or in late:
            1. Delete purchase line so unlinked the future delivery
            2. Order line will be reset to 'draft' mode (check assign)
            3. Order will be recheck when triggered
        """
        self.ensure_one()

        # Note: now it's not possibile, evaluate if necessary to reload
        # Stock with that qty:
        # 0. Has delivered Qty
        if self.load_line_ids:
            raise exceptions.UserError(
                _('Has delivered qty associated, cannot return!'))

        # 1. Unlink assigned q from stock:
        self.assigned_line_ids.unlink()

        # 2. Unlink purchase order line:
        for line in self.purchase_line_ids:
            # Log deleted reference in purchase order:
            message = _(
                ''' Customer order: %s
                    Product: [%s] %s
                    Q. removed: %s
                    ''' % (
                        self.order_id.name,
                        self.product_id.product_tmpl_id.default_code,
                        self.product_id.name,
                        line.product_qty,  # Q in order!
                        )
                )
            line.order_id.message_post(
                body=message, subtype='mt_comment')
        self.purchase_line_ids.unlink()

        # 3. Change line state and header:
        # Order will be remanaged when retrigger procedure!
        self.logistic_state = 'draft'
        self.order_id.logistic_state = 'order'
        return True

    @api.multi
    def open_view_sale_order(self):
        """ Open order view
        """
        # model_pool = self.env['ir.model.data']
        # view_id = model_pool.get_object_reference(
        #    'module_name', 'view_name')[1]
        view_id = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale order'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': self.order_id.id,
            'res_model': 'sale.order',
            # 'view_id': view_id,  # False
            'views': [(False, 'form'), (False, 'tree')],
            'domain': [('id', '=', self.order_id.id)],
            # 'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    @api.multi
    def open_view_sale_order_product(self):
        """ Open subsituted product
        """
        # model_pool = self.env['ir.model.data']
        # view_id = model_pool.get_object_reference(
        #    'module_name', 'view_name')[1]
        view_id = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Product detail'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': self.product_id.id,
            'res_model': 'product.product',
            # 'view_id': view_id,  # False
            'views': [(False, 'form'), (False, 'tree')],
            'domain': [('id', '=', self.product_id.id)],
            # 'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    @api.multi
    def open_view_sale_order_original_product(self):
        """ Open original product
        """
        # model_pool = self.env['ir.model.data']
        # view_id = model_pool.get_object_reference(
        #    'module_name', 'view_name')[1]
        view_id = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Product detail'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': self.origin_product_id.id,
            'res_model': 'product.product',
            # 'view_id': view_id,  # False
            'views': [(False, 'form'), (False, 'tree')],
            'domain': [('id', '=', self.origin_product_id.id)],
            # 'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    @api.multi
    def open_view_sale_order_kit_product(self):
        """ Open original product
        """
        view_id = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Product detail'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': self.kit_product_id.id,
            'res_model': 'product.product',
            #'view_id': view_id,  # False
            'views': [(False, 'form'), (False, 'tree')],
            'domain': [('id', '=', self.kit_product_id.id)],
            #'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    # -------------------------------------------------------------------------
    #                   WORKFLOW: [LAVORATION OPERATION TRIGGER]
    # -------------------------------------------------------------------------
    # A. Draft > Progress
    @api.multi
    def workflow_mrp_draft_to_progress(self):
        """ Update mrp_state
        """
        for line in self:
            self.mrp_state = 'progress'

    # B. Progress > Done
    def workflow_mrp_progress_to_done(self):
        """ Update mrp_state
        """
        line_pool = self.env['sale.order.line']

        #line_ids = []
        for line in self:
            #line_ids.append(line.id)
            line.mrp_state = 'done'

            # Update also logistic state to ready:
            line.logistic_state = 'ready'

        # Check master order (reload lines for updated status):
        #sale_lines = line_pool.browse(line_ids)
        line_pool.logistic_check_ready_order(self)#sale_lines)

    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    #                   WORKFLOW: [LOGISTIC OPERATION TRIGGER]
    # -------------------------------------------------------------------------
    # A. Assign available q.ty in stock assign a stock movement / quants
    @api.model
    def workflow_order_to_uncovered(self):
        """ Logistic phase 3:
            Assign stock q. available to order product creating a
            stock.move or stock.quant movement
            Evaluate also if we can use alternative product
        """
        now = fields.Datetime.now()

        product_pool = self.env['product.product']
        quant_pool = self.env['stock.quant']
        sale_pool = self.env['sale.order']
        lines = self.search([
            ('order_id.logistic_state', '=', 'order'),  # Logistic state
            ('logistic_state', '=', 'draft'),
            ])

        # ---------------------------------------------------------------------
        # Load parameter from company setup:
        # ---------------------------------------------------------------------
        if lines:
            # Access company parameter from first line
            company = lines[0].order_id.company_id

            location_id = company.logistic_location_id.id
            sort = company.logistic_order_sort
            mode = company.logistic_assign_mode

            _logger.info(
                'Update order with parameter: '
                'Location: %s, sort: %s, mode: %s' % (
                    location_id, sort, mode))
        else:
            _logger.info('No line ready for assign stock qty')
            return True

        # ---------------------------------------------------------------------
        # Parameter: Sort options:
        # ---------------------------------------------------------------------
        if sort == 'create_date':
            sorted_line = sorted(lines, key=lambda x:
                x.order_id.create_date)
        else: # validity_date
            sorted_line = sorted(lines, key=lambda x:
                x.order_id.validity_date or x.order_id.create_date)

        # ---------------------------------------------------------------------
        #                  Modify sale order line status:
        # ---------------------------------------------------------------------
        update_db = {} # Line to be updated
        #sale_line_ready = [] # To check if order also is ready

        # This fix a bug because stock status don't update immediately
        quant_used = {} # product quant used during process

        order_touched_ids = [] # For end operation (dropship, default suppl.)
        for line in sorted_line:
            # Update touched order list:
            if line.order_id.id not in order_touched_ids:
                order_touched_ids.append(line.order_id.id)

            product = line.product_id
            # -----------------------------------------------------------------
            # Kit line not used:
            # -----------------------------------------------------------------
            if not product or product.is_kit:
                update_db[line] = {
                    'logistic_state': 'unused',
                    }
                continue # Comment line

            order_qty = line.product_uom_qty

            # -----------------------------------------------------------------
            # Similar pool generate:
            # -----------------------------------------------------------------
            product_list = [product] # Start list first with this product
            if product.similar_ids:
                # Search other product from template list
                template_ids = [
                    template.id for template in product.similar_ids]
                similar_product = product_pool.search([
                    ('product_tmpl_id', 'in', template_ids),
                    ])
                product_list.extend([item for item in similar_product])

            # -----------------------------------------------------------------
            # Use stock to cover order:
            # -----------------------------------------------------------------
            state = False # Used for check if used some pool product
            for used_product in product_list: # p.p similar
                # XXX Remove used qty during assign process:
                # TODO problem if qty_qvailable dont update with quants created
                stock_qty = used_product.qty_available - \
                    quant_used.get(used_product, 0.0)

                # -------------------------------------------------------------
                # Manage mode of use stock: (TODO better available)
                # -------------------------------------------------------------
                assign_quantity = 0.0 # To check is was created
                if mode == 'first_available' and stock_qty:
                    if stock_qty > order_qty:
                        assign_quantity = order_qty
                        state = 'ready'
                        #sale_line_ready.append(line)
                    else:
                        assign_quantity = stock_qty
                        state = 'uncovered'

                    company = line.order_id.company_id # XXX
                    data = {
                        'company_id': company.id,
                        'in_date': now,
                        'location_id': location_id,
                        'product_id': used_product.id,
                        #'product_tmpl_id': used_product.product_tmpl_id.id,
                        #'lot_id' #'package_id'
                        'quantity': - assign_quantity,

                        # Link field:
                        'logistic_assigned_id': line.id,
                        }
                    try:
                        quant_pool.create(data)
                    except:
                        _logger.error('Product is service? [%s - %s]\n%s' % (
                            used_product.product_tmpl_id.default_code or '',
                            used_product.name,
                            sys.exc_info(),
                            ))
                        continue

                    # ---------------------------------------------------------
                    # Save used stock for next elements:
                    # ---------------------------------------------------------
                    if used_product in quant_used:
                        quant_used[used_product] += assign_quantity
                    else:
                        quant_used[used_product] = assign_quantity

                    # Update line if quant created
                    update_db[line] = {
                        'logistic_state': state,
                        }

                # -------------------------------------------------------------
                # TODO manage alternative product here!
                # -------------------------------------------------------------

                # -------------------------------------------------------------
                # Update similar product in order line (if used):
                # -------------------------------------------------------------
                if state and used_product != product:
                    # Update sale line with information:
                    update_db[line]['linked_mode'] = 'similar'
                    update_db[line]['origin_product_id'] = product.id
                    update_db[line]['product_id'] = used_product.id

                if assign_quantity:
                    break # no other product was taken

            # -----------------------------------------------------------------
            # No stock passed in uncovered state:
            # -----------------------------------------------------------------
            if line not in update_db:
                update_db[line] = {
                    'logistic_state': 'uncovered',
                    }

        # ---------------------------------------------------------------------
        # Update sale line state:
        # ---------------------------------------------------------------------
        selected_ids = [] # ID, to return view list
        selected_order = [] # Obj, to update master order status
        for line in update_db:
            line.write(update_db[line])
            selected_ids.append(line.id)
            if line.order_id not in selected_order:
                selected_order.append(line.order_id)

        # ---------------------------------------------------------------------
        #                          PARTICULAR CASES:
        # ---------------------------------------------------------------------
        # Note: Work only if start this procedure with data!
        pending_draft = self.search([
            ('order_id.logistic_state', '=', 'pending'),
            ('logistic_state', '=', 'draft'),
            ])
        if pending_draft:
            _logger.error(
                'Pending order with draft movements: %s' % len(pending_draft))
            for line in pending_draft:
                product = line.product_id

                # A. Kit must be unused state not draft:
                if product.is_kit:
                    line.logistic_state = 'unused'

                # B. Service must be ready (not kit)
                elif product.type == 'service':
                    line.logistic_state = 'ready'

                # C. Covered with stock: TODO

                # END: Add this order to the check state order:
                if line.order_id not in selected_order:
                    selected_order.append(line.order_id)

        # Note: Particular cases for line with standard procedure will be
        #       updata also order logistic state (see after):
        # ---------------------------------------------------------------------


        # ---------------------------------------------------------------------
        # Update order to ready / pending status:
        # ---------------------------------------------------------------------
        # TODO line_pool.logistic_check_ready_order(sale_line_ready)
        all_ready = set(['ready'])
        for order in selected_order:
            # Generate list of line state, jump not used:
            line_logistic_state = [
                line.logistic_state for line in order.order_line \
                    if line.logistic_state != 'unused']

            # -----------------------------------------------------------------
            # Update order state depend on all line:
            # -----------------------------------------------------------------
            if all_ready == set(line_logistic_state):
                order.logistic_state = 'ready'
            else: # All other order stay in pending state:
                order.logistic_state = 'pending'
            # TODO Manage Dropshipping!!


        # Sale order still in pending state so no update of logistic status
        # ---------------------------------------------------------------------
        # Mark sale order with extra information:
        # ---------------------------------------------------------------------
        # Dropshipping # TODO spostare da qui altrimenti crea l'ordine acquisto
        #sale_order.check_dropshipping_order(order_touched_ids)
        # TODO Mettere prima dell'assegnamento magazzino ed eventualmente n
        # non fare quello!!!!!!!!

        # Default supplier
        _logger.warning('Assign default supplier for order')
        sale_pool.mark_default_supplier_order(order_touched_ids)

        # Return view:
        return self.return_order_line_list_view(selected_ids)

    # A. Assign available q.ty in stock assign a stock movement / quants
    @api.model
    def workflow_uncovered_pending(self):
        """ Logistic phase 2:
            Order remain uncovered qty to the default supplier
            Generate purchase order to supplier linked to product
        """
        now = fields.Datetime.now()

        # ---------------------------------------------------------------------
        # Pool used:
        # ---------------------------------------------------------------------
        sale_pool = self.env['sale.order']
        purchase_pool = self.env['purchase.order']
        purchase_line_pool = self.env['purchase.order.line']

        # Note: Update only pending order with uncovered lines
        lines = self.search([
            # Filter logistic state:
            ('order_id.logistic_state', '=', 'pending'),

            # Filter line state:
            ('logistic_state', '=', 'uncovered'),

            # Not select lavoration line:
            ('mrp_state', '=', False),
            ])

        # ---------------------------------------------------------------------
        # Parameter from company:
        # ---------------------------------------------------------------------
        if lines:
            # Access company parameter from first line
            company = lines[0].order_id.company_id
        else:  # No lines found:
            return True

        # ---------------------------------------------------------------------
        #                 Check if order are present:
        # ---------------------------------------------------------------------
        purchase_pending = {}
        for purchase in purchase_pool.search([
                ('logistic_state', '=', 'draft'),
                ]):
            supplier_id = purchase.partner_id.id
            if supplier_id not in purchase_pending:
                purchase_pending[supplier_id] = purchase.id  # link ID

        # ---------------------------------------------------------------------
        #                 Collect data for purchase order:
        # ---------------------------------------------------------------------
        order_touched_ids = [] # For ending extra operations (linked to order)
        purchase_db = {} # supplier is the key
        for line in lines:
            product = line.product_id
            supplier = product.default_supplier_id

            # Collect order touched:
            order_id = line.order_id.id
            if order_id not in order_touched_ids:
                order_touched_ids.append(order_id)

            # Update supplier purchase:
            if supplier not in purchase_db:
                purchase_db[supplier] = []
            purchase_db[supplier].append(line)

        selected_ids = []  # ID: to return view list

        # 15 gen 2019: Cause a strange case there's some uncovered line
        # but covered with stock, change here the availability
        for supplier in purchase_db:
            # -----------------------------------------------------------------
            # Create details:
            # -----------------------------------------------------------------
            purchase_id = False
            is_company_partner = supplier == company.partner_id
            for line in purchase_db[supplier]:
                product = line.product_id

                # -------------------------------------------------------------
                # Lavoration order
                # -------------------------------------------------------------
                if is_company_partner and product.type == 'service':
                    line.mrp_state = 'draft'  # put in lavoration state
                    continue

                # -------------------------------------------------------------
                # Use stock to cover order:
                # -------------------------------------------------------------
                if not product:
                    continue

                purchase_qty = line.logistic_uncovered_qty
                if purchase_qty <= 0.0:
                    # ---------------------------------------------------------
                    # Bugfix (close yet covered order:
                    # ---------------------------------------------------------
                    if line.logistic_covered_qty == line.product_uom_qty:
                        line.logistic_state = 'ready'
                        _logger.error(
                            'Covered line marked as uncovered, correct!')
                    continue  # no order negative uncovered (XXX needed)

                # -------------------------------------------------------------
                # Create/Get header purchase.order (only if line was created):
                # -------------------------------------------------------------
                # TODO if order was deleted restore logistic_state to uncovered
                if not purchase_id:
                    partner = supplier or company.partner_id  # Use company
                    if partner.id in purchase_pending:
                        purchase_id = purchase_pending[partner.id]
                    else:
                        purchase_id = purchase_pool.create({
                            'partner_id': partner.id,
                            'date_order': now,
                            'date_planned': now,
                            # 'name': # TODO counter?
                            # 'partner_ref': '',
                            # 'logistic_state': 'draft',
                            }).id
                    selected_ids.append(purchase_id)

                purchase_line_pool.create({
                    'order_id': purchase_id,
                    'product_id': product.id,
                    'name': product.name,
                    'product_qty': purchase_qty,
                    'date_planned': now,
                    'product_uom': product.uom_id.id,
                    'price_unit': 1.0,  # TODO change product.0.0,

                    # Link to sale:
                    'logistic_sale_id': line.id,
                    })

                # Update line state:
                line.logistic_state = 'ordered' # XXX needed?

        # Bug: Close order pending but ready (nothing passed = check all)
        closed_order_ids = self.logistic_check_ready_order()

        # Check if some order linkable to other present with same partner:
        if closed_order_ids:
            _logger.warning('Order touched: %s' % len(order_touched_ids))
            order_touched_ids = tuple(
                set(order_touched_ids) - set(closed_order_ids))
            _logger.warning('Order touched real: %s' % len(order_touched_ids))

        sale_pool.sale_order_unificate_same_partner(order_touched_ids)

        # Return view:
        return purchase_pool.return_purchase_order_list_view(selected_ids)

    # -------------------------------------------------------------------------
    #                            COMPUTE FIELDS FUNCTION:
    # -------------------------------------------------------------------------
    @api.multi
    # @api.depends('assigned_line_ids', 'purchase_line_ids', 'load_line_ids',
    #    'delivered_line_ids', 'mrp_state')
    def _get_logistic_status_field(self):
        """ Manage all data for logistic situation in sale order:
        """
        _logger.warning('Update logistic qty fields now')
        for line in self:
            if line.product_id.is_kit:
                # -------------------------------------------------------------
                #                           KIT:
                # -------------------------------------------------------------
                # if is kit >> line not used:
                line.logistic_covered_qty = 0.0
                line.logistic_purchase_qty = 0.0
                line.logistic_uncovered_qty = 0.0
                line.logistic_received_qty = 0.0
                line.logistic_remain_qty = 0.0
                line.logistic_delivered_qty = 0.0
                line.logistic_undelivered_qty = 0.0
                # line.logistic_state = 'unused'
                line.logistic_position = ''  # TODO explode component?
            else:
                # -------------------------------------------------------------
                #                       NORMAL PRODUCT:
                # -------------------------------------------------------------
                # state = 'draft'
                product = line.product_id
                logistic_position = ''

                # -------------------------------------------------------------
                # OC: Ordered qty:
                # -------------------------------------------------------------
                logistic_order_qty = line.product_uom_qty

                # -------------------------------------------------------------
                # ASS: Assigned:
                # -------------------------------------------------------------
                logistic_covered_qty = 0.0
                for quant in line.assigned_line_ids:
                    logistic_covered_qty -= quant.quantity
                    logistic_position += _('[MAG] Q. %s > %s\n') % (
                        -quant.quantity,
                        product.default_slot_id.name or ''
                        )
                line.logistic_covered_qty = logistic_covered_qty

                # State valuation:
                # if logistic_order_qty == logistic_covered_qty:
                #    state = 'ready' # All in stock
                # else:
                #    state = 'uncovered' # To order

                # -------------------------------------------------------------
                # PUR: Purchase (order done):
                # -------------------------------------------------------------
                logistic_purchase_qty = 0.0

                if line.mrp_state in ('draft', 'progress'):
                    # Lavoration product (internal):
                    logistic_purchase_qty = logistic_order_qty
                else:
                    # Purchase product:
                    for purchase in line.purchase_line_ids:
                        logistic_purchase_qty += purchase.product_qty
                line.logistic_purchase_qty = logistic_purchase_qty

                # -------------------------------------------------------------
                # UNC: Uncovered (to purchase) [OC - ASS - PUR]:
                # -------------------------------------------------------------
                logistic_uncovered_qty = \
                    logistic_order_qty - logistic_covered_qty - \
                    logistic_purchase_qty
                line.logistic_uncovered_qty = logistic_uncovered_qty

                # State valuation:
                # if state != 'ready' and not logistic_uncovered_qty: # XXX
                #    state = 'ordered' # A part (or all) is order

                # -------------------------------------------------------------
                # BF: Received (loaded in stock):
                # -------------------------------------------------------------
                logistic_received_qty = 0.0
                if line.mrp_state == 'done':
                    # Job product (internal):
                    logistic_received_qty = logistic_order_qty
                    logistic_position += _('[PROD] Q. %s > %s\n') % (
                        logistic_order_qty,
                        '',
                        )
                else:
                    # Purchase product:
                    for move in line.load_line_ids:
                        # TODO verify
                        logistic_received_qty += move.product_uom_qty
                        logistic_position += _('[TAV] Q. %s > %s\n') % (
                            move.product_uom_qty,
                            move.slot_id.name or ''
                            )
                line.logistic_received_qty = logistic_received_qty

                # -------------------------------------------------------------
                # REM: Remain to receive [OC - ASS - BF]:
                # -------------------------------------------------------------
                logistic_remain_qty = \
                    logistic_order_qty - logistic_covered_qty - \
                    logistic_received_qty
                line.logistic_remain_qty = logistic_remain_qty

                # State valuation:
                # if state != 'ready' and not logistic_remain_qty: # XXX
                #    state = 'ready' # All present coveder or in purchase

                # -------------------------------------------------------------
                # BC: Delivered:
                # -------------------------------------------------------------
                logistic_delivered_qty = 0.0
                for move in line.delivered_line_ids:
                    # TODO verify
                    logistic_delivered_qty += move.product_uom_qty
                line.logistic_delivered_qty = logistic_delivered_qty

                # -------------------------------------------------------------
                # UND: Undelivered (remain to pick out) [OC - BC]
                # -------------------------------------------------------------
                logistic_undelivered_qty = \
                    logistic_order_qty - logistic_delivered_qty
                line.logistic_undelivered_qty = logistic_undelivered_qty

                # State valuation:
                # if not logistic_undelivered_qty: # XXX
                #    state = 'done' # All delivered to customer

                # -------------------------------------------------------------
                # Write data:
                # -------------------------------------------------------------
                # line.logistic_state = state
                line.logistic_position = logistic_position

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    # RELATION MANY 2 ONE:

    # A. Assigned stock:
    assigned_line_ids = fields.One2many(
        'stock.quant', 'logistic_assigned_id', 'Assign from stock',
        help='Assign all this q. to this line (usually one2one',
        )

    # B. Purchased:
    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'logistic_sale_id', 'Linked to purchase',
        help='Supplier ordered line linked to customer\'s one',
        )
    load_line_ids = fields.One2many(
        'stock.move', 'logistic_load_id', 'Linked load to sale',
        help='Loaded movement in picking in documents',
        )

    # C. Deliver:
    delivered_line_ids = fields.One2many(
        'stock.move', 'logistic_unload_id', 'Linked to deliveder',
        help='Deliver movement in pick out documents',
        )

    # -------------------------------------------------------------------------
    #                               FUNCTION FIELDS:
    # -------------------------------------------------------------------------
    # Computed q.ty data:
    logistic_covered_qty = fields.Float(
        'Covered qty', digits=dp.get_precision('Product Price'),
        help='Qty covered with internal stock',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )
    logistic_uncovered_qty = fields.Float(
        'Uncovered qty', digits=dp.get_precision('Product Price'),
        help='Qty not covered with internal stock (so to be purchased)',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )
    logistic_purchase_qty = fields.Float(
        'Purchase qty', digits=dp.get_precision('Product Price'),
        help='Qty order to supplier',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )
    logistic_received_qty = fields.Float(
        'Received qty', digits=dp.get_precision('Product Price'),
        help='Qty received with pick in delivery',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )
    logistic_remain_qty = fields.Float(
        'Remain qty', digits=dp.get_precision('Product Price'),
        help='Qty remain to receive to complete ordered',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )
    logistic_delivered_qty = fields.Float(
        'Delivered qty', digits=dp.get_precision('Product Price'),
        help='Qty deliverer  to final customer',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )
    logistic_undelivered_qty = fields.Float(
        'Not delivered qty', digits=dp.get_precision('Product Price'),
        help='Qty not deliverer to final customer',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )

    # Position:
    logistic_position = fields.Text(
        'Position', help='Stock position',
        readonly=True, compute='_get_logistic_status_field', multi=True,
        store=False,
        )

    # MRP state:
    mrp_state = fields.Selection([
        ('draft', 'Internal lavoration'),
        ('progress', 'In progress'),
        ('done', 'Done'),
        ], 'Lavoration state',
        )

    # State (sort of workflow):
    logistic_state = fields.Selection([
        ('unused', 'Unused'),  # Line not managed

        ('draft', 'Custom order'),  # Draft, customer order
        ('uncovered', 'Uncovered'),  # Not covered with stock
        ('ordered', 'Ordered'),  # Supplier order uncovered
        ('ready', 'Ready'),  # Order to be picked out (all in stock)
        ('done', 'Done'),  # Delivered qty (order will be closed)
        ], 'Logistic state', default='draft',
        # readonly=True,
        # compute='_get_logistic_status_field', multi=True,
        # store=True,  # TODO store True # for create columns
    )
