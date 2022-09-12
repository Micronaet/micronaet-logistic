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

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DialogBoxWizard(models.TransientModel):
    """ Wizard for dialog box
    """
    _name = 'dialog.box.wizard'

    message = fields.Text('Message')
    mode = fields.Selection([
        ('ok', 'OK only'),
        ('yes_no', 'Yes / No'),
        ('cancel_confirm', 'Cancel / Confirm'),
        ], 'Mode', default='cancel_confirm')
    action = fields.Text('Action', help='Use self as reference for call')

    @api.model
    def open_dialog(self, message, action, title, mode='cancel_confirm'):
        """ Open dialog box procedure
        """
        # Create record
        current = self.create({
            'message': message,
            'mode': mode,
            'action': action,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': current.id,
            'res_model': 'dialog.box.wizard',
            # 'view_id': view_id, # False
            'views': [(False, 'form')],
            'domain': [],
            'context': self.env.context,
            'target': 'new',
            'nodestroy': False,
            'flags': {
                'form': {'action_buttons': False},
                }
            }

    # --------------------
    # Wizard button event:
    # --------------------
    def action_go(self):
        """ Event for button done
        """
        return eval(self.action)
