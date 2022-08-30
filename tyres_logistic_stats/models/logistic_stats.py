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
import shutil
import requests
import base64
from odoo import api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


_logger = logging.getLogger(__name__)


class SaleOrderStats(models.Model):
    """ Model name: Sale Order
    """

    _inherit = 'sale.order'

    # -------------------------------------------------------------------------
    #                           UTILITY:
    # -------------------------------------------------------------------------
    @api.multi
    def refresh_all_statistic_orders(self):
        """ Refresh all
        """
        for order in self:
            _logger.info('Update statistic data %s: [Current: %s]' % (
                order.name,
                order.logistic_state,
                ))
            order.sale_order_refresh_margin_stats()

    # -------------------------------------------------------------------------
    #                           OVERRIDE FOR CALLS:
    # -------------------------------------------------------------------------
    # draft > order:
    # payment_is_done(self): # Not necessary

    # order > pending:
    @api.multi
    def workflow_manual_order_pending(self):
        """ If order have all line checked make one step in pending state
        """
        res = super(SaleOrderStats, self).workflow_manual_order_pending()
        self.refresh_all_statistic_orders()
        return res

    # todo pending > ready

    # ready > (delivering) > done
    @api.model
    def workflow_ready_to_done_draft_picking(self):
        """ Override order WF action
        """
        res = super(
            SaleOrderStats, self).workflow_ready_to_done_draft_picking()
        self.refresh_all_statistic_orders()
        return res

    # -------------------------------------------------------------------------
    #                           BUTTON EVENTS:
    # -------------------------------------------------------------------------
    @api.multi
    def go_real_sale_order(self):
        """ Call real order
        """
        form_id = self.env.ref('sale.view_order_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': self.id,
            'res_model': 'sale.order',
            'view_id': form_id,
            'views': [(form_id, 'form'), (False, 'tree')],
            'domain': [],
            'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }
    @api.multi
    def sale_order_refresh_margin_stats(self):
        """ Update margin data:
        """
        def get_net(line):
            """ Extract net price
            """
            price_unit = line.price_unit
            try:
                tax = line.tax_id[0]
                if not tax.price_include:
                    return price_unit
                amount = tax.amount / 100.0
                return price_unit / (1 + amount)
            except:
                _logger.error('Error reading tax for line: %s' % line)
                return price_unit

        self.ensure_one()

        # Statistic data:
        amount_untaxed = self.amount_untaxed
        payment_fee = self.mmac_payment_transaction_fee
        marketplace_fee = self.mmac_marketplace_transaction_fee
        shippy = self.carrier_cost

        pfu = purchase = 0.0
        stat_excluded = False
        detail_block = {
            'pfu': '',
            'purchase': '',
            'lines': '',
            }

        service_mask = '%s x %10.2f = %10.2f<br/>'
        product_mask = '%s x %10.2f [%s]<br/>'
        for line in self.order_line:
            price = get_net(line)
            subtotal = (price * line.product_uom_qty)
            product = line.product_id

            # -----------------------------------------------------------------
            # PFU article
            # -----------------------------------------------------------------
            if product.default_code == 'PFU':
                detail_block['pfu'] += service_mask % (
                    line.product_uom_qty,
                    price,
                    subtotal,
                    )
                pfu += subtotal
                continue

            # -----------------------------------------------------------------
            # Expence article
            # -----------------------------------------------------------------
            if product.is_expence:
                continue # not used!

            # -----------------------------------------------------------------
            # Product detail
            # -----------------------------------------------------------------
            detail_block['lines'] += product_mask % (
                line.product_uom_qty,
                price,
                product.name_extended,
                )

            # -----------------------------------------------------------------
            # Purchase cost:
            # -----------------------------------------------------------------
            for purchase_line in line.purchase_line_ids:
                if purchase_line.order_id.partner_id.internal_stock:
                    stat_excluded = True

                price = purchase_line.price_unit # TODO get_net(line)?
                subtotal = (price * purchase_line.product_qty)
                detail_block['purchase'] += service_mask % (
                    purchase_line.product_qty,
                    price,
                    subtotal,
                    )
                purchase += subtotal
                continue

        margin = amount_untaxed - payment_fee - marketplace_fee - \
            pfu - purchase - shippy

        if amount_untaxed:
            margin_rate = 100.0 * (margin / amount_untaxed)
        else:
            margin_rate = 0.0

        if margin > 0.0:
            level = 'positive'
        elif not margin:
            level = 'neutral'
        else:
            level = 'negative'

        # ---------------------------------------------------------------------
        # Log Detail:
        # ---------------------------------------------------------------------
        detail = _('Total sold untaxed: <b>%10.2f</b><br/>') % amount_untaxed

        detail += _('- Payment fee: <b>%10.2f</b><br/>') % payment_fee
        detail += _('- Marketplace fee: <b>%10.2f</b><br/>') % marketplace_fee
        detail += _('- Shippy: <b>%10.2f</b><br/>') % shippy

        if detail_block['pfu']:
            detail += _('- PFU: <b>%10.2f</b><br/><i>%s</i><br/>') % (
                pfu,
                detail_block['pfu'],
                )

        if detail_block['purchase']:
            detail += _('- Purchase: <b>%10.2f</b><br/><i>%s</i><br/>') % (
                purchase,
                detail_block['purchase'],
                )

        detail += _('= Margin: <b>%10.2f</b> >> %10.2f %%<br/>') % (
            margin,
            margin_rate,
            )

        detail += _('Sale result: <b>%s</b><br/>') % level


        # Update record with statistic:
        self.write({
            'stat_sale': amount_untaxed,
            # payment_fee
            # marketplace_fee
            'stat_shippy': shippy,
            'stat_pfu': pfu,
            'stat_purchase': purchase,
            'stat_margin': margin,
            'stat_margin_rate': margin_rate,
            'stat_level': level,
            'stat_detail': detail,
            'stat_lines': detail_block['lines'],
            'stat_excluded': stat_excluded,
            })
        return True

    # -------------------------------------------------------------------------
    #                               COLUMNS:
    # -------------------------------------------------------------------------
    stat_sale = fields.Float('Sale net', digits=(16, 2))
    # payment_fee
    # marketplace_fee
    stat_shippy = fields.Float('Shippy', digits=(16, 2))
    stat_pfu = fields.Float('PFU Total', digits=(16, 2))
    stat_purchase = fields.Float('Purchase total', digits=(16, 2))
    stat_margin = fields.Float('Margin', digits=(16, 2))
    stat_margin_rate = fields.Float('Margin rate', digits=(16, 2))
    stat_lines = fields.Text('Sale lines')
    stat_detail = fields.Text('Sale detail')
    stat_excluded = fields.Boolean('Excluded', help='Has internal purchase')
    stat_level = fields.Selection([
        ('unset', 'Not present'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('positive', 'Positive'),
        ], 'Margin level', default='unset',
        )
