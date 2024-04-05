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


class CarrierSupplier(models.Model):
    """ Model name: Parcels supplier
    """

    _name = 'carrier.supplier'
    _description = 'Parcel supplier'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Name')
    account_ref = fields.Char('Account ref.')


class CarrierSupplierMode(models.Model):
    """ Model name: Parcels supplier mode of delivery
    """

    _name = 'carrier.supplier.mode'
    _description = 'Carrier mode'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Name', required=True)
    supplier_id = fields.Many2one('carrier.supplier', 'Carrier', required=True)

class CarrierParcelTemplate(models.Model):
    """ Model name: Parcels template
    """

    _name = 'carrier.parcel.template'
    _description = 'Parcel template'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Name')
    carrier_supplier_id = fields.Many2one('carrier.supplier', 'Carrier')
    length = fields.Float('Length', digits=(16, 2), required=True)
    width = fields.Float('Width', digits=(16, 2), required=True)
    height = fields.Float('Height', digits=(16, 2), required=True)
    dimension_uom_id = fields.Many2one('product.uom', 'Product UOM')

    weight = fields.Float('Weight', digits=(16, 2), required=True)
    weight_uom_id = fields.Many2one('product.uom', 'Product UOM')


class SaleOrderParcel(models.Model):
    """ Model name: Parcels for sale order
    """

    _name = 'sale.order.parcel'
    _description = 'Sale order parcel'
    _rec_name = 'weight'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    order_id = fields.Many2one('sale.order', 'Order')

    # Dimension:
    length = fields.Float('Length', digits=(16, 2), required=True)
    width = fields.Float('Width', digits=(16, 2), required=True)
    height = fields.Float('Height', digits=(16, 2), required=True)
    order_id = fields.Many2one('sale.order', 'Order')
    dimension_uom_id = fields.Many2one('product.uom', 'Product UOM')

    # Weight:
    weight = fields.Float('Weight', digits=(16, 2), required=True)
    weight_uom_id = fields.Many2one('product.uom', 'Product UOM')


