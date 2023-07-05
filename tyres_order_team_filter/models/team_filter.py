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
from odoo import api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class CrmTeam(models.Model):
    """ Team setup (force default function)
    """
    _inherit = 'crm.team'

    @api.model
    def my_menu_server_action(self, mode):
        """ Call sale order with different open modes
        """
        user_id = self.env.uid
        user = self.env['res.users'].browse(user_id)

        # tree,form,graph,pivot
        team_ids = [t.id for t in user.team_ids]
        domain = [
            ('logistic_source', 'not in', ('refund', )),
            ('team_id', 'in', team_ids),
        ]

        if mode == 'carrier':
            domain.extend([
                ('partner_id.internal_stock', '=', False),
                ('carrier_ok', '=', False),
                ('logistic_state', 'in', (
                    'order', 'pending', 'ready', 'delivering')),
            ])
        elif mode != 'all':
            # Add the logistic state filter except for all:
            domain.append(('logistic_state', '=', mode))

        if mode == 'ready':  # Extra integration
            domain.append(('locked_delivery', '=', False))

        tree_id = self.env.ref('sale.view_order_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ordini modalità %s' % mode,
            'view_type': 'form',
            'view_mode': 'tree,form,graph,pivot',
            # 'res_id': self.id,
            'res_model': 'sale.order',
            'view_id': tree_id,
            'views': [
                (tree_id, 'tree'),
                (False, 'form'),
                (False, 'pivot'),
                (False, 'graph'),
                ],
            'domain': domain,
            'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }


class CrmTeam(models.Model):
    """ Team setup (force default function)
    """
    _inherit = 'crm.team'

    # -------------------------------------------------------------------------
    # Override original function:
    # -------------------------------------------------------------------------
    @api.model
    @api.returns('self', lambda value: value.id if value else False)
    def _get_default_team_id(self, user_id=None):
        """ Get default from user setup
        """
        if not user_id:
            user_id = self.env.uid
        user = self.env['res.users'].browse(user_id)
        return user.my_default_team_id


class ResUsersMyTemplate(models.Model):
    """ Model name: Res Users My Template
    """

    _name = 'res.users.my.template'
    _rec_name = 'user_id'
    _order = 'sequence'

    # -------------------------------------------------------------------------
    # COLUMNS:
    # -------------------------------------------------------------------------
    # Template part:
    user_id = fields.Many2one('res.users', 'User link')
    template_menu_id = fields.Many2one('ir.ui.menu', 'Template menu',
        # domain="[('action.res_model', '=', 'sale.order')]"
        )
    sequence = fields.Integer('Sequence', default=10)
    force_name = fields.Char('Force name')

    # User part:
    my_user_id = fields.Many2one('res.users', 'User link')
    my_action_id = fields.Many2one(
        'ir.actions.act_window', 'My action')
    my_menu_id = fields.Many2one('ir.ui.menu', 'My menu')
    my_sequence = fields.Integer('My Sequence', default=10)
    # -------------------------------------------------------------------------


class ResUsers(models.Model):
    """ Model name: Res Users
    """

    _inherit = 'res.users'

    # -------------------------------------------------------------------------
    # COLUMNS:
    # -------------------------------------------------------------------------
    my_user_template = fields.Boolean(
        'Template',
        help='Used as template for extra menu list')
    my_group_id = fields.Many2one('res.groups', 'My Menu group')
    team_ids = fields.Many2many(
        'crm.team', relation='rel_user_team',
        column1='user_id', column2='team_id',
        string='Teams', help='Select team for filter orders')
    template_ids = fields.One2many(
        'res.users.my.template', 'user_id', 'User',
        help='Template list for default menu')
    my_menu_ids = fields.One2many(
        'res.users.my.template', 'my_user_id',
        'User', help='Menu generated from template user')
    my_default_team_id = fields.Many2one(
        'crm.team', string='Default Team', help='Default for this user')
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    @api.multi
    def get_user_domain_team(self, ):
        """ Return domain for user team selected
        """
        team_ids = [item.id for item in self[0].team_ids]
        return str([('team_id', 'in', team_ids)])

    @api.model
    def create_my_action(self, domain, origin_action, name):
        """ Generate similar domain action for origin_action forced
            Note: Domain is not changed
        """
        action_pool = self.env['ir.actions.act_window']

        # Domain integration:

        try:
            action = origin_action.domain
        except:
            action = '[]'
        if action == '[]':
            domain = str(domain)
        else:
            domain = '%s, %s' % (action[:-1], domain[1:])
        try:
            view_id = origin_action.view_id.id
        except:
            _logger.error(
                'Cannot found view for action: %s' % origin_action.name)
            return False

        return action_pool.create({
            'name': name,
            'type': origin_action.type,
            'help': origin_action.help,
            'binding_model_id': origin_action.binding_model_id.id,
            'binding_type': origin_action.binding_type,
            'view_id': view_id,
            'domain': domain,
            'context': origin_action.context,
            'res_id': origin_action.res_id,
            'res_model': origin_action.res_model,
            'src_model': origin_action.src_model,
            'target': origin_action.target,
            'view_mode': origin_action.view_mode,
            'view_type': origin_action.view_type,
            'usage': origin_action.usage,
            'limit': origin_action.limit,
            'search_view_id': origin_action.search_view_id.id,
            'filter': origin_action.filter,
            'auto_search': origin_action.auto_search,
            'multi': origin_action.multi,
            }).id

    @api.model
    def create_my_menu(self, my_action_id, my_group_id, name, sequence=10):
        """ Create menu item
        """
        menu_pool = self.env['ir.ui.menu']

        # Default action used to copy
        parent_menu = self.env.ref(
            'tyres_order_team_filter.menu_logistic_my_order_root')
        return menu_pool.create({
            'name': name,
            'active': True,
            'sequence': sequence,
            'parent_id': parent_menu.id,
            'action': 'ir.actions.act_window,%s' % my_action_id,
            'groups_id': [(6, 0, [my_group_id])],
            # 'parent_left' 'parent_right' 'web_icon'
            }).id

    # -------------------------------------------------------------------------
    # Button action:
    # -------------------------------------------------------------------------
    @api.multi
    def remove_my_menu(self):
        """ Delete all object created for my menu, user passed
        """
        for extra in self.my_menu_ids:
            extra.my_menu_id.unlink() # remove also action
        return self.my_menu_ids.unlink()

    @api.multi
    def load_template_menu(self):
        """ Load template menu found in template user
        """
        self.ensure_one()
        user = self[0]

        # Pool used:
        menu_pool = self.env['res.users.my.template']
        group_pool = self.env['res.groups']

        template_user = self.search([('my_user_template', '=', True)])
        if not template_user:
            raise odoo.exceptions.Warning(
                _('Please mark a user as template and add there menus'))

        templates = template_user[0].template_ids
        if not templates:
            raise odoo.exceptions.Warning(
                _('No template present in template user'))

        # ---------------------------------------------------------------------
        # 1. Create or get my group:
        # ---------------------------------------------------------------------
        self.remove_my_menu()  # remove previous
        domain = self.get_user_domain_team()  # get team domain

        # All group has this category owner:
        category_id = self.env.ref(
            'tyres_logistic_management.ir_module_category_logistic_my').id
        if user.my_group_id:
            my_group_id = user.my_group_id.id

            # Update some fields:
            user.my_group_id.write({
                'users': [(6, 0, [user.id, ])],
                'category_id': category_id,
                })
        else:
            my_group_id = group_pool.create({
                'name': _('My Order %s') % user.name,
                'comment': 'Group auto created from tyres_order_team_filter',
                'users': [(6, 0, [user.id, ])],
                'category_id': category_id,
                }).id
            user.my_group_id = my_group_id

        # ---------------------------------------------------------------------
        # 2. Add submenu as template:
        # ---------------------------------------------------------------------
        for template in templates:
            menu = template.template_menu_id
            name = template.force_name or menu.name

            # Create actions copy template:
            my_action_id = self.create_my_action(
                domain, menu.action, 'My action: %s' % name)

            if not my_action_id:
                _logger.error('Menu non created!')
                continue

            # Create menu:
            my_menu_id = self.create_my_menu(
                my_action_id, my_group_id, name, template.sequence)

            # Create record:
            menu_pool.create({
                'my_user_id': self.id,
                'my_action_id': my_action_id,
                'my_menu_id': my_menu_id,
                'my_sequence': template.sequence,
                })
        return
