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
import zipfile
import logging
import shutil
import base64
import json
import requests
from odoo import api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
import pdb

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """ Model name: Res Company utility
    """

    _inherit = 'res.company'

    def get_zulu_date(self, date):
        """ Return this date in Zulu format
            2021-04-28T09:15:50.692Z
        """
        date = str(date)  # if datetime format
        zulu_date = '%sT%sZ' % (
            date[:10], (date[11:] or '00:00:00'))
        return zulu_date


class AccountFiscalPositionPrint(models.Model):
    """ Model name: Purchase order line
    """

    _name = 'account.fiscal.position.print'
    _description = 'Print parameter'
    _rec_name = 'market'
    _order = 'market'

    market = fields.Selection([
        ('b2b', 'B2B'),
        ('b2c', 'B2C'),
        ], 'Market', default='b2b', required=True)
    position_id = fields.Many2one('account.fiscal.position', 'Position')

    report_picking = fields.Integer('Picking', default=1)
    report_ddt = fields.Integer('DDT', default=1)
    report_invoice = fields.Integer('Invoice', default=1)
    report_extra = fields.Integer('Extra doc.', default=1)
    report_label = fields.Integer('Label', default=1)

    _sql_constraints = [
        ('name_uniq', 'unique (position_id, market)',
            'Market in position must be unique!'),
        ]


class AccountFiscalPosition(models.Model):
    """ Model name: Print parameters
    """

    _inherit = 'account.fiscal.position'

    print_group = fields.Char(
        'Gruppo di stampa',
        help='Ordinamento e raggruppamento di stampa fatture sequenziali')
    sequential_print = fields.Boolean(
        string='Stampa sequenziale',
        help='La fattura viene stampata solo in modalità stampa sequenziale '
             '(ovvero selezionando dalla apposita videata gli ordini e'
             'lanciando la stampa)')
    print_ids = fields.One2many(
        'account.fiscal.position.print', 'position_id',
        'Print parameters',
        )


class PurchaseOrderLine(models.Model):
    """ Model name: Purchase order line
    """

    _inherit = 'purchase.order.line'

    # Used?:
    exported_date = fields.Date(
        'Exported date', related='logistic_sale_id.order_id.exported_date')

    internal_note = fields.Char('Internal note', size=160)
    purchase_order_date = fields.Datetime(
        'Ord. forn.', related='order_id.date_order')
    customer_order_date = fields.Datetime(
        'Ord. cl.', related='logistic_sale_id.order_id.date_order')
    internal_stock = fields.Boolean(
        'Ordine interno',
        related='order_id.partner_id.internal_stock',
        help='Usato per velocizzare il test nella videata di arrivo merce',
        store=True)
    # todo remove?
    internal_stock_mail = fields.Boolean(
        'Mail per trasferimento interno',
        related='order_id.partner_id.internal_stock_mail',
        help='Usato per velocizzare il test nella videata di arrivo merce',
        store=True)


class SaleOrderPrintResult(models.TransientModel):
    """ Esit printing report
    """
    _name = 'sale.order.print.result'
    _description = 'Print result'

    note = fields.Text('Result printing')


class ReturnAttachmentWizard(models.TransientModel):
    """ Wizard for download document
    """
    _name = 'return.attachment.wizard'

    name = fields.Char('Name', size=80)
    datas_fname = fields.Char('File name', help='Filename for url', size=80)
    attachment = fields.Binary('Attachment')