class SaleOrder(models.Model):
    """ Model name: Sale order carrier data
    """

    _inherit = 'sale.order'

    @api.multi
    def set_default_carrier_description(self):
        """ Update description from sale order line
        """
        carrier_description = ''
        for line in self.order_line:
            product = line.product_id
            if product.type == 'service' or product.is_expence:
                continue
            carrier_description += '%s (X %s) '% (
                product.description_sale or product.titolocompleto or \
                    product.name or _('Not found'),
                int(line.product_uom_qty),
                )

        self.carrier_description = carrier_description.strip()

    @api.multi
    def load_template_parcel(self, ):
        """ Load this template
        """
        parcel_pool = self.env['sale.order.parcel']
        template = self.carrier_parcel_template_id

        parcel_pool.create({
            'order_id': self.id,
            'length': template.length,
            'width': template.width,
            'height': template.height,

            'weight': template.weight,
            })
        return True

    @api.multi
    def set_carrier_ok_yes(self, ):
        """ Set carrier as OK
        """
        self.write_log_chatter_message(_('Carrier data is OK'))

        # Check if order needs to be passed in ready status:
        self.carrier_ok = True
        self.logistic_check_and_set_ready()
        return True

    @api.multi
    def set_carrier_ok_no(self, ):
        """ Set carrier as UNDO
        """
        self.write_log_chatter_message(
            _('Carrier data is not OK (undo operation)'))
        self.carrier_ok = False
        return True

    @api.multi
    def _get_carrier_check_address(self):
        """ Check address for delivery
        """
        self.ensure_one()

        # Function:
        def format_error(field):
            return '<font color="red"><b> [%s] </b></font>' % field

        def get_partner_data(partner, check_dimension=False):
            """ Embedded function to check partner data
            """
            name = partner.name or ''
            street = partner.street or ''
            street2 = partner.street2 or ''
            if check_dimension:
                if len(name) > 70:  # check_dimension:
                    name = format_error(name)
                if len(street) > check_dimension:
                    street = format_error(street)
                if len(street2) > check_dimension:
                    street2 = format_error(street2)
                if len('%s%s' % (street or '', street2 or '')) > \
                        check_dimension:
                    street = format_error(street)
                    street2 = format_error(street2)

            return '%s %s %s - %s %s [%s %s] %s - %s<br/>' % (
                name,
                street or format_error(_('Address')),
                street2,
                partner.zip or format_error(_('ZIP')),
                partner.city or format_error(_('City')),
                partner.state_id.name or format_error(_('State')),
                partner.country_id.name or format_error(_('Country')),
                partner.phone or format_error(_('Phone')),
                partner.property_account_position_id.name or format_error(
                    _('Pos. fisc.')),
                )

        partner = self.partner_invoice_id
        if self.fiscal_position_id != partner.property_account_position_id:
            check_fiscal = format_error(
                _('Fiscal pos.: Order: %s, Partner %s<br/>') % (
                    self.fiscal_position_id.name,
                    partner.property_account_position_id.name,
                    ))
        else:
            check_fiscal = ''

        mask = _('%s<b>ORD.:</b> %s\n<b>INV.:</b> %s\n<b>DELIV.:</b> %s')
        self.carrier_check = mask % (
            check_fiscal,
            get_partner_data(self.partner_id),
            get_partner_data(partner),
            get_partner_data(self.partner_shipping_id, check_dimension=34),
            )

    @api.multi
    def _get_carrier_parcel_total(self):
        """ Return total depend on type of delivery: manual or shippy
        """
        for order in self:
            if order.carrier_shippy:
                order.real_parcel_total = len(order.parcel_ids)
            else:
                order.real_parcel_total = order.carrier_manual_parcel

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    report_supplier_hide = fields.Boolean(
        'Nascondi fornitore',
        help='Nella stampa dei picking non stampa il fornitore')

    carrier_ok = fields.Boolean('Carrier OK',
        help='Carriere must be confirmed when done!')
    carrier_shippy = fields.Boolean('Carrier Shippy', default=True,
        help='Carriere is managed by shippy pro (instead manual)!')

    # Manual:
    carrier_manual_weight = fields.Float('Manual weight', digits=(16, 2))
    carrier_manual_parcel = fields.Integer('Manual parcels')

    # Shippy:
    carrier_supplier_id = fields.Many2one('carrier.supplier', 'Carrier')
    carrier_mode_id = fields.Many2one('carrier.supplier.mode', 'Mode')
    carrier_parcel_template_id = fields.Many2one(
        'carrier.parcel.template', 'Parcel template')
    carrier_check = fields.Text('Carrier check', help='Check carrier address',
        compute='_get_carrier_check_address', widget='html')
    carrier_description = fields.Text('Carrier description')
    carrier_note = fields.Text('Carrier note')
    carrier_stock_note = fields.Text('Stock operator note')
    carrier_total = fields.Float('Goods value', digits=(16, 2))
    carrier_ensurance = fields.Float('Ensurance', digits=(16, 2))
    carrier_cash_delivery = fields.Float('Cash on delivery', digits=(16, 2))
    carrier_pay_mode = fields.Selection([
        ('cash', 'Cash'),
        ], 'Pay mode', default='cash')
    # carrier_incoterm = fields.selection([
    #    ('dap', 'DAP'),
    #    ], 'Pay mode', default='dap')
    parcel_ids = fields.One2many('sale.order.parcel', 'order_id', 'Parcels')
    real_parcel_total = fields.Integer(
        string='Colli', compute='_get_carrier_parcel_total')
    destination_country_id = fields.Many2one(
        'res.country', 'Destinazione',
        related='partner_shipping_id.country_id',
    )

    # From Carrier:
    carrier_cost = fields.Float('Cost', digits=(16, 2))
    carrier_track_id = fields.Char('Track ID', size=64)
    # manual_track_id = fields.Char('Track ID (not shippy)', size=64)
    # TODO extra data needed!

