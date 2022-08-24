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


class ResCompany(models.Model):
    """ API Management
    """
    _inherit = 'res.company'

    api_root_url = fields.Char(
        string='Api root url', size=60)
    api_username = fields.Char(
        string='Api username', size=60)
    api_password = fields.Char(
        string='Api password', size=60)
    api_token = fields.Text(
        string='Api token')
    api_management = fields.Boolean(
        'Gestione API',
        help='Attivazione gestione API gestionale per evitare passaggi CSV')
    api_invoice_area = fields.Boolean(
        'Fatturazione', help='Creazione fattura e recupero PDF stampa')
    api_fees_area = fields.Boolean(
        'Corrispettivi', help='Scarico corrispettivi fine giornata')
    api_pick_internal_area = fields.Boolean(
        'Scarico interno',
        help='Scarico merce assegnata agli ordini da magazzino interno'
             'Ex. cartella order/internal dove vengono messi i picking di'
             'assegnazione merce per gli ordini cliente (impegno di magazzino')
    # todo needed? not with api_pick_load_area
    # api_pick_refund = fields.Boolean(
    #     'Resi', help='Attivazione gestione resi con le API')
    api_pick_undo = fields.Boolean(
         'Undo', help='Gestire le operazioni di UNDO con le API')
    api_pick_load_area = fields.Boolean(
        'Carico a magazzino',
        help='Carico merce utilizzato in varie modalità:'
             'merce extra ordine che va caricata a magazzino,'
             'merce da caricare in sequito a operazioni di "undo",'
             'merce da caricare a magazzino per qualsiasi motivo.')
