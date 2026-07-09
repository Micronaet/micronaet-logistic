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
import pdb
import sys

import erppeek
import codecs

from datetime import datetime

try:
    import ConfigParser as configparser
except:
    import configparser


# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
cfg_file = os.path.expanduser('../odoo.cfg')

config = configparser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

# -----------------------------------------------------------------------------
# Connect to ODOO:
# -----------------------------------------------------------------------------
print('Connect to ODOO')
odoo = erppeek.Client(
    'http://%s:%s' % (server, port),
    db=dbname,
    user=user,
    password=pwd,
    )

fees_pool = odoo.model('logistic.fees.api')
partner_ids = partner_pool.search([
    ('state', '=', 'draft'),
    ])

if not partner_ids:
    print('Not necessary')
    sys.exit()

now = str(datetime.now()).replace('/', '_').replace('-', '').replace(':', '_')
log_f = codecs.open('./log/partner_%s.log' % now, 'w', 'utf-8')
for fee in fees_pool.browse(fees_pool):
    fees_pool.api_sync([fee.id])
    message = 'Caricato scontrino ID: {}'.format(fee.id)
    print(message)
    log_f.write(message)
    log_f.write('\n')
    log_f.flush()


