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


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """ Sale order
    """
    _inherit = 'sale.order'

    def sale_order_for_this_agent(self):
        """ Filter this user team order
        """
        model_pool = self.env['ir.model.data']
        tree_view_id = model_pool.get_object_reference(
            'sale', 'view_order_tree')[1]
        form_view_id = model_pool.get_object_reference(
            'sale', 'view_order_form')[1]
        search_view_id = model_pool.get_object_reference(
            'sale', 'view_sales_order_filter')[1]

        pdb.set_trace()
        team_id = self.env.user.agent_team_id.id
        if not team_id:
            raise exceptions.Warning(
                'Nessun ordine visibile, controllare il team di agente per '
                'impostarli!')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordini agente'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'view_id': tree_view_id,
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('team_id', '=', team_id)],
            'context': self.env.context,
            'target': 'current',
            'nodestroy': False,
            }


class ResUsers(models.Model):
    """ Agent references
    """
    _inherit = 'res.users'

    agent_team_id = fields.Many2one(
        'crm.team', 'Team agente',
        help='Team di riferimento per l\'agente, servirà per filtrare'
             'gli ordini nel menu apposito per gli agenti')
