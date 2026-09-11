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
from odoo import fields, api, models, exceptions
from odoo import tools
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class SaleOrderInherit(models.Model):
    """ Model name: Sale order
    """

    _inherit = 'sale.order'

    @api.multi
    def get_custom_delivery_missed_report_data(self):
        """ Metodo custom chiamato dal QWeb per generare N moduli per un singolo ordine.
            Se l'ordine ha 3 pacchi/spedizioni, restituirà 3 dizionari distinti,
            stampando così 3 moduli consecutivi con interruzione pagina.
        """
        self.ensure_one()

        # --------------------------------------------------------------------------------------------------------------
        # Loop for report page:
        # --------------------------------------------------------------------------------------------------------------
        order = self
        parcels_data = []
        for report_page in (order.carrier_tracking_ids_dpd or [False]):
            if not report_page:  # Empty report
                parcels_data.append({
                    'return_address': self.company_id.partner_id.contact_address or 'Indirizzo Sede Centrale',
                    'date_dispatch': self.confirmation_date or '',
                    'parcel_number': 'N/D',
                    'sender': self.company_id.name,
                    'receiver_address': self.partner_id.contact_address or '',
                    'receiver_email': self.partner_id.email or '',
                    'receiver_phone': self.partner_id.phone or '',
                    'middle_logo_base64': False,  # Eventuale logo
                })
            else:
                # Every report has one page:
                # TODO put right data:
                parcels_data.append({
                    'return_address': self.company_id.partner_id.contact_address or 'Indirizzo Sede Centrale',
                    'date_dispatch': self.confirmation_date or '',
                    'parcel_number': 'N/D',
                    'sender': self.company_id.name,
                    'receiver_address': self.partner_id.contact_address or '',
                    'receiver_email': self.partner_id.email or '',
                    'receiver_phone': self.partner_id.phone or '',
                    'middle_logo_base64': False,  # Eventuale logo
                })
        return parcels_data  # Always present!

    '''@api.multi
    def get_custom_delivery_missed_company_report_data(self, ):
        """ Get company data
        """
        self.ensure_one()
        company = self.company_id

        text = u"""%s
            %s%s
            %s - %s (%s)
            %s - Tel. %s
            Cod. Fisc. e P.I. %s
            """ % (
                (company.name or '').upper(),
                company.street or '',
                company.street2 or '',
                company.zip or '',
                company.city or '',
                company.state_id.name if company.state_id else '',
                (company.country_id.name if company.country_id else '').upper(),
                company.phone or '',
                company.vat or '',
                )
        return text.split('\n')
    '''