class SaleOrder(models.Model):
    """ Model name: Sale order
    """

    _inherit = 'sale.order'

    @api.multi
    def odoo_button_download_document(self):
        """ Return document
        """
        order = self
        document = []

        # ---------------------------------------------------------------------
        # Check what document are present:
        # ---------------------------------------------------------------------
        name = order.name.strip().replace(' ', '_').replace('-', '_')
        if order.check_need_invoice:
            invoice_fullname = order.get_invoice_fullname()
            invoice_name = os.path.basename(invoice_fullname)
            document.append(
                (invoice_fullname, invoice_name))

        if order.has_extra_document:
            extra_name = 'extra_document_%s.pdf' % name
            extra_fullname = order.with_context(
                force_filename=extra_name
            ).save_extra_document_file()
            document.append(
                (extra_fullname, extra_name))

        if not document:
            _logger.error('Nessun documento da scaricare!')
            raise exceptions.Warning('Nessun documento da scaricare!')

        # ---------------------------------------------------------------------
        # Generate Zip file:
        # ---------------------------------------------------------------------
        zip_path = '/tmp'
        zip_name = '%s.zip' % name
        zip_fullname = os.path.join(zip_path, zip_name)

        # ---------------------------------------------------------------------
        # Add document:
        # ---------------------------------------------------------------------
        zip_f = zipfile.ZipFile(zip_fullname, 'w')
        for attachment_fullname, attachment_filename in document:
            _logger.warning('Attaching %s file' % attachment_fullname)
            zip_f.write(
                attachment_fullname, attachment_filename, zipfile.ZIP_DEFLATED)
        zip_f.close()

        # ---------------------------------------------------------------------
        # Save binary file in wizard field:
        # ---------------------------------------------------------------------
        with open(zip_fullname, 'rb') as f:
            file_bytes = f.read()
            b64 = base64.b64encode(file_bytes)

        # ---------------------------------------------------------------------
        # Return document:
        # ---------------------------------------------------------------------
        attach_id = self.env['return.attachment.wizard'].create({
            'name': zip_name,
            'datas_fname': zip_name,
            'attachment': b64,
        }).id
        url = '/web/content/?field_filename=name&' \
              'model=return.attachment.wizard&id={}' \
              '&field=attachment&download=true'.format(
                   attach_id)

        _logger.warning('Return zip file: %s' % zip_name)
        return {
            'name': 'Document %s' % name,
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': url,
            }

    @api.multi
    def confirm_all_selected_server_action(self):
        """ Confirm all selected order
        """
        for order in self:
            if order.logistic_state != 'ready':
                _logger.error(
                    'Jump order not in ready status: %s' % order.name)
                continue
            order.workflow_ready_to_done_current_order()

    @api.multi
    def yet_sequential_printed(self):
        """ Yet printed """
        return self.write({
            'sequential_printed': True,
        })

    @api.multi
    def sequential_print_all_server_action(self):
        """ Print all server action
        """
        result_pool = self.env['sale.order.print.result']
        note = ''
        printed_order_invoice = []
        for order in sorted(self, reverse=True, key=lambda x: (
                x.fiscal_position_id.print_group or '',
                x.invoice_detail,
                x.name)):
            order_name = order.name
            fiscal = order.fiscal_position_id

            # Error check:
            if not fiscal.sequential_print:
                note += \
                    'Ordine %s: Pos. fisc. not per stampa sequenziale\n' % \
                    order_name
                _logger.warning('Order not for sequential print')
                continue
            if order.sequential_printed:
                note += \
                    'Ordine %s: fattura già stampata!\n' % \
                    order_name
                _logger.warning('Order with invoice yet printed)')
                continue
            if not order.invoice_detail:
                note += \
                    'Ordine %s senza la fattura\n' % order_name
                _logger.error('Order without invoice detail')
                continue
            if order.locked_delivery or order.logistic_source == 'internal' or\
                    order.logistic_state not in ('ready', 'done'):
                note += \
                    'Ordine %s: bloccato, non pronto o non fatto\n' % \
                    order_name
                _logger.error('Order not for printing '
                              '(not ready / done, locked or internal)')
                continue
            if order.logistic_picking_ids and \
                    order.logistic_picking_ids[
                        0].invoice_number == 'DA ASSEGNARE':
                no_invoice = True
                note += \
                    'Ordine %s: fattura ancora da assegnare\n' % order_name
                _logger.error('Order not for printing '
                              '(not ready / done, locked or internal)')
            else:
                no_invoice = False

            # -----------------------------------------------------------------
            # Read print parameters:
            # -----------------------------------------------------------------
            market = order.team_id.market_type
            try:
                # Read parameter line:
                parameter = [item for item in fiscal.print_ids
                             if item.market == market][0]
                loop_invoice = parameter.report_invoice
            except:
                note += \
                    'Ordine %s: Problemi con lettura parametri\n' % order_name
                _logger.error('Error reading print parameters')
                continue

            # -----------------------------------------------------------------
            # Invoice
            # -----------------------------------------------------------------
            try:
                if no_invoice:
                    _logger.warning('Jumped invoice printing')
                else:
                    for time in range(0, loop_invoice):
                        order.workflow_ready_print_invoice()
            except:
                note += \
                    'Ordine %s: errore stampa fattura: %s\n' % (
                        order_name, sys.exc_info())

                _logger.error('Error reading print invoice PDF')
                continue
            try:
                _logger.warning('Updated as printed [%s] # %s' % (
                    order.fiscal_position_id.name,
                    order.invoice_detail,
                ))
            except:
                pass
            printed_order_invoice.append(order)  # Printed

        for order in printed_order_invoice:
            order.write({
                'sequential_printed': True,
            })
        _logger.warning('Updated as printed # %s' % len(printed_order_invoice))

        # ---------------------------------------------------------------------
        # Log error
        # ---------------------------------------------------------------------
        result_id = result_pool.create({
            'note': note.replace('\n', '<br/>'),
            }).id

        form_id = self.env.ref(
            'tyres_logistic_pick_in_load.view_sale_order_print_result_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Result for view_name'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': result_id,
            'res_model': 'sale.order.print.result',
            'view_id': form_id,
            'views': [(form_id, 'form')],
            'domain': [],
            'context': self.env.context,
            'target': 'new',
            'nodestroy': False,
            }

    @api.multi
    def print_all_server_action(self):
        """ Print all server action
            Managed also with manage office parameter CUPS
        """
        result_pool = self.env['sale.order.print.result']

        log_print = {}
        for order in sorted(self, key=lambda x: x.name):
            log_print[order] = []
            if order.locked_delivery or order.logistic_source == 'internal' or\
                    order.logistic_state not in ('ready', 'done'):
                log_print[order].append(_('Not print order: %s') % order.name)
                continue

            # Setup loop print:
            # 31/03/2021 Integrazione parte di Alessandro Conti:
            # modifica per gestire pos. fiscale UK come parametri di stampa
            if order.partner_shipping_id.country_id.code == 'GB' and \
                    not order.fiscal_position_id.external_invoice_management:
                fisc_obj = self.env['account.fiscal.position'].search(
                    [('name', '=', 'United Kingdom')]
                )
                if fisc_obj:
                    fiscal = fisc_obj
                else:
                    fiscal = order.fiscal_position_id
            else:
                fiscal = order.fiscal_position_id
            _logger.info('---- PRINT ALL FISCAL POSITION %s' % fiscal.name)
            market = order.team_id.market_type
            try:
                # Read parameter line:
                parameter = [item for item in fiscal.print_ids
                             if item.market == market][0]

                # Invoice sequential print only:
                sequential_print = parameter.position_id.sequential_print

                loop_picking = parameter.report_picking
                loop_ddt = parameter.report_ddt
                loop_invoice = \
                    0 if sequential_print else parameter.report_invoice
                loop_extra = parameter.report_extra
                loop_label = parameter.report_label
            except:
                # Default print 1
                loop_picking = loop_ddt = loop_invoice = loop_extra = \
                    loop_label = 1
            _logger.info(
                'Printall: pick %s, ddt %s, invoice %s, extra %s, label %s' %
                (loop_picking, loop_ddt, loop_invoice, loop_extra, loop_label))

            log_print[order].append(_('Start print order: %s') % order.name)
            # -----------------------------------------------------------------
            # Picking
            # -----------------------------------------------------------------
            for time in range(0, loop_picking):
                order.workflow_ready_print_picking()
            log_print[order].append(_('Print #%s Picking') % loop_picking)

            # =================================================================
            # 31/03/2021 Integrazione parte gestione GB di Conti:
            if order.partner_shipping_id.country_id.code == 'GB':
                # -------------------------------------------------------------
                # Invoice
                # -------------------------------------------------------------
                for time in range(0, loop_invoice):
                    order.workflow_ready_print_invoice()
                log_print[order].append('Print #%s Invoice' % loop_invoice)

                # -------------------------------------------------------------
                # DDT
                # -------------------------------------------------------------
                for time in range(0, loop_ddt):
                    order.workflow_ready_print_ddt()
                log_print[order].append('Print #%s DDT' % loop_ddt)

            else:  # Normal part:
                # -------------------------------------------------------------
                # Invoice
                # -------------------------------------------------------------
                if order.check_need_invoice:
                    for time in range(0, loop_invoice):
                        order.workflow_ready_print_invoice()
                    log_print[order].append(
                        'Print #%s Invoice' % loop_invoice)

                # -------------------------------------------------------------
                # DDT
                # -------------------------------------------------------------
                else:
                    for time in range(0, loop_ddt):
                        order.workflow_ready_print_ddt()
                    log_print[order].append('Print #%s DDT' % loop_ddt)
            # End Alessandro Conti, [31.03.21 13:16]
            # =================================================================

            # -----------------------------------------------------------------
            # Extra document
            # -----------------------------------------------------------------
            if order.has_extra_document:
                for time in range(0, loop_extra):
                    order.workflow_ready_print_extra()
                log_print[order].append(_('Print #%s Extra doc') % loop_extra)

            # -----------------------------------------------------------------
            # Label
            # -----------------------------------------------------------------
            if order.has_label_to_print:
                for time in range(0, loop_label):
                    order.workflow_ready_print_label()
                log_print[order].append(_('Print #%s label') % loop_label)
            order.mmac_print_status = 'all'  # print_status = 'all'
        if len(self) <= 1:
            return True

        # ---------------------------------------------------------------------
        # Generate log (for many orders):
        # ---------------------------------------------------------------------
        note = ''
        for order in sorted(log_print, key=lambda x: x.name):
            note += _('Order: <b>%s<b/><br/>Messages:<br/>')

            for message in log_print[order]:
                note += message
            note += _('<br/><br/>')

        result_id = result_pool.create({
            'note': note,
            }).id

        form_id = self.env.ref(
            'tyres_logistic_pick_in_load.view_sale_order_print_result_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Result for view_name'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': result_id,
            'res_model': 'sale.order.print.result',
            'view_id': form_id,  # False
            'views': [(form_id, 'form')],
            'domain': [],
            'context': self.env.context,
            'target': 'new',
            'nodestroy': False,
            }

    @api.multi
    def _get_has_extra_document(self, ):
        """ Check if needed
        """
        # TODO setup correct check (filename will raise error not hide button)
        for order in self:
            try:
                # Extra CEE for B2B market:
                private_market = order.fiscal_position_id.private_market
                if private_market and \
                        private_market == order.team_id.market_type:
                    order.has_extra_document = True
                # XXX OLD: order.has_extra_document = \
                #    order.logistic_picking_ids[0].invoice_filename
            except:
                order.has_extra_document = False

    @api.multi
    def _get_has_label_to_print(self, ):
        """ Check if needed label
        """
        for order in self:
            order.has_label_to_print = order.mmac_shippy_order_id > 0

    @api.multi
    def _get_label_status(self, ):
        """ Check if needed label
        """
        for order in self:
            if order.carrier_shippy:
                if order.mmac_shippy_order_id > 0:  # has the code
                    order.get_label_status = 'shippy'
                else:
                    order.get_label_status = 'error'
            else:
                order.get_label_status = 'manual'

    has_extra_document = fields.Boolean(
        'Has extra document', compute='_get_has_extra_document')
    sequential_printed = fields.Boolean(
        'Sequential printed',
        help='Sequential printed check for clean order list')

    has_label_to_print = fields.Boolean(
        'Has label', compute='_get_has_label_to_print')

    get_label_status = fields.Char(
        'Label satus', size=10, compute='_get_label_status')


