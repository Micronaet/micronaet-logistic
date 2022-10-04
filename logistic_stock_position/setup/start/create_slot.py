# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
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
import erppeek

remove_char = ('\t', '\n')

cfg_file = os.path.expanduser('../odoo.cfg')

try: # Pyton 2.7
    import ConfigParser
    config = ConfigParser.ConfigParser()
except: # Python 3 (pip install ConfigParser)
    import configparser
    config = configparser.ConfigParser()

# -----------------------------------------------------------------------------
# From config file:
# -----------------------------------------------------------------------------
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

# -----------------------------------------------------------------------------
# Connect to ODOO:
# -----------------------------------------------------------------------------
odoo = erppeek.Client(
    'http://%s:%s' % (server, port),
    db=dbname,
    user=user,
    password=pwd,
    )
partner_pool = odoo.model('res.partner')
table_pool = odoo.model('stock.location.table')
slot_pool = odoo.model('stock.location.slot')
rel_pool = odoo.model('stock.table.slot.rel')

# Supplier, suffix, defauls, SL x 5
database = [
    ['ACSUD', 'AC-', 'T1', 'T1.UP1', 'T1.UP2', 'T1.APT.1', 'T1.APT.2', 'T1.APT.T'],
    ['LAMPA', 'LA-', 'T2', 'T2.UP1', 'T2.UP2', 'T2.APT.1', 'T2.APT.2', 'T2.APT.T'],
    ['SPARMART', 'SP-', 'T3', 'T3.UP1', 'T3.UP2', 'T3.APT.1', 'T3.APT.2', 'T3.APT.T'],
    ['GIVI', 'GV-', 'T4', 'T4.UP1', 'T4.UP2', 'T4.APT.1', 'T4.APT.2', 'T4.APT.T'],
    ['CAMAMOTO', 'CA-', 'T5', 'T5.UP1', 'T5.UP2', 'T5.APT.1', 'T5.APT.2', 'T5.APT.T'],
    ['SGR', 'SG-', 'T6', 'T6.UP1', 'T6.UP2', 'T6.APT.1', 'T6.APT.2', 'T6.APT.T'],
    ['ATHENA', 'AT-', 'T7', 'T7.UP1', 'T7.UP2', 'T7.APT.1', 'T7.APT.2', 'T7.APT.T'],
    ['MANDELLI', 'MN-', 'T8', 'T8.UP1', 'T8.UP2', 'T8.APT.1', 'T8.APT.2', 'T8.APT.T'],

    ['KAPPA', 'KK-', 'T4', 'T4.UP1', 'T4.UP2', 'T4.APT.1', 'T4.APT.2', 'T4.APT.T'],
    ['BERGAMASCHI', 'BG-', 'T6', 'T6.UP1', 'T6.UP2', 'T6.APT.1', 'T6.APT.2', 'T6.APT.T'],
    ['RMS', 'RM-', 'T6', 'T6.UP1', 'T6.UP2', 'T6.APT.1', 'T6.APT.2', 'T6.APT.T'],
    ['LARSSON', 'LR-', 'T7', 'T7.UP1', 'T7.UP2', 'T7.APT.1', 'T7.APT.2', 'T7.APT.T'],
    ['RICAMBIO', 'RR-', 'T7', 'T7.UP1', 'T7.UP2', 'T7.APT.1', 'T7.APT.2', 'T7.APT.T'],
    ['FACO', 'FC-', 'T8', 'T8.UP1', 'T8.UP2', 'T8.APT.1', 'T8.APT.2', 'T8.APT.T'],
    ]

for record in database:
    supplier = record[0]
    prefix = record[1]
    table = record[2]
    slot_list = record[2:]

    # -------------------------------------------------------------------------
    # Create partner:
    # -------------------------------------------------------------------------
    partner_ids = partner_pool.search([('name', '=', supplier)])
    if partner_ids:
        partner_id = partner_ids[0]
    else:
        partner_id = partner_pool.create({
            'name': supplier,
            'supplier': True,
            'is_company': True,
            #'product_suffix': prefix.strip('-'),
            }).id

    # -------------------------------------------------------------------------
    # Create table:
    # -------------------------------------------------------------------------
    table_ids = table_pool.search([('code', '=', table)])
    if table_ids:
        table_id = table_ids[0]
    else:
        table_id = table_pool.create({
            'code': table,
            'name': 'Tavolo %s' % table[-1],
            }).id

    # -------------------------------------------------------------------------
    # Update default table for supplier:
    # -------------------------------------------------------------------------
    partner_pool.write(partner_id, {
        'delivery_table_id': table_id,
        })

    # -------------------------------------------------------------------------
    # Create slot for ready:
    # -------------------------------------------------------------------------
    mode = 'supplier'
    sequence = 0
    for slot in slot_list:
        slot_ids = slot_pool.search([
            ('name', '=', slot),
            ])
        if slot_ids:
            slot_id = slot_ids[0]
        else:
            slot_id = slot_pool.create({
                'mode': mode,
                'name': slot,
                }).id

        # ---------------------------------------------------------------------
        # Link slot to table
        # ---------------------------------------------------------------------
        if mode == 'supplier':
            table_pool.write(table_id, {
                'default_slot_id': slot_id,
                })
        else:
            rel_ids = rel_pool.search([
                ('table_id', '=', table_id),
                ('slot_id', '=', slot_id),
                ])

            if rel_ids:
                rel_pool.write(rel_ids, {
                    'sequence': sequence,
                    })
            else:
                try:
                    rel_pool.create({
                        'sequence': sequence,
                        'table_id': table_id,
                        'slot_id': slot_id,
                        })
                except:
                    pass#print 'Error table_id %s slot_id %s' % (table_id, slot_id)

        mode = 'pending'  # other is pending
        sequence += 1
