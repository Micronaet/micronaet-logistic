#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
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
###############################################################################

import os
import sys
import odoo
import logging
import pdb
from odoo import models, fields, api
from odoo.tools.translate import _

# Converter from part to JSON name:
iban_field_available = {
    'country': 'isoiban',
    'abi': 'abi',
    'cab': 'cab',
    'account': 'bankAccount',
    'cin': False,  # Not used
    'check': False,  # Not used
}

_logger = logging.getLogger(__name__)


class ResPartnerBankInherit(models.Model):
    """ Model name: Partner bank
    """
    _inherit = 'res.partner.bank'

    @api.model
    def iban_breakdown(self, country):
        """ Split bank data also with check country
        """
        bank = self
        separator = '|'
        iban = (bank.acc_number or '').strip().replace(' ', '')  # Clean IBAN
        iban_part_data = {  # Empty block
            # Bank part:
            'iban': iban,

            # Split part:
            'abi': '',
            'cab': '',
            'bankAccount': '',
        }

        # Read format:
        iban_format = country.iban_format.split(separator)
        iban_field = country.iban_field.split(separator)
        total = len(iban_field)

        start = 0
        for i in range(total):
            size = int(iban_format[i].strip())
            end = start + size

            # Extract part and associate with field:
            text_part = iban[start:end]
            start = end  # New start!
            field_name = iban_field_available.get(iban_field[i])
            if not field_name:
                continue  # Not used

            iban_part_data[field_name] = text_part
        return iban_part_data


class ResCountryInherit(models.Model):
    """ Model name: Extend Res Country
    """
    _inherit = 'res.country'

    def get_iban_check(self):
        """ Check IBAN data reference
        """
        separator = '|'
        iban_check = ''
        self.ensure_one()
        if not self.iban_management:
            self.iban_check = iban_check

        # --------------------------------------------------------------------------------------------------------------
        #                                       Check validator:
        # --------------------------------------------------------------------------------------------------------------
        # Format must be digit:
        iban_format = self.iban_format or ''
        if not iban_format.replace(separator, '').isdigit():
            iban_check += 'Nelle parti del formato devono essere presenti solo numeri e il divisore | \n'

        # --------------------------------------------------------------------------------------------------------------
        # Check part:
        # --------------------------------------------------------------------------------------------------------------
        iban_format_part = iban_format.split(separator)

        # Format and Field must have same items:
        iban_field = (self.iban_field or '').lower()
        iban_field_part = iban_field.split(separator)
        if len(iban_format_part) != len(iban_field_part):
            iban_check += 'Le parti del formato e dei campi differiscono di numero\n'

        # Fields name must in a valid list:
        wrong_field = ''
        for field in iban_field_part:
            if field not in iban_field_available:
                wrong_field += '[{}] '.format(field)
        if wrong_field:
            iban_check += 'Nomi di campi non autorizzati: {}\n'.format(wrong_field)

        self.iban_check = iban_check

    # ------------------------------------------------------------------------------------------------------------------
    # Columns:
    # ------------------------------------------------------------------------------------------------------------------
    iban_management = fields.Boolean('Gestione IBAN')
    iban_format = fields.Char(
        'Formato IBAN', size=100,
        # default='2|2|1|5|5|12',
        help='Indicare le parti con lunghezza blocco separati con |, es.: 2|2|1|5|5|12')
    iban_field = fields.Char(
        'Campi IBAN', size=180,
        # default='country|check|cin|abi|cab|account',
        help='Indicare i campi delle parti del formato sempre separati con |, '
             'es.: country|check|abi|cab|account'
             'I possibili valori sono: country, check, cin, abi, cab, account')
    iban_check = fields.Char('Controllo dati', compute=get_iban_check)