class StockPickingDelivery(models.Model):
    """ Model name: Stock picking import document
    """

    _name = 'stock.picking.delivery'
    _description = 'Generator of delivery'
    _rec_name = 'create_date'
    _order = 'create_date desc'

    @api.multi
    def assign_refund_counter_sequence(self):
        """ Assign counter number
        """
        self.name = self.env['ir.sequence'].next_by_code(
            'stock.picking.refund.generic.sequence')

    @api.multi
    def check_import_reply(self):
        """ Check import reply for get confirmation EXTRA BF
            Folder checked: delivery, refund
        """
        # todo schedule action?
        # Pool used:
        quant_pool = self.env['stock.picking.delivery.quant']
        # company_pool = self.env['res.company']

        # Parameter:
        company = self.env.user.company_id
        logistic_root_folder = os.path.expanduser(company.logistic_root_folder)

        refund_order_check = []
        move_list = []

        # Use same procedure to check delivery in product and refunds:
        for folder_mode in ('delivery', 'refund'):
            reply_path = os.path.join(
                logistic_root_folder, folder_mode, 'reply')
            history_path = os.path.join(
                logistic_root_folder, folder_mode, 'history')

            for root, subfolders, files in os.walk(reply_path):
                for f in files:
                    f_split = f[:-4].split('_')
                    try:
                        pick_id = int(f_split[-1])  # pick_in_ID.csv
                        if f_split[1] == 'in':
                            quants = quant_pool.search([
                                ('order_id', '=', pick_id)])
                            quants.write({'account_sync': True, })
                        # else: # 'undo' # not checked!

                        # -----------------------------------------------------
                        # Check if refund order (need extra check on move):
                        # -----------------------------------------------------
                        for move in self.browse(pick_id).move_line_ids:
                            order = move.logistic_load_id.order_id
                            if order.logistic_source == 'refund' and \
                                    order not in refund_order_check:
                                refund_order_check.append(order)

                    except:
                        _logger.error('Cannot read pick ID: %s' % f)

                    # XXX Move when all is done after?
                    move_list.append((
                        os.path.join(reply_path, f),
                        os.path.join(history_path, f),
                        ))
                    _logger.info('Pick ID: %s correct!' % f)
                break  # only first folder

        # ---------------------------------------------------------------------
        # Close refund order:
        # ---------------------------------------------------------------------
        for refund_order in refund_order_check:
            close = True
            for line in refund_order.order_line:
                # XXX INT check:
                if int(line.product_uom_qty) != \
                        int(line.logistic_received_qty):
                    close = False
                    break

            if close:
                refund_order.write({
                    'logistic_state': 'done',
                    })
                _logger.info('Refund all complete: %s' % refund_order.name)
            else:
                _logger.info('Refund not complete: %s' % refund_order.name)

        # Move files after all:
        for origin, destination in move_list:
            shutil.move(origin, destination)
        return True

    @api.model
    def api_check_import_reply(self, pick_id):
        """ Check import reply for get confirmation EXTRA BF
            Folder checked: delivery, refund
        """
        # Context parameters:
        is_refund = self.env.context.get('is_refund')

        # Pool used:
        quant_pool = self.env['stock.picking.delivery.quant']
        picking_pool = self.env['stock.picking']

        if is_refund:
            _logger.info('Refund mode')
            picking = self.browse(pick_id)  # Reload picking delivery!
        else:
            _logger.info('Order mode')
            picking = picking_pool.browse(pick_id)

        # Parameter:
        refund_order_check = []  # no need here?

        # Use same procedure to check delivery in product and refunds:
        # not used for undo (document was deleted!)
        quants = quant_pool.search([
            ('order_id', '=', pick_id)])
        quants.write({'account_sync': True, })

        # ---------------------------------------------------------------------
        # Check if refund order (need extra check on move):
        # ---------------------------------------------------------------------
        for move in picking.move_line_ids:
            order = move.logistic_load_id.order_id
            if order.logistic_source == 'refund' and \
                    order not in refund_order_check:
                refund_order_check.append(order)

        # ---------------------------------------------------------------------
        # Close refund order:
        # ---------------------------------------------------------------------
        for refund_order in refund_order_check:
            close = True
            for line in refund_order.order_line:
                # integer check:
                if int(line.product_uom_qty) != \
                        int(line.logistic_received_qty):
                    close = False
                    break
            if close:
                refund_order.write({
                    'logistic_state': 'done',
                    })
                _logger.info('Refund all complete: %s' % refund_order.name)
            else:
                _logger.info('Refund not complete: %s' % refund_order.name)
        return True

    # -------------------------------------------------------------------------
    #                            WORKFLOW ACTION:
    # -------------------------------------------------------------------------
    @api.multi
    def confirm_stock_load(self):
        """ Create new picking loading the selected material
        """
        # ---------------------------------------------------------------------
        # Pool used:
        # ---------------------------------------------------------------------
        # Stock:
        picking_pool = self.env['stock.picking']
        quant_pool = self.env['stock.picking.delivery.quant']
        sale_line_pool = self.env['sale.order.line']
        purchase_pool = self.env['purchase.order']
        company_pool = self.env['res.company']  # For format function

        # ---------------------------------------------------------------------
        #                          Load parameters
        # ---------------------------------------------------------------------
        company = self.env.user.company_id
        logistic_pick_in_type = company.logistic_pick_in_type_id

        logistic_pick_in_type_id = logistic_pick_in_type.id
        location_from = logistic_pick_in_type.default_location_src_id.id
        location_to = logistic_pick_in_type.default_location_dest_id.id

        # 2 way manage mode:
        api_mode = company.api_pick_load_area  # Load checkbox parameter
        logistic_root_folder = os.path.expanduser(company.logistic_root_folder)

        # ---------------------------------------------------------------------
        # Create picking:
        # ---------------------------------------------------------------------
        partner = self.supplier_id
        scheduled_date = self.create_date
        name = self.name  # mandatory Doc ID
        origin = _('%s [%s]') % (name, scheduled_date)

        picking = picking_pool.create({
            'partner_id': partner.id,
            'scheduled_date': scheduled_date,
            'origin': origin,
            # 'move_type': 'direct',
            'picking_type_id': logistic_pick_in_type_id,
            'group_id': False,
            'location_id': location_from,
            'location_dest_id': location_to,
            # 'priority': 1,
            'state': 'done',  # immediately!
            })
        self.picking_id = picking.id

        # ---------------------------------------------------------------------
        # Append stock.move detail (or quants if in stock)
        # ---------------------------------------------------------------------
        # ready line after assign load qty to purchase:
        sale_line_check_ready = []
        purchase_ids = []  # purchase order to check state
        for line in self.move_line_ids:  # Stock move to assign to picking
            # Extract purchase order (for final check closing state)
            purchase_id = line.logistic_purchase_id.order_id.id
            if purchase_id not in purchase_ids:
                purchase_ids.append(purchase_id)

            sale_line = line.logistic_load_id
            sale_order = sale_line.order_id
            product = line.product_id
            product_qty = line.product_uom_qty  # This move qty

            # -----------------------------------------------------------------
            # Order that load account stock status:
            # -----------------------------------------------------------------
            # Duplicate row to load stock:
            if sale_order.logistic_source in (
                    'internal', 'workshop', 'resell', 'refund'):
                quant_pool.create({
                    # date and uid are default
                    'order_id': self.id,  # Delivery order reference
                    'product_id': product.id,
                    'product_qty': product_qty,
                    'price': line.price_unit,
                    'sale_order_id': sale_order.id,  # Used for refund
                    })

            # -----------------------------------------------------------------
            # Create movement (not load stock):
            # -----------------------------------------------------------------
            # Link stock movement to delivery:
            line.write({
                'picking_id': picking.id,
                'origin': origin,
                })
            if sale_line not in sale_line_check_ready:
                sale_line_check_ready.append(sale_line)

        # ---------------------------------------------------------------------
        #                   Manage extra delivery / refund:
        # ---------------------------------------------------------------------
        # This delivery order quants:
        quants = quant_pool.search([('order_id', '=', self.id)])

        # Default data (to remove warning when not used):
        supplier_code = comment_line = ''
        order_file = refund_source = order_json = False

        # Create extra delivery order in exchange file:
        api_error = ''
        load_mode = 'delivery'  # keep as default if no quants
        if quants:
            folder_path = {}
            # Create folder if not present:
            for item in ('delivery', 'refund'):
                item_path = os.path.join(logistic_root_folder, item)
                folder_path[item] = item_path
                try:
                    os.system(
                        'mkdir -p %s' % os.path.join(item_path, 'reply'))
                    os.system(
                        'mkdir -p %s' % os.path.join(item_path, 'history'))
                except:
                    _logger.error('Cannot create %s' % item_path)

            # Note: every refund order il linked to one delivery in document!
            sale_order = quants[0].sale_order_id
            if sale_order.logistic_source == 'refund':
                load_mode = 'refund'
                refund_source = sale_order.refund_source_id
            else:
                load_mode = 'delivery'

            # -----------------------------------------------------------------
            # 2 Manage mode:
            # -----------------------------------------------------------------
            if api_mode:
                order_json = {}
            else:
                order_file = open(
                    os.path.join(
                        folder_path[load_mode],
                        'pick_in_%s.csv' % self.id),  # Delivery ID ref. here!
                    'w')

            if load_mode == 'delivery':
                # -------------------------------------------------------------
                # NORMAL DELIVERY (ONLY HEADER):
                # -------------------------------------------------------------
                api_endpoint = 'warehousemanagement/load'
                header = 'SKU|QTA|PREZZO|CODICE FORNITORE|RIF. DOC.|DATA\r\n'

            else:  # Refund
                api_endpoint = 'returnfromcustomer'
                # -------------------------------------------------------------
                # REFUND DOCUMENT (HEADER + COMMENT):
                # -------------------------------------------------------------
                # Extract data from invoice or fees:
                try:
                    # Get generator sale order:
                    generator_orders = self.env['mmac.reso'].search([
                        ('reso_order_id', '=', sale_order.id)])
                    if not generator_orders:
                        raise exceptions.Warning(
                            _('Cannot find sale order generator '
                              'for this refund'))
                    if len(generator_orders) > 1:
                        raise exceptions.Warning(
                            _('Found more than one sale order generator'))

                    generator_order = generator_orders[0].order_id
                    delivery_picking = generator_order.order_line[
                        0].delivered_line_ids[0].picking_id
                    if delivery_picking.is_fees:
                        # -----------------------------------------------------
                        # FEES:
                        # -----------------------------------------------------
                        comment_line = 'C|Corrispettivo %s del %s:\r\n' % (
                            generator_order.team_id.name or '',  # Team name
                            company_pool.formatLang(
                                delivery_picking.scheduled_date[:10],
                                date=True,
                            ),
                        )
                        supplier_code = \
                            generator_order.team_id.team_code_ref or ''
                    else:
                        # -----------------------------------------------------
                        # INVOICE:
                        # -----------------------------------------------------
                        comment_line = 'C|Fattura numero %s del %s\r\n' % (
                            delivery_picking.invoice_number,
                            company_pool.formatLang(
                                delivery_picking.invoice_date[:10],
                                date=True,
                            ),
                        )
                        supplier_code = '#%s' % (
                            generator_order.partner_id.id or '')
                except:
                    raise exceptions.Warning(
                        _('Cannot locate delivery picking'))

                # Header title + comment:
                header = 'TIPO|SKU|QTA|PREZZO|CODICE CLIENTE|AGENTE|DATA\r\n'
                header += comment_line

            if not api_mode:
                order_file.write(header)

            # -----------------------------------------------------------------
            # COMMON PART: Extract quants for lines:
            # -----------------------------------------------------------------
            for quant in quants:
                delivery_order = quant.order_id
                # -------------------------------------------------------------
                #                          Delivery:
                # -------------------------------------------------------------
                if load_mode == 'delivery':
                    # ---------------------------------------------------------
                    # 2 Manage mode:
                    # ---------------------------------------------------------
                    if api_mode:
                        # Header part
                        if not order_json:  # Header not loaded
                            order_json.update({
                                'documentNo': delivery_order.name,
                                'documentDate': company_pool.get_zulu_date(
                                    delivery_order.date),
                                'supplierCode':
                                    delivery_order.supplier_id.
                                    sql_supplier_code or '',
                                'details': [],
                            })
                        # Detail append:
                        order_json['details'].append({
                            'sku': quant.product_id.default_code,
                            'quantity': quant.product_qty,
                            'unitValue': quant.price,
                        })
                    else:
                        order_file.write('%s|%s|%s|%s|%s|%s\r\n' % (
                            quant.product_id.default_code,
                            quant.product_qty,
                            quant.price,
                            delivery_order.supplier_id.sql_supplier_code or '',
                            delivery_order.name,
                            company_pool.formatLang(
                                delivery_order.date, date=True),
                            ))

                # -------------------------------------------------------------
                #                             Refund:
                # -------------------------------------------------------------
                else:
                    # ---------------------------------------------------------
                    # 2 Manage mode:
                    # ---------------------------------------------------------
                    if api_mode:
                        # Header part
                        if not order_json:  # Header not loaded
                            order_json.update({
                                'custumerCode': supplier_code,
                                'documentDate': company_pool.get_zulu_date(
                                    delivery_order.date),
                                'salesPerson':
                                    refund_source.team_id.channel_ref or '',
                                'notes': comment_line[2:],  # Remove 'C|'
                                'details': [],
                            })
                        # Detail append:
                        order_json['details'].append({
                            'sku': quant.product_id.default_code,
                            'quantity': quant.product_qty,
                            'unitValue': quant.price,
                            # "type": "string",
                            # 'description': "string",
                            # 'notes': "string"
                        })
                    else:
                        order_file.write('A|%s|%s|%s|%s|%s|%s\r\n' % (
                            quant.product_id.default_code,
                            quant.product_qty,
                            quant.price,
                            # delivery_order.supplier_id.sql_supplier_code
                            # or '',
                            supplier_code,
                            refund_source.team_id.channel_ref or '',
                            # delivery_order.name,
                            company_pool.formatLang(
                                delivery_order.date, date=True),
                            ))

            if api_mode:
                # -------------------------------------------------------------
                # API Call:
                # -------------------------------------------------------------
                url = company.api_root_url
                location = '%s/%s' % (url, api_endpoint)
                token = company.api_token or company.api_get_token()
                json_dumps = json.dumps(order_json)

                loop_times = 1
                while loop_times <= 2:  # Loop twice if token error
                    loop_times += 1
                    header = {
                        'Authorization': 'bearer %s' % token,
                        'accept': 'text/plain',
                        'Content-Type': 'application/json',
                    }

                    # Send invoice:
                    _logger.warning('Calling: %s\n'
                                    'JSON: %s [Attempt: %s]' % (
                        location, json_dumps, loop_times - 1))
                    reply = requests.post(
                        location, data=json_dumps, headers=header)
                    if reply.ok:
                        _logger.info('[SUCCESS] Called: %s\nJSON: %s\n'
                                     'Reply: %s' % (
                                         location, json_dumps, reply))
                        reply_json = reply.json()
                        _logger.warning('Load generated: %s' % reply_json)
                        api_error = ''  # Reset error
                        break  # No new attempt
                    elif reply.status_code == 401:  # Token error
                        _logger.warning('[WARNING]: Refresh token')
                        token = company.api_get_token()
                    else:
                        api_error = reply.text
                        _logger.error(
                            'Load not received: \n%s!' % reply.text)
            else:
                order_file.close()

        # Check if procedure if fast to confirm reply (instead scheduled!):
        # todo manage in api mode:
        if api_mode:
            if api_error:
                raise exceptions.Warning(
                    'Errore chiamata API:\n{}'.format(api_error))
            else:  # Complete async call for picking generated here
                # todo tristate with delivery?
                if load_mode == 'refund':  # Parameter call for refund:
                    self.with_context(is_refund=True).api_check_import_reply(
                        self.id)
                else:  # Normal order
                    self.api_check_import_reply(picking.id)

        else:  # Work only with files:
            # Complete with async call for check file reply folder
            self.check_import_reply()

        # ---------------------------------------------------------------------
        # Sale order: Update Logistic status:
        # ---------------------------------------------------------------------
        sale_line_pool.check_ordered_ready_status(sale_line_check_ready)

        # ---------------------------------------------------------------------
        # Check Purchase order ready
        # ---------------------------------------------------------------------
        if purchase_ids:
            _logger.info('Check purchase order closed:')
            return purchase_pool.check_order_confirmed_done(purchase_ids)

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    @api.multi
    def open_purchase_line(self):
        """ Open current opened line
        """
        tree_view_id = self.env.ref(
            'tyres_logistic_pick_in_load.view_delivery_selection_tree').id
        search_view_id = self.env.ref(
            'tyres_logistic_pick_in_load.view_delivery_selection_search').id

        # Select record to show
        # TODO filter active!
        purchase_pool = self.env['purchase.order.line']
        purchases = purchase_pool.search([
            ('order_id.partner_id', '=', self.supplier_id.id),
            # ('logistic_undelivered_qty', '>', 0.0),
            # TODO change with logistic_status:
            # logistic_state = done!!!
            ])

        purchase_ids = []
        for purchase in purchases:
            if purchase.logistic_undelivered_qty:
                purchase_ids.append(purchase.id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purcase line:'),
            'view_type': 'form',
            'view_mode': 'tree',
            # 'res_id': 1,
            'res_model': 'purchase.order.line',
            'view_id': tree_view_id,
            'search_view_id': search_view_id,
            'views': [(tree_view_id, 'tree')],
            'domain': [('id', 'in', purchase_ids)],
            'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    name = fields.Char('Ref.', size=64, default=' ')
    date = fields.Date(
        'Date', default=fields.Datetime.now())
    create_date = fields.Datetime(
        'Create date', required=True, default=fields.Datetime.now())
    create_uid = fields.Many2one(
        'res.users', 'Create user', required=True,
        default=lambda s: s.env.user)
    supplier_id = fields.Many2one(
        'res.partner', 'Supplier', required=True,
        domain='[("supplier", "=", True)]',
        )
    carrier_id = fields.Many2one('carrier.supplier', 'Carrier')
    picking_id = fields.Many2one('stock.picking', 'Picking')


class StockPickingDeliveryQuant(models.Model):
    """ Model name: Stock line that create real load of stock
    """

    _name = 'stock.picking.delivery.quant'
    _description = 'Extra purchase line'
    _rec_name = 'product_id'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    order_id = fields.Many2one(
        'stock.picking.delivery', 'Order')
    sale_order_id = fields.Many2one(
        'sale.order', 'Origin order', help='Used for refund purposes')
    create_date = fields.Datetime(
        'Create date', default=fields.Datetime.now())
    create_uid = fields.Many2one(
        'res.users', 'Create user', default=lambda s: s.env.user)
    product_id = fields.Many2one(
        'product.product', 'Product', required=True)
    product_qty = fields.Float('Q.', digits=(16, 2), required=True)
    price = fields.Float('Price', digits=(16, 2))
    account_sync = fields.Boolean('Account sync')


class StockMove(models.Model):
    """ Model name: Stock Move
    """
    _inherit = 'stock.move'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    delivery_id = fields.Many2one(
        'stock.picking.delivery', 'Delivery',
        ondelete='set null')
    name_extended = fields.Char(
        string='Extended name', related='product_id.name_extended')
    default_code = fields.Char(
        string='Default code', related='product_id.default_code')
    force_hide = fields.Boolean('Force hide')
    internal_note = fields.Char('Note interne', size=160)

    # -------------------------------------------------------------------------
    #                                   Button event:
    # -------------------------------------------------------------------------
    @api.multi
    def hide_pending_stock_movement(self):
        """ Deactivate line (not visible)
        """
        # Log hide operation on original order:
        order = self.logistic_load_id.order_id
        order.write_log_chatter_message(_(
            'Supplier: %s, Product %s, Q. %s, hide movement!') % (
                self.partner_id.name,
                self.product_id.default_code,
                self.product_uom_qty,
                ))
        self.force_hide = True

    @api.multi
    def unhide_pending_stock_movement(self):
        """ Reactivate line (not visible)
        """
        # Log hide operation on original order:
        order = self.logistic_load_id.order_id
        order.write_log_chatter_message(_(
            'Supplier: %s, Product %s, Q. %s, Restored movement!') % (
                self.partner_id.name,
                self.product_id.default_code,
                self.product_uom_qty,
                ))

        self.force_hide = False

    @api.multi
    def unlink_pending_stock_movement(self):
        """ Button [-]
            Unlink stock move with log
        """
        # 1. Log deletion on original sale order:
        order = self.logistic_load_id.order_id
        order.write_log_chatter_message(_(
            'Delete stock move, Delivery: %s, wrong load: %s [%s] q %s') % (
                self.partner_id.name,
                self.product_id.name,
                self.product_id.default_code,
                self.product_uom_qty,
                ))

        # 2. Restore purchase order line:
        purchase_line = self.logistic_purchase_id
        purchase_line.write({
            'user_select_id': False,
            'logistic_delivered_manual': 0.0,
            'check_status': 'partial',
            })

        # 3. Delete stock.move:
        self.state = 'draft'
        return self.unlink()

    @api.multi
    def split_pending_stock_movement(self):
        """ Split stock.move
        """
        old_move = self
        new_quantity = 1  # todo
        old_quantity = old_move.product_uom_qty
        if new_quantity >= old_quantity:
            raise exceptions.Warning(_('La nuova quantità deve essere minore di {}'.format(old_quantity)))

        # Update old record:
        old_move.write({
            'product_uom_qty': old_quantity - new_quantity,
        })

        # Create new record:
        new_move = self.copy(default={
            'product_uom_qty': quantity,
            'price_unit': old_move,
            # 'ordered_qty'
        })
        new_move.action_confirm()
        return True

    @api.multi
    def generate_delivery_orders_from_line(self):
        """ Delivery order creation:
            Create the list of all order received split for supplier
        """
        delivery_pool = self.env['stock.picking.delivery']

        # --------------------------------------------------------------------------------------------------------------
        # Extract supplier line list:
        # --------------------------------------------------------------------------------------------------------------
        suppliers = {} # TODO also with carrier?
        for line in self:
            # sale_order = line.logistic_load_id.order_id
            purchase_order = line.logistic_purchase_id.order_id

            supplier = purchase_order.partner_id
            if supplier not in suppliers:
                suppliers[supplier] = []
            suppliers[supplier].append(line)

        # --------------------------------------------------------------------------------------------------------------
        # Create purchase order:
        # --------------------------------------------------------------------------------------------------------------
        delivery_ids = []
        for supplier in suppliers:
            # ----------------------------------------------------------------------------------------------------------
            # Create header:
            # ----------------------------------------------------------------------------------------------------------
            delivery_id = delivery_pool.create({
                'supplier_id': supplier.id,
                # 'carrier_id': carrier.id,
                # 'create_uid': self.env.uid,
                }).id
            delivery_ids.append(delivery_id)
            for line in suppliers[supplier]:
                line.delivery_id = delivery_id # Link to delivery order

        # --------------------------------------------------------------------------------------------------------------
        # Return created order:
        # --------------------------------------------------------------------------------------------------------------
        tree_view_id = form_view_id = False
        if len(delivery_ids) == 1:
            res_id = delivery_ids[0]
            views = [(tree_view_id, 'form'), (tree_view_id, 'tree')]
        else:
            res_id = False
            views = [(tree_view_id, 'tree'), (tree_view_id, 'form')]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery created:'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': res_id,
            'res_model': 'stock.picking.delivery',
            'view_id': tree_view_id,
            # 'search_view_id': search_view_id,
            'views': views,
            'domain': [('id', 'in', delivery_ids)],
            'context': self.env.context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    def unlink_from_stock_picking_load(self):
        """ Unlink stock move from order
        """
        model_pool = self.env['ir.model.data']

        delivery = self.delivery_id
        is_last = len(delivery.move_line_ids) <= 1

        # Remove line:
        self.write({'delivery_id': False})

        # Remove document:
        if is_last:
            delivery.unlink()

            # Return to assign view
            form_view_id = False
            tree_view_id = model_pool.get_object_reference(
                'tyres_logistic_pick_in_load', 'view_delivery_selection_stock_move_tree')[1]
            return {
                'type': 'ir.actions.act_window',
                'name': _('Assegna doc. di consegna:'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_id': False,
                'res_model': 'stock.move',
                'view_id': tree_view_id,
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                'domain': [('force_hide', '=', False), ('delivery_id', '=', False), ('picking_id', '=', False)],
                'context': self.env.context,
                'target': 'current', # 'new'
                'nodestroy': False,
                }
        return True


class PurchaseOrderLine(models.Model):
    """ Model name: Purchase Order Line
    """
    _inherit = 'purchase.order.line'

    @api.multi
    def dummy(self):
        """ Dummy button (do nothing)
        """
        return True

    # Fast filter:
    @api.model
    def return_fast_filter_view(self, field_name, field_value, name):
        """ Return view filtered for field
        """
        # Readability:
        context = self.env.context
        uid = self.env.uid
        ctx = {}

        command_clean_before = context.get('command_clean_before', False)
        if not field_name or command_clean_before:
            # Clean previous context from search defaults:
            for key in context:
                # Remove all previous search default:
                if key.startswith('search_default_'):
                    continue  # Cannot remove!
                ctx[key] = context[key]
            if command_clean_before:  # clean yet now!
                ctx['command_next_clean'] = False  # yet clean
            else:
                ctx['command_next_clean'] = True  # clean all next filter

        if field_name:
            ctx = context.copy()
            ctx['search_default_%s' % field_name] = field_value
        _logger.info(context)

        tree_id = self.env.ref(
            'tyres_logistic_pick_in_load.view_delivery_selection_tree').id
        search_id = self.env.ref(
            'tyres_logistic_pick_in_load.view_delivery_selection_search').id

        open_mode = context.get('open_mode')
        if open_mode == 'refund':
            _logger.warning('View in refund mode')
            domain = [
                ('dropship_manage', '=', False),
                ('check_status', '!=', 'done'),
                ('logistic_source', '=', 'refund'),
                ('order_id.logistic_state', '=', 'confirmed'),
                ('internal_stock', '=', False),
                ('user_select_id', 'in', (False, uid)),
            ]
        elif open_mode == 'workshop':
            _logger.warning('View in office mode')
            domain = [
                ('dropship_manage', '=', False),
                ('check_status', '!=', 'done'),
                ('logistic_source', '!=', 'refund'),
                ('order_id.logistic_state', '=', 'confirmed'),
                ('internal_stock', '=', False),
                ('user_select_id', 'in', (False, uid)),
            ]
        else:  # 'office'
            _logger.warning('View in office mode')
            domain = [
                ('dropship_manage', '=', False),
                ('check_status', '!=', 'done'),
                ('logistic_source', '!=', 'refund'),
                ('order_id.logistic_state', '=', 'confirmed'),
                ('internal_stock', '=', False),
                ('user_select_id', 'in', (False, uid)),
            ]

        action_data = {
            'type': 'ir.actions.act_window',
            'name': _('Filter applied: %s' % name),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order.line',
            'view_id': tree_id,
            'search_view_id': search_id,  # todo dont' work!!!
            'views': [
                (tree_id, 'tree'),
                (False, 'form'),
                (search_id, 'search'),
                ],
            'domain': domain,
            'context': ctx,
            'target': 'main',  # 'target': 'current', # 'new'
            'nodestroy': False,
            }
        _logger.warning('Filter: %s' % (action_data, ))
        return action_data

    @api.multi
    def clean_fast_filter(self):
        """ Remove fast filter:
        """
        return self.return_fast_filter_view(False, False, False)

    @api.multi
    def fast_filter_supplier(self):
        """ Filter this supplier
        """
        return self.return_fast_filter_view(
            'order_supplier_id',
            self.order_supplier_id.id,
            self.order_supplier_id.name,
            )

    @api.multi
    def fast_filter_product_id(self):
        """ Filter this product_id
        """
        return self.return_fast_filter_view(
            'product_id',
            self.product_id.id,
            self.product_id.default_code,
            )

    @api.multi
    def fast_filter_larghezza(self):
        """ Filter this larghezza
        """
        return self.return_fast_filter_view(
            'larghezza',
            self.larghezza,
            self.larghezza,
            )

    @api.multi
    def fast_filter_spalla(self):
        """ Filter this spalla
        """
        return self.return_fast_filter_view(
            'spalla',
            self.spalla,
            self.spalla,
            )

    @api.multi
    def fast_filter_raggio(self):
        """ Filter this raggio
        """
        return self.return_fast_filter_view(
            'raggio',
            self.raggio,
            self.raggio,
            )

    # On change not used!
    @api.onchange('logistic_delivered_manual')
    def onchange_logistic_delivered_manual(self, ):
        """ Write check state depend on partial or done
        """
        if self.logistic_delivered_manual < self.logistic_undelivered_qty:
            self.check_status = 'partial'
        else:
            self.check_status = 'total'

    @api.multi
    def create_delivery_orders(self):
        """ Create the list of all order received splitted for supplier
        """
        # ---------------------------------------------------------------------
        # Search selection line for this user:
        # ---------------------------------------------------------------------
        lines = self.search([
            ('user_select_id', '=', self.env.uid),  # This user
            ('logistic_delivered_manual', '>', 0),  # With quantity insert
            ('internal_stock', '=', False),  # No internal
            ('check_status', '!=', 'done'),  # Market previously
            ])

        if not lines:
            raise exceptions.Warning('No selection for current user!')

        # Create stock movements:
        self.stock_move_from_purchase_line(lines)

        # Update purchase line:
        for line in lines:
            # Partial not touched! # TODO correct?
            check_status = line.check_status
            if check_status == 'total':
                check_status = 'done'
            line.write({
                'user_select_id': False,
                'logistic_delivered_manual': 0.0,
                'check_status': check_status,
                })

        # TODO check ready order now:
        return self.clean_fast_filter()

    @api.multi
    def open_detail_delivery_in(self):
        """ Return detail view for stock operator
        """
        form_view_id = self.env.ref(
            'tyres_logistic_pick_in_load.view_delivery_selection_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Line detail'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'purchase.order.line',
            'view_id': form_view_id,
            'views': [(form_view_id, 'form')],
            'domain': [],
            'context': self.env.context,
            'target': 'new',
            'nodestroy': False,
            }

    @api.multi
    def delivery_0(self):
        """ Add +1 to manual arrived qty
        """
        self.write({
            'logistic_delivered_manual': 0,
            'user_select_id': False, # no need to save user
            })
        return self.onchange_logistic_delivered_manual()

    @api.multi
    def delivery_more_1(self):
        """ Add +1 to manual arrived qty
        """
        logistic_undelivered_qty = self.logistic_undelivered_qty
        logistic_delivered_manual = self.logistic_delivered_manual

        if logistic_delivered_manual >= logistic_undelivered_qty:
            raise exceptions.Warning(
                _('All received: %s!') % logistic_undelivered_qty)

        self.write({
            'logistic_delivered_manual': logistic_delivered_manual + 1.0,
            'user_select_id': self.env.uid,
            })
        return self.onchange_logistic_delivered_manual()

    @api.multi
    def delivery_less_1(self):
        """ Add +1 to manual arrived qty
        """
        logistic_delivered_manual = self.logistic_delivered_manual

        # todo check also logistic_undelivered_qty for remain?
        if logistic_delivered_manual < 1.0:
            raise exceptions.Warning('Nothing to remove!')

        if logistic_delivered_manual <= 1.0:
            active_id = False # XXX need?
        self.write({
            'logistic_delivered_manual': logistic_delivered_manual - 1.0,
            'user_select_id': self.env.uid,
            })
        return self.onchange_logistic_delivered_manual()

    @api.multi
    def delivery_all(self):
        """ Add +1 to manual arrived qty
        """
        logistic_undelivered_qty = self.logistic_undelivered_qty

        if logistic_undelivered_qty <= 0.0:
            raise exceptions.Warning('No more q. to deliver!')

        self.write({
            'logistic_delivered_manual': logistic_undelivered_qty,
            'user_select_id': self.env.uid,
            })
        return self.onchange_logistic_delivered_manual()

    # -------------------------------------------------------------------------
    # Compute function:
    # -------------------------------------------------------------------------
    @api.multi
    def _get_stock_extended_name(self):
        """ Add stock note from order
        """
        for line in self:
            try:
                order_note = line.logistic_sale_id.order_id.note_picking or ''
            except:
                order_note = ''

            product = line.product_id
            try:
                default_code = product.default_code or ''
            except:
                default_code = ''

            line.name_extended_stock = '%s %s%s' % (
                product.name_extended,
                ' <font color="blue">[{}]</font>'.format(default_code)
                if default_code else '',
                ' <font color="red">[{}]</font>'.format(order_note)
                if order_note else '',
            )

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    name_extended_stock = fields.Char(
        string='Nome per magazzinieri', compute='_get_stock_extended_name')

    # todo remove:
    name_extended = fields.Char(
        string='Extended name', related='product_id.name_extended')

    logistic_delivered_manual = fields.Float('Manual', digits=(16, 2))
    user_select_id = fields.Many2one('res.users', 'Selected user')

    # Related for filter
    supplier_delivery_date = fields.Date(
        'Previsione arrivo',
        )
    raggio = fields.Char(
        'Ray', related='product_id.raggio', store=True)
    larghezza = fields.Char(
        'Width', related='product_id.larghezza', store=True)
    spalla = fields.Char(
        'Spalla', related='product_id.spalla', store=True)

    order_supplier_id = fields.Many2one(
        'res.partner', 'Supplier', domain="[('supplier', '=', True)]",
        related='order_id.partner_id', store=True)

    order_supplier_name = fields.Char(
        'Supplier name', related='order_supplier_id.name')

    product_name = fields.Char('Product name', related='product_id.name')

    check_status = fields.Selection([
        # ('none', 'Not touched'), # Not selected
        ('done', 'Load in stock'), # Selected all remain to deliver

        ('total', 'Total received'), # Selected all to deliver
        ('partial', 'Partially received'), # Select partial to deliver
        ], 'Check status', default='partial')

    date_order = fields.Datetime(
        'Logistic source', readonly=True,
        related='logistic_sale_id.order_id.date_order',
        )

    logistic_source = fields.Selection(
        'Logistic source', readonly=True,
        related='logistic_sale_id.order_id.logistic_source',
        store=True,
        )


class StockPickingDelivery(models.Model):
    """ Model name: Stock picking import document: add relations
    """

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    _inherit = 'stock.picking.delivery'

    move_line_ids = fields.One2many(
        'stock.move', 'delivery_id', 'Load move')
    quant_ids = fields.One2many(
        'stock.picking.delivery.quant', 'order_id', 'Stock quant:')
    product_id = fields.Many2one(
        'product.product',
        related='move_line_ids.product_id',
        string='Product')
    quant_id = fields.Many2one(
        'product.product',
        related='quant_ids.product_id',
        string='Product in stock')
