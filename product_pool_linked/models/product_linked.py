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
from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)

class ProductTemplatePoolLinked(models.Model):
    """ Model name: ProductTemplatePoolLinked
    """

    _name = 'product.template.pool.linked'
    _description = 'Pool of linked product'
    _rec_name = 'id'
    _order = 'mode,id'

    # -------------------------------------------------------------------------
    #                                   BUTTON:
    # -------------------------------------------------------------------------
    @api.multi
    def add_similar_product_in_pool(self):
        """ Add selected product in alternative pool
            depend on open mode selection
        """
        product = self.similar_id
        if not product:
            return True

        product.similar_id = self.id

        # Clean product selection in pool:
        self.similar_id = False

        target = self.env.context.get('open_mode', 'current')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pool management'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'product.template.pool.linked',
            #'view_id': view_id, # False
            'views': [(False, 'form')], #, (False, 'tree')
            'domain': [],
            'context': self.env.context,
            'target': target,
            'nodestroy': False,
            }

    @api.multi
    def add_alternative_product_in_pool(self):
        """ Add selected product in alternative pool
            depend on open mode selection
        """
        product = self.alternative_id
        if not product:
            return True

        product.alternative_id = self.id

        # Clean product selection in pool:
        self.alternative_id = False

        target = self.env.context.get('open_mode', 'current')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pool management'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'product.template.pool.linked',
            #'view_id': view_id, # False
            'views': [(False, 'form')], #, (False, 'tree')
            'domain': [],
            'context': self.env.context,
            'target': target,
            'nodestroy': False,
            }

    # -------------------------------------------------------------------------
    #                             FUNCTION FIELD:
    # -------------------------------------------------------------------------
    # TODO Unificare:
    @api.multi
    def _get_product_similar_text(self):
        """ Better list of product for tree view
        """
        for pool in self:
            res = []
            for similar in sorted(pool.similar_ids,
                    key=lambda x: x.name):
                res.append(similar.default_code)
            pool.similar_text = ', '.join(res)

    @api.multi
    def _get_product_alternative_text(self):
        """ Better list of product for tree view
        """
        for pool in self:
            res = []
            for alternative in sorted(pool.alternative_ids,
                    key=lambda x: x.name):
                res.append(alternative.default_code)
            pool.alternative_text = ', '.join(res)

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    mode = fields.Selection([
        ('alternative', 'Substitutive'),
        ('similar', 'Alternative'),
        ], 'Mode', default='similar')

    similar_id = fields.Many2one('product.template', 'Add alternative')
    alternative_id = fields.Many2one('product.template', 'Add substitutive')

    similar_text = fields.Text(
        'Alternative product', compute='_get_product_similar_text', store=False)
    alternative_text = fields.Text(
        'Substitutive product', compute='_get_product_alternative_text',
        store=False)

    note = fields.Text('Note')


class ProductTemplate(models.Model):
    """ Model name: ProductTemplate
    """

    _inherit = 'product.template'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    similar_id = fields.Many2one(
        'product.template.pool.linked', 'Alternative', ondelete='set null')
    alternative_id = fields.Many2one(
        'product.template.pool.linked', 'Substitutive', ondelete='set null')

class ProductTemplatePoolLinked(models.Model):
    """ Model name: ProductTemplatePoolLinked
    """

    _inherit = 'product.template.pool.linked'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    similar_ids = fields.One2many(
        'product.template', 'similar_id', 'Alternative pool')
    alternative_ids = fields.One2many(
        'product.template', 'alternative_id', 'Substitute pool')

class ProductTemplate(models.Model):
    """ Model name: ProductTemplate
    """

    _inherit = 'product.template'

    # -------------------------------------------------------------------------
    #                            Button event:
    # -------------------------------------------------------------------------
    @api.multi
    def create_similar_pool(self):
        """ Create a new pool of alternative product, start adding this product
            in it
        """
        linked_pool = self.env['product.template.pool.linked']
        model_pool = self.env['ir.model.data']

        if self.similar_id:
            linked_id = self.similar_id.id
        else:
            # Create new pool and attach this product
            linked = linked_pool.create({
                'mode': 'similar',
                'similar_ids': [(6, 0, (self.id, ))],
                })
            linked_id = linked.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('New alternative pool'),
            'view_type': 'form',
            'view_mode': 'form', # tree
            'res_id': linked_id,
            'res_model': 'product.template.pool.linked',
            #'view_id': view_id, # False
            'views': [(False, 'form')], #, (False, 'tree')
            'domain': [],
            'context': self.env.context,
            'target': 'new',
            'nodestroy': False,
            }

    @api.multi
    def create_alternative_pool(self):
        """ Create a new pool of alternative product, start adding this product
            in it
        """
        linked_pool = self.env['product.template.pool.linked']
        model_pool = self.env['ir.model.data']

        if self.alternative_id:
            linked_id = self.alternative_id.id
        else:
            # Create new pool and attach this product
            linked = linked_pool.create({
                'mode': 'alternative',
                'alternative_ids': [(6, 0, (self.id, ))],
                })
            linked_id = linked.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('New subsitutive pool'),
            'view_type': 'form',
            'view_mode': 'form', # tree
            'res_id': linked_id,
            'res_model': 'product.template.pool.linked',
            #'view_id': view_id, # False
            'views': [(False, 'form')], #, (False, 'tree')
            'domain': [],
            'context': self.env.context,
            'target': 'new',
            'nodestroy': False,
            }

    # TODO unificare le 2 procedure
    @api.multi
    def unlink_similar_pool(self):
        """ Unlink from the pool, delete also pool if is the last
        """
        similar = self.similar_id
        # Delete pool if only 1 or 2 record (no similar product)
        if len(similar.similar_ids) in (1, 2):
            similar.unlink()
        else:
            self.similar_id = False
        return True

    @api.multi
    def unlink_alternative_pool(self):
        """ Unlink from the pool, delete also pool if is the last
        """
        alternative = self.alternative_id
        # Delete pool if only 1 or 2 record (no alternative product)
        if len(alternative.alternative_ids) in (1, 2):
            alternative.unlink()
        else:
            self.alternative_id = False
        return True

    # -------------------------------------------------------------------------
    #                          Related fields function
    # -------------------------------------------------------------------------
    # Only in form mode (not depends):
    # TODO unificare le due procedure:
    @api.one
    def _compute_product_template_similar_ids(self):
        """ Return pool of product present in alternative pool:
            It's a related field but maybe modified in the future
        """
        res = []
        for similar in sorted(self.similar_id.similar_ids,
                key=lambda x: x.name):
            if similar != self:
                res.append(similar.id)
        self.similar_ids = res

    @api.one
    def _compute_product_template_alternative_ids(self):
        """ Return pool of product present in subsitutive pool:
            It's a related field but maybe modified in the future
        """
        res = []
        for alternative in sorted(self.alternative_id.alternative_ids,
                key=lambda x: x.name):
            if alternative != self:
                res.append(alternative.id)
        self.alternative_ids = res

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    similar_ids = fields.One2many(
        'product.template',
        compute='_compute_product_template_similar_ids',
        string='Alternative pool')

    alternative_ids = fields.One2many(
        'product.template',
        compute='_compute_product_template_alternative_ids',
        string='Substitute pool')
