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
from odoo import exceptions 


_logger = logging.getLogger(__name__)

class ProductTemplateSupplierStock(models.Model):
    """ Model name: ProductTemplateSupplierStock
    """
    
    _name = 'product.template.supplier.stock'
    _description = 'Supplier stock'
    _rec_name = 'supplier_id'
    _order = 'quotation'

    @api.model
    def get_context_sale_order_object(self):
        ''' Return browseable sale line reference:
        '''
        line_pool = self.env['sale.order.line']
        context = self.env.context
        sale_order_id = context.get('sale_order_id')
        return line_pool.browse(sale_order_id)

    @api.multi
    def assign_to_purchase_none(self):
        ''' Remove this supplier
        '''
        line = self.get_context_sale_order_object()

        for splitted in line.purchase_split_ids:
            if splitted.supplier_id == self.supplier_id:
                splitted.unlink()
        return True
        
    @api.multi
    def assign_to_purchase_minus(self):
        ''' Assign -1 to this supplier
        '''
        sale_pool = self.env['sale.order.line']
        purchase_pool = self.env['sale.order.line.purchase']
        
        # Current sale line:
        line = self.get_context_sale_order_object()

        product_uom_qty = line.product_uom_qty
        stock_qty = self.stock_qty

        current_qty = 0.0
        current_line = False   
        for splitted in line.purchase_split_ids:
            if splitted.supplier_id == self.supplier_id:
                current_line = splitted
            current_qty += splitted.product_uom_qty
        if not current_line or current_qty < 1:
            raise exceptions.Warning('Nothing to remove')

        new_qty = current_line.product_uom_qty - 1.0
        if new_qty <= 0.0:
            current_line.unlink()
        elif current_line: # Update:
            current_line.write({
                'purchase_price': self.quotation,
                'product_uom_qty': new_qty,
                })                
        return True

    @api.multi
    def assign_to_purchase_plus(self):
        ''' Assign +1 to this supplier
        '''
        sale_pool = self.env['sale.order.line']
        purchase_pool = self.env['sale.order.line.purchase']
        
        # Current sale line:
        line = self.get_context_sale_order_object()
        product_uom_qty = line.product_uom_qty
        stock_qty = self.stock_qty

        current_qty = 0.0
        current_line = False   

        for splitted in line.purchase_split_ids:
            if splitted.supplier_id == self.supplier_id:
                current_line = splitted
            current_qty += splitted.product_uom_qty

        if current_line:
            used_qty = current_line.product_uom_qty + 1.0
            if used_qty > stock_qty:
                raise exceptions.Warning(
                    'Stock not available to cover! [%s < %s]' % (
                        stock_qty, product_uom_qty))
        else:
            used_qty = 1.0     
                
        if (current_qty + 1.0) > product_uom_qty:
            raise exceptions.Warning('All covered!')

        if current_line: # Update:
            current_line.write({
                'purchase_price': self.quotation,
                'product_uom_qty': used_qty,
                })
        else:        
            purchase_pool.create({
                'line_id': line.id,
                'purchase_price': self.quotation,
                'supplier_id': self.supplier_id.id,
                'product_uom_qty': used_qty,
                })                        
        return True

    @api.multi
    def assign_to_purchase_all(self):
        ''' Assign all order to this supplier
        '''
        # Selected sale line:
        purchase_pool = self.env['sale.order.line.purchase']
        
        line = self.get_context_sale_order_object()
        line.clean_all_purchase_selected() # Remove all
        
        # Collect fields:
        product_uom_qty = line.product_uom_qty
        stock_qty = self.stock_qty 
        if stock_qty >= product_uom_qty:
            used_qty = product_uom_qty
        else:
            used_qty = stock_qty

        # Create load:
        return purchase_pool.create({
            'line_id': line.id,
            'purchase_price': self.quotation,
            'supplier_id': self.supplier_id.id,
            'product_uom_qty': used_qty,
            })

    @api.multi
    def assign_to_purchase_this(self):
        ''' Assign max stock from this supplier (or remain)
        '''
        sale_pool = self.env['sale.order.line']
        purchase_pool = self.env['sale.order.line.purchase']
        
        # Current sale line:
        line = self.get_context_sale_order_object()

        product_uom_qty = line.product_uom_qty
        stock_qty = self.stock_qty

        current_qty = product_uom_qty
        current_line = False   
        for splitted in line.purchase_split_ids:
            if splitted.supplier_id == self.supplier_id:
                current_line = splitted
            else:    
                current_qty -= splitted.product_uom_qty
        
        if current_qty <= 0.0:
            return True

        # Check if stock cover remain:
        if stock_qty >= current_qty:
            used_qty = current_qty
        else:
            used_qty = stock_qty
        if used_qty <= 0.0:
            return True    

        if current_line: # Update:
            current_line.write({
                'purchase_price': self.quotation,
                'product_uom_qty': used_qty,
                })
        else:        
            purchase_pool.create({
                'line_id': line.id,
                'purchase_price': self.quotation,
                'supplier_id': self.supplier_id.id,
                'product_uom_qty': used_qty,
                })                        
        return True

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------    
    product_id = fields.Many2one(
        'product.template', 'Product', index=True, ondelete='cascade',
        )
    supplier_id = fields.Many2one(
        'res.partner', 'Partner', index=True, ondelete='cascade',
        domain="[('supplier', '=', True)]",
        )
    stock_qty = fields.Float(
        'Quantity', required=True, default=1.0,
        digits=dp.get_precision('Product Unit of Measure'))
    quotation = fields.Float(
        'Price', digits=dp.get_precision('Product Price'))
    best_price = fields.Boolean('Best price')    
    ipcode = fields.Char('Supplier code', size=24)

