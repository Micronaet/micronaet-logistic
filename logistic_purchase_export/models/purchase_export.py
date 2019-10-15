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
import xlsxwriter
from odoo import api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)

class ResSupplierPurchaseExport(models.Model):
    """ Model name: ResSupplierPurchaseExport
    """
    
    _name = 'res.partner.purchase.export'
    _description = 'Export purchase'
    _rec_name = 'name'
    _order = 'name'

    # -------------------------------------------------------------------------    
    # Columns:
    # -------------------------------------------------------------------------    
    name = fields.Char('Name', size=40, required=True,
        help='Name of this syntax of export')    
    mode = fields.Selection([
        ('csv', 'CSV'),
        ('xlsx', 'XLSX'),
        ], string='Mode')    
    header = fields.Text('Header', size=280, 
        help='Column name split with |, ex.: Name|Q|Deadline')
    field_name = fields.Text('Fields', size=280, 
        help='Line field split with |, ex.: product_id.name, product_uom_qty')
    separator = fields.Char('Separator', size=5, 
        help='Separator for fields (only CSV)')

class ResSupplierPurchaseFolder(models.Model):
    """ Model name: ResSupplierPurchaseFolder
    """
    
    _name = 'res.partner.purchase.folder'
    _description = 'Export folder'
    _rec_name = 'name'
    _order = 'name'

    # -------------------------------------------------------------------------
    #                            COMPUTE FIELDS FUNCTION:
    # -------------------------------------------------------------------------
    @api.multi
    @api.depends('folder', )
    def _get_folder_path(self):
        ''' Return folder full path and create if not exist
        '''
        for folder in self:
            # -----------------------------------------------------------------
            # Create path if not exist:
            # -----------------------------------------------------------------
            try:
                fullpath = os.path.expanduser(folder.folder)
                os.system('mkdir -p %s' % fullpath)
            except:
                fullpath = ''    
                _logger.error('Error creating %s' % fullpath)
            
            # -----------------------------------------------------------------
            # Save value:
            # -----------------------------------------------------------------
            folder.fullpath = fullpath
        
    # -------------------------------------------------------------------------    
    # Columns:
    # -------------------------------------------------------------------------    
    name = fields.Char('Name', size=40, required=True,
        help='Name of this folder position')
    folder = fields.Char('Folder', size=280, required=True,
        help='Folder path, ex: /home/odoo/purchase or ~/supplier')
    fullpath = fields.Char('Folder path', size=280, 
        help='Expand folder name in correct path and create if not exist',
        compute='_get_folder_path')
    #test_mount = fields.Char('Test mount', size=280, 
    #    help='Check mount file, ex: /home/odoo/purchase/whoami.server')
        
        
class ResPartner(models.Model):
    """ Model name: Res Partner > Supplier
    """
    
    _inherit = 'res.partner'
    
    # -------------------------------------------------------------------------    
    # Columns:
    # -------------------------------------------------------------------------    
    purchase_export_id = fields.Many2one(
        'res.partner.purchase.export', string='File syntax')
    purchase_folder_id = fields.Many2one(
        'res.partner.purchase.folder', string='Output folder')

class PurchaseOrder(models.Model):
    """ Model name: Purchase order
    """
    
    _inherit = 'purchase.order'

    # -------------------------------------------------------------------------
    #                       COLUMNS:
    # -------------------------------------------------------------------------
    filename = fields.Char('Filename', size=100)

    @api.multi    
    def export_purchase_order(self):
        ''' Export purchase order
        '''
                    
        # ---------------------------------------------------------------------
        # Utility:
        # ---------------------------------------------------------------------
        # Excel:
        def xls_write_row(WS, row, row_data):
            ''' Print line in XLS file            
            '''
            col = 0
            for item in row_data:    
                WS.write(row, col, item)
                col += 1
            return True

        def clean(name):
            ''' Clean name for write in file system
            '''
            replace_list = [
                ('-', '_'),
                (' ', '_'),
                (':', '_'),
                ('/', '_'),
                ('\\', '_'),
                ]
            for item in replace_list:
                name = name.replace(item[0], item[1])    
            return name

        def get_field_list(line, field_name, all_string=False):
            ''' Extract and load data, return a list of values
            '''
            def formatLang(field, date=True, date_time=False):
                ''' Fake function for format Format date passed
                '''
                # Change italian mode:
                if not field:
                    return field
                    
                res = '%s/%s/%s%s' % (
                    field[8:10],
                    field[5:7],
                    field[:4],
                    field[10:],                    
                    )
                if date_time:
                    return res
                elif date:
                    return res[:10]    
            
            # Start procedure:        
            res = []

            for f in field_name.split('|'):
                if all_string:
                    res.append('%s' % eval(f))
                else:    
                    res.append(eval(f))
            return res
            
        return_mode = '\n'        
        now = fields.Datetime.now()

        for purchase in self:
            partner = purchase.partner_id
            if not partner.purchase_export_id or \
                    not partner.purchase_folder_id:
                _logger.warning(
                    'No export needed for purchase: %s' % purchase.name)
                continue
                
            # Get export path:
            fullpath = partner.purchase_folder_id.fullpath
            
            export = partner.purchase_export_id
            
            # Name was generated once:
            if purchase.filename:
                filename = purchase.filename
            else:
                filename = clean('%s_%s.%s' % (
                    partner.name,
                    purchase.name,
                    #purchase.date_order,
                    export.mode,
                    ))
                purchase.filename = filename
    
            fullname = os.path.join(fullpath, filename)
            _logger.warning('Purchase export: %s' % fullname)

            if export.mode == 'csv':
                # -------------------------------------------------------------                
                #                               CSV:
                # -------------------------------------------------------------                
                f_out = open(fullname, 'w')

                # -------------------------------------------------------------                
                # Header:
                # -------------------------------------------------------------                
                if export.header:
                    f_out.write('%s%s' % ( 
                        export.header.replace('|', export.separator),
                        return_mode,
                        ))

                # -------------------------------------------------------------                
                # Line:    
                # -------------------------------------------------------------                
                for line in purchase.order_line:
                    field_ids = get_field_list(
                        line, export.field_name, all_string=True)
                    f_out.write('%s%s' % ( 
                        export.separator.join(field_ids),
                        return_mode,
                        ))
                f_out.close()
            else: # 'xlsx'
                # -------------------------------------------------------------                
                #                              Excel:
                # -------------------------------------------------------------                
                WB = xlsxwriter.Workbook(fullname)
                WS = WB.add_worksheet(purchase.name)
                
                row = 0
                if export.header:
                    xls_write_row(WS, row, export.header.split('|'))
                    row += 1
                
                for line in purchase.order_line:
                    field_ids = get_field_list(line, export.field_name)
                    xls_write_row(WS, row, field_ids)
                    row += 1
                    
                try:
                    WB.close()
                except:    
                    _logger.error('Error closing XLSX file')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
