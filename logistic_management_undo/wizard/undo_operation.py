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


_logger = logging.getLogger(__name__)

class SaleOrderUndoWizard(models.TransientModel):
    _name = 'sale.order.undo.wizard'
    _description = 'Sale order undo wizard'

    # -------------------------------------------------------------------------
    #                              FIELDS FUNCTION:
    # -------------------------------------------------------------------------    
    @api.multi
    @api.depends('order_id')
    def _get_order_status(self):
        ''' Analyse order and define progression state
        '''
        self.ensure_one()
        
        
        # TODO Analyise procedure:
        order = self.order_id
        order_state = order.logistic_state
        line_state = [line.logistic_state for line in order.order_line]
        
        state = u'draft'
        state_text = _(
            u'''<b>Order analysis:</b><br/>
                Current state: <b>%s</b><br/>
                Line state: <b>%s</b><br/>
            ''')  % (
                order_state,
                set(line_state),
                )

        undo_text = _(
            u'''<b>Undo operation:</b><br/>''')

        if order_state in ('error', 'cancel'):
            self.state_text = _('Order is in %s state, nothing todo!') % (
                order_state,
                )
            self.undo_text = _('Nothing todo on this order')
            self.state = 'nothing'
            return 


        # ---------------------------------------------------------------------
        # Delivered order:
        # ---------------------------------------------------------------------
        if order.logistic_picking_ids:
            state_text += '<br/><b>Account document present:</b><br/>'
            undo_text += '<br/><b>Remove document present, load stock:</b><br/>'
            for picking in order.logistic_picking_ids:
                state_text += 'DDT: <b>%s</b> [%s]<br/>' % (
                    picking.ddt_number,
                    picking.ddt_date,
                    )
                if picking.invoice_number:    
                    state_text += 'Invoice: <b>%s</b> [%s]<br/>' % (
                        picking.invoice_number,
                        picking.invoice_date,
                        )
                    
                undo_text += 'Remove: <b>%s</b> [%s]<br/>' % (
                    picking.ddt_number,
                    picking.ddt_date,
                    )
                if picking.invoice_number:    
                    undo_text += 'Remove: <b>%s</b> [%s] <br/>' % (
                        picking.invoice_number,
                        picking.invoice_date
                        )
                # TODO resi!!    

            if order.logistic_picking_ids[0].invoice_number:
                # -------------------------------------------------------------
                # 10. Phase Invoice
                # -------------------------------------------------------------
                state = 'invoice'
            else:    
                # -------------------------------------------------------------
                # 9. Phase DDT
                # -------------------------------------------------------------
                state = 'ddt'
                
        self.state_text = state_text
        self.undo_text = undo_text
        self.state = state

    # -------------------------------------------------------------------------
    #                               COLUMNS:
    # -------------------------------------------------------------------------    
    order_id = fields.Many2one('sale.order', 'Order selected', required=True)
    partner_id = fields.Many2one('res.partner', 'Customer', 
        related='order_id.partner_id', readonly=True)
        
    state_text = fields.Text('Status phase', widget='html', 
        compute='_get_order_status', store=False, readonly=True)
    undo_text = fields.Text('Undo phase', widget='html',
        compute='_get_order_status', store=False, readonly=True)

    #state_text_2 = fields.Text('Status phase 2', widget='html', 
    #    compute='_get_order_status', store=False, readonly=True)
    #undo_text_2 = fields.Text('Undo phase 2', widget='html',
    #    compute='_get_order_status', store=False, readonly=True)

    ddt_reason = fields.Text('DDT reason undo',
        default='Order cancelled from user')
        
    state = fields.Selection([
        ('nothing', 'Nothing to do'),
        
        ('draft', 'Draft'),
        ('payed', 'Payed'),
        ('order', 'Order'),
        ('covered', 'Covered'), # Partial
        ('ordered', 'Ordered'),
        ('delivered', 'Delivered'), # Partially
        ('ready', 'Ready'), # All present
        ('ddt', 'DDT Ready'), # DDT or Invoice generated
        ('invoice', 'Invoice Ready'), # DDT or Invoice generated
        ('done', 'Done'), # Delivered to customer
        ], 'State', compute='_get_order_status', readonly=True)

    state_undo = fields.Selection([
        ('cancel', 'Cancel'), # Remove order!

        ('draft', 'Draft'),
        ('payed', 'Payed'),
        ('order', 'Order'),
        ('covered', 'Covered'), # Partial
        ('ordered', 'Ordered'),
        ('delivered', 'Delivered'), # Partially
        ('ready', 'Ready'), # All present
        ('deliver', 'Deliver Ready'), # DDT or Invoice generated
        ], 'Undo state', default='cancel')

    # -------------------------------------------------------------------------
    #                               BUTTON EVENT:    
    # -------------------------------------------------------------------------    
    # Undo order:
    @api.multi
    def undo_ddt_cancel(self):
        ''' Delete picking ordine annullato
        '''
        quant_pool = self.env['stock.quant']
        cancel_pool = self.env['stock.ddt.cancel']
        
        import pdb; pdb.set_trace()
        order = self.order_id
        now = fields.Date.now()
        
        delete_move = []
        for picking in order.picking_ids: # Normally only one!
            # Collect detail text:
            detail = ''
            for line in picking.move_lines_for_report:
                detail += '' # TODO 

            # Collect data for deletion and stock operation:
            for line in picking.move_lines: # only done state
                product = line.used_product_id

                # -------------------------------------------------------------                    
                # To be removed:
                # -------------------------------------------------------------                    
                delete_move.append(line.id)

                # -------------------------------------------------------------                    
                # Reload stock:
                # -------------------------------------------------------------                    
                # Only loaded product will be reloaded:
                # no product: consu, service 
                if line.logistic_state in ('unused', ) or \
                        product.type != 'product':
                    continue
                data = {
                    'company_id': product.company_id.id,
                    'in_date': now,
                    'location_id': 
                        product.company_id.logistic_location_id.id
                    'product_id': product.id,
                    'quantity': line.product_uom_qty,
                    }            
                try:    
                    quant_pool.create(data)
                except:
                    _logger.error('Product is service? [%s - %s]\n%s' % (
                        product.product_tmpl_id.default_code or '',
                        product.name,
                        sys.exc_info(),
                        ))
                    continue                      

            # -----------------------------------------------------------------
            # Remove operations:
            # -----------------------------------------------------------------
            # Move:            
            self.env['stock.move'].unlink(delete_move)
            
            # Picking
            self.logistic_picking_ids.unlink()

            # -----------------------------------------------------------------
            # Cancel order and lined:
            # -----------------------------------------------------------------
            for line in order.order_line:
                # Line in draft (for future reload? XXX check assignements!)
                line.logistic_state = 'draft'
            order.logistic_state = 'cancel'
            
            # -----------------------------------------------------------------
            # Create new record for Undo registry:
            # -----------------------------------------------------------------
            cancel_pool.create({
                'date': field.Date.now(),
                'reason': self.ddt_reason,
                'detail': detail,
                })    
        return True

    @api.multi
    def undo_button(self):
        ''' Undo operation on order
        '''
        
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
