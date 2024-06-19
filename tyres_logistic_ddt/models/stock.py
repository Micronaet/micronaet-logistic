#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2001-2018 Micronaet S.r.l. (<https://micronaet.com>)
#    Developer: Nicola Riolini @thebrush
#               (<https://it.linkedin.com/in/thebrush>)
#    Copyright (C) 2014 Abstract (http://www.abstract.it)
#    @author Davide Corio <davide.corio@abstract.it>
#    Copyright (C) 2014 Agile Business Group (http://www.agilebg.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import sys
import logging
from odoo import fields, models, api
from odoo import _


_logger = logging.getLogger(__name__)


class StockPickingCarriageCondition(models.Model):

    _name = "stock.picking.carriage_condition"
    _description = "Carriage Condition"

    name = fields.Char(string='Carriage Condition', required=True)
    note = fields.Text(string='Note')

class StockPickingGoodsDescription(models.Model):

    _name = 'stock.picking.goods_description'
    _description = "Description of Goods"

    name = fields.Char(string='Description of Goods', required=True)
    note = fields.Text(string='Note')


class StockPickingTransportationReason(models.Model):

    _name = 'stock.picking.transportation_reason'
    _description = 'Reason for Transportation'

    name = fields.Char(string='Reason For Transportation', required=True)
    note = fields.Text(string='Note')


class StockPickingTransportationMethod(models.Model):

    _name = 'stock.picking.transportation_method'
    _description = 'Method of Transportation'

    name = fields.Char(string='Method of Transportation', required=True)
    note = fields.Text(string='Note')


class StockPicking(models.Model):
    """ Add extra fields to keep picking as DDT or Invoice:
    """
    _inherit = 'stock.picking'

    # BUTTON / UTILITY: Launch wizard
    @api.multi
    def generate_refund_document(self):
        """ Open refund management from this document
        """
        # Pool used:
        wizard_pool = self.env['stock.picking.refund.wizard']
        line_pool = self.env['stock.picking.refund.line.wizard']

        # ---------------------------------------------------------------------
        # Create wizard element
        # ---------------------------------------------------------------------
        wizard_id = wizard_pool.create({
            'picking_id': self.id,
            }).id

        for line in self.move_lines: #move_lines_for_report()
            product_qty = line.product_qty
            if not product_qty:
                continue # jump empty q (es. Kit)
            if line.product_id.type == 'service':
                continue # no service product (expense and lavoration)

            line_pool.create({
                'wizard_id': wizard_id,
                'product_id': line.product_id.id,
                'product_qty': product_qty,
                'refund_qty': product_qty, # Same q. (returned from customer)
                'stock_qty': product_qty, # Same q. (load stock)
                # Reference for description in report:
                'line_id': line.logistic_unload_id.id,
                })

        # ---------------------------------------------------------------------
        # Open wizard element
        # ---------------------------------------------------------------------
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refund wizard'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard_id,
            'res_model': 'stock.picking.refund.wizard',
            'view_id': False,
            'views': [(False, 'form')],
            'domain': [],
            'context': self.env.context,
            'target': 'new',
            'nodestroy': False,
            }

    @api.multi
    def assign_invoice_number(self):
        """ Assign invoice number depend on fiscal position and parameter in
            partner configuration
        """
        for picking in self:
            # Load partner sequence (depend on fiscal position)
            partner = picking.partner_id
            if not partner.property_account_position_id:
                _logger.error(
                    'Partner %s with no fiscal position' % partner.name)
                return False

            sequence = False # TODO
            if not sequence:
                _logger.error(
                    'Partner %s no sequence found in fiscal position' % (
                        partner.name))
                return False

            sequence_number = False  # todo
            if picking.stock_mode == 'out':
                picking.write({
                    'invoice_number': sequence_number,
                    'invoice_date': fields.Datetime.now(),
                    })
            else: # 'nc' >> Credit note
                # Note: Keep same number but different prefix:
                sequence_number = sequence_number.replace('FT', 'NC')
                picking.write({
                    'invoice_number': sequence_number,
                    'invoice_date': fields.Datetime.now(),
                    })
        return True

    @api.multi
    def assign_ddt_number(self):
        """ Assign DDt number depend on fiscal position and parameter in
            partner configuration
        """
        for picking in self: # Use DDT counter:
            if picking.stock_mode == 'out':
                counter = self.env['ir.sequence'].next_by_code(
                    'stock.picking.ddt.sequence')
            else:  # in >> Refund value:
                counter = self.env['ir.sequence'].next_by_code(
                    'stock.picking.refund.sequence')

            # Update Document data (DDT or FC)
            picking.write({
                'ddt_number': counter,
                'ddt_date': fields.Datetime.now(),
                })
        return True

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    stock_mode = fields.Selection([
        ('in', 'Refund document'),
        ('out', 'Delivery document'),
        ], string='Stock mode', default='out')
    refund_origin_id = fields.Many2one(
        'stock.picking', string='Back document refunded')

    # -------------------------------------------------------------------------
    # API fields:
    ddt_number = fields.Char('Document number')
    ddt_date = fields.Datetime('Document date')
    ddt_filename = fields.Char(
        'DDT filename', size=80,
        help='DDT filename for PDF report')

    invoice_number = fields.Char('Invoice number')
    invoice_date = fields.Datetime('Invoice date')
    invoice_filename = fields.Char(
        'Invoice filename', size=80,
        help='Invoice filename for PDF report')

    invoice_json = fields.Text(
        'JSON Reply',
        help='Invoice od DDT reply in JSON')
    # -------------------------------------------------------------------------

    carriage_condition_id = fields.Many2one(
        'stock.picking.carriage_condition', string='Carriage Condition')
    goods_description_id = fields.Many2one(
        'stock.picking.goods_description', string='Description of Goods')
    transportation_reason_id = fields.Many2one(
        'stock.picking.transportation_reason',
        string='Reason for Transportation')
    transportation_method_id = fields.Many2one(
        'stock.picking.transportation_method',
        string='Method of Transportation')
    carrier_id = fields.Many2one(
        'res.partner', string='Carrier')
    parcels = fields.Integer('Parcels')
    weight = fields.Float('Weight')


class StockPicking(models.Model):
    """ Add extra fields to keep picking as DDT or Invoice:
    """
    _inherit = 'stock.picking'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    refunded_ids = fields.One2many(
        'stock.picking', 'refund_origin_id',
        string='Document refunded this BC')

