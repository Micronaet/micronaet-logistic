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
import openerp
import logging
from openerp import models, fields
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _
from openerp.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare,
    )


_logger = logging.getLogger(__name__)


class MmacBrand(models.Model):
    """ Model name: Brand
    """

    _inherit = 'mmac_brand'

    owner = fields.Char(string='Proprietario', size=80)
    street = fields.Char(string='Indirizzo', size=100)
    city = fields.Char(string='Città', size=80)
    zipcode = fields.Char(string='CAP', size=20)
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Nazione')


class ResCompany(models.Model):
    """ Model name: ResCompany
    """

    _inherit = 'res.company'

    # -------------------------------------------------------------------------
    # COLUMNS:
    # -------------------------------------------------------------------------
    # report_free_export = fields.Text('Report text: Free Export')
    # -------------------------------------------------------------------------
