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
import erppeek
import pdb
from datetime import datetime, timedelta

try:
    import ConfigParser
except:
    import configparser as ConfigParser


# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
cfg_file = os.path.expanduser('../odoo.cfg')

config = ConfigParser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')  # verify if it's necessary: getint

# -----------------------------------------------------------------------------
# Connect to ODOO:
# -----------------------------------------------------------------------------
odoo = erppeek.Client(
    'http://%s:%s' % (
        server, port),
    db=dbname,
    user=user,
    password=pwd,
)

pfu_pool = odoo.model('stock.pfu.assigned')
move_pool = odoo.model('stock.move')
quant_pool = odoo.model('stock.picking.delivery.quant')

# Clean assigned PFU
pdb.set_trace()
assigned_ids = pfu_pool.search([])
pfu_pool.unlink(assigned_ids)

# Clean Check in Move
checked_ids = move_pool.search([
    ('pfu_done', '=', True),
])
move_pool.write(checked_ids, {
    'pfu_done': False,
})

# Clean Check in Qant
checked_ids = quant_pool.search([
    ('pfu_done', '=', True),
])
quant_pool.write(checked_ids, {
    'pfu_done': False,
})

