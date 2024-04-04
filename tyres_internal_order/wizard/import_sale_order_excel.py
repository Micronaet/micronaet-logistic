#!/usr/bin/python
###############################################################################
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
###############################################################################

import logging
import base64
import pdb

import xlrd
from odoo import api, models, fields, exceptions

from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """ Sale order wizard
    """
    _inherit = 'sale.order'

    def open_extract_sale_exception_wizard(self):
        """ Extract data
        """
        model_pool = self.env['ir.model.data']
        wizard_pool = self.env['import.excel.sale.order.wizard']

        form_id = model_pool.get_object_reference(
            'tyres_internal_order',
            'view_import_excel_sale_order_wizard_form')[1]

        # Update context for call:
        context = self.with_context({
            'default_order_id': self.id,
        }).env.context

        wizard_id = wizard_pool.create({
            'order_id': self.id,
        }).id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Wizard import Ordini'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard_id,
            'res_model': 'import.excel.sale.order.wizard',
            'view_id': form_id,
            'views': [(form_id, 'form')],
            'domain': [],
            'context': context,
            'target': 'new',
            'nodestroy': False,
        }


class ImportExcelSaleOrderWizard(models.TransientModel):
    """ Import Wizard
    """
    _name = 'import.excel.sale.order.wizard'
    _description = 'Import Excel Sale Order Wizard'

    def export_sale_order_file(self):
        """ Export price file for this purchase order
        """
        wizard = self
        order = wizard.order_id

        report_pool = self.env['excel.report']

        # ---------------------------------------------------------------------
        # Excel file configuration:
        # ---------------------------------------------------------------------
        header = [
            _('Codice'), _('Quant.'), _('Prezzo unitario'),
        ]
        column_width = [
            10, 10, 12,
        ]

        ws_name = _('Dettaglio ordine')  # Worksheet name used
        report_pool.create_worksheet(ws_name, format_code='DEFAULT')
        report_pool.column_width(ws_name, column_width)

        # Header:
        row = 0
        report_pool.write_xls_line(ws_name, row, header, style_code='header')
        report_pool.freeze_panes(ws_name, 1, 0)
        # report_pool.autofilter(ws_name, [row, 0, row, 2])
        # report_pool.row_hidden(ws_name, [row])
        # report_pool.column_hidden(ws_name, [0])

        number = 'number'
        text = 'text'
        empty_data = (
            '',
            ('', number),
            ('', number),
        )
        for line in range(150):
            row += 1
            report_pool.write_xls_line(
                ws_name, row, empty_data, style_code=text)

        # Change wizard status:
        self.mode = 'import'
        # Save file:
        return report_pool.return_attachment('template_dettaglio_ordine')

    def import_sale_order_file(self):
        """ Export price file for this purchase order
        """
        wizard = self
        line_pool = self.env['sale.order.line']

        # ---------------------------------------------------------------------
        # Save file passed:
        # ---------------------------------------------------------------------
        if not wizard.file:
            raise exceptions.Warning(
                _('Necessario un file XLSX con il dettaglio ordine!'),
                )

        b64_file = base64.decodebytes(wizard.file)
        now = str(fields.Datetime.now()).replace(':', '_').replace('-', '_')
        filename = '/tmp/sale_order_%s.xlsx' % now
        f = open(filename, 'wb')
        f.write(b64_file)
        f.close()

        # ---------------------------------------------------------------------
        # Load force name (for web publish)
        # ---------------------------------------------------------------------
        try:
            WB = xlrd.open_workbook(filename)
        except:
            raise exceptions.Error(
                _('Impossibile leggere il file passato!: %s' % filename),
                )

        WS = WB.sheet_by_index(0)
        for row in range(WS.nrows):
            default_code = WS.cell(row, 0).value
            quantity = WS.cell(row, 1).value
            price = WS.cell(row, 2).value
            # todo import in sale order here
        return True

    order_id = fields.Many2one('sale.order', 'Ordine di rif.')
    mode = fields.Selection([
        ('export', '1. Scarica template'),
        ('import', '2. Carica ordine'),
    ], 'Modalità', default='export')
    file = fields.Binary(
        'File', help='File con dettaglio ordine da caricare in ODOO')
