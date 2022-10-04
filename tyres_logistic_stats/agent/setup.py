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
import ConfigParser
from datetime import datetime, timedelta


try:
    mode = sys.argv[1]
except:
    print '''
    Error, launch as:
    python ./setup.py [MODE]
        mode = all (create > 10 and modify > today)
        mode = ready    (and pending)
        mode = done
    '''
    sys.exit()

log_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'log',
    )
os.system('mkdir -p %s' % log_path)
log_file = os.path.join(log_path, 'activity.log')
print 'Log file: %s' % log_file

log_f = open(log_file, 'a')

def log_event(log_f, mode, event='Start event'):
    ''' Write event
    '''
    log_f.write('%s. Mode %s: %s\n' % (
        datetime.now(),
        mode,
        event,
        ))

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
log_event(log_f, mode, 'Start update stats')

cfg_file = os.path.expanduser('../odoo.cfg')

config = ConfigParser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

now = datetime.now()
now_2 = now - timedelta(days=2)
now_4 = now - timedelta(days=4)
now_10 = now - timedelta(days=10)

now = now.strftime('%Y-%m-%d 00:00:00')
now_2 = now_2.strftime('%Y-%m-%d 00:00:00')
now_4 = now_4.strftime('%Y-%m-%d 00:00:00')
now_10 = now_10.strftime('%Y-%m-%d 00:00:00')

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
order_pool = odoo.model('sale.order')

if mode == 'all':
    domain = [
        #('write_date', '>=', now),
        ('create_date', '>=', now_10),
        ('logistic_state', 'not in', ('draft', 'order')),
        #('stats_level', '=', 'unset'), # Remove for ALL
        ]
elif mode == 'ready':
    domain = [
        ('logistic_state', '=', ('pending', 'ready')),
        ]
elif mode == 'done':
    domain = [
        ('create_date', '>=', now_4),
        ('logistic_state', '=', 'done'),
        ]
else:
    print('Mode error not found: %s' % mode)
    sys.exit()

order_ids = order_pool.search(domain)

total = len(order_ids)
print 'Connect to ODOO: Mode %s [Tot. %s]' % (
    mode, total)

i = 0
for order in order_pool.browse(order_ids):
    i += 1
    if i % 20 == 0:
        print 'Updated %s on %s' % (i, total)
    order.sale_order_refresh_margin_stats()

log_event(log_f, mode, 'Stop udate status: # %s record' % total)