class ProductTemplate(models.Model):
    """ Model name: ProductTemplate
    """
    
    _inherit = 'product.template'
    
    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    supplier_stock_ids = fields.One2many(
        'product.template.supplier.stock', 'product_id', 'Supplier stock')

class SaleOrderLinePurchase(models.Model):
    """ Model name: Temp reference that will generare purchase order
    """
    
    _name = 'sale.order.line.purchase'
    _description = 'Sale purchase line'
    _rec_name = 'line_id'
    
    # -------------------------------------------------------------------------
    # COLUMNS:
    # -------------------------------------------------------------------------
    line_id = fields.Many2one('sale.order.line', 'Line')
    purchase_price = fields.Float(
        'Purchase Price', digits=dp.get_precision('Product Price'))
    product_uom_qty = fields.Float(
        'Q.ty', digits=dp.get_precision('Product Unit of Measure'))
    supplier_id = fields.Many2one(
        'res.partner', 'Partner', index=True, ondelete='cascade',
        domain="[('supplier', '=', True)]",
        )
    # -------------------------------------------------------------------------
    

class SaleOrderLine(models.Model):
    """ Model name: Sale order line relations
    """
    
    _inherit = 'sale.order.line'

    @api.multi
    def clean_all_purchase_selected(self):
        ''' Clean all selected elements
        '''
        for splitted in self.purchase_split_ids:
            splitted.unlink()
        return True

    @api.multi
    def _get_purchase_state(self):
        ''' Return stat of line
        '''
        gap = 0.00001
        for line in self:
            product_uom_qty = line.product_uom_qty
            covered_qty = 0.0
            for purchase in line.purchase_split_ids:
                covered_qty += purchase.product_uom_qty
            if abs(covered_qty - product_uom_qty) < gap:
                line.state_check = True
            else:    
                line.state_check = False
            line.state_qty = covered_qty
        return
    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    # TODO field for state of purchase 
    # TODO field for purchase supplier present    
    product_supplier_ids = fields.One2many(
        'product.template.supplier.stock', 
        related='product_id.supplier_stock_ids',
        )
    purchase_split_ids = fields.One2many(
        'sale.order.line.purchase', 'line_id')
    state_qty = fields.Float(
        'Covered q.', digits=dp.get_precision('Product Unit of Measure'),
        compute='_get_purchase_state', multi=True,
        ) 
    state_check = fields.Boolean(
        'OK', compute='_get_purchase_state', multi=True,
        ) 


class SaleOrder(models.Model):
    """ Model name: Sale order line relations
    """
    
    _inherit = 'sale.order'
    
    @api.multi
    def purchase_management_button(self):
        ''' Open view for purchase management
        '''
        
        model_pool = self.env['ir.model.data']
        tree_view_id = model_pool.get_object_reference(
            'logistic_product_supplier', 
            'view_sale_order_line_purchase_management_tree')[1]
        form_view_id = model_pool.get_object_reference(
            'logistic_product_supplier', 
            'view_sale_order_line_purchase_management_form')[1]

        line_ids = [item.id for item in self.order_line]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase line management'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'sale.order.line',
            'view_id': tree_view_id,
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('id', 'in', line_ids)],
            'context': self.env.context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
