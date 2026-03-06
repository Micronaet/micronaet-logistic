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
import ConfigParser
import time
import sys
import pdb
from datetime import datetime

pidfile = '/tmp/auto_print_daemon.pid'
log_exec_file = '/tmp/auto_print.log'
# os.system('mkdir -p ./log')  # Create log folder
log_exec_f = open(log_exec_file, 'a')


# -----------------------------------------------------------------------------
# Function:
# -----------------------------------------------------------------------------
def write_log(message, mode='info', log_file=None, verbose=True):
    """ Log on file
    """
    full_message = '%s - [%s] %s\n' % (
        datetime.now(), mode.upper(), message)
    if log_file:
        log_file.write(full_message)
    if verbose:
        print(full_message.strip())


# -----------------------------------------------------------------------------
# Check multi execution:
# -----------------------------------------------------------------------------
# A. Check if yet running:
pid = str(os.getpid())
if os.path.isfile(pidfile):
    message = '[%s] Invoice Daemon already running [%s]' % (pid, pidfile)
    write_log(message, log_file=log_exec_f)
    sys.exit()
else:
    message = '[%s] Invoice Daemon running [%s]' % (pid, pidfile)
    write_log(message, log_file=log_exec_f)

    # B. Create PID file:
    pid_f = open(pidfile, 'w')
    pid_f.write(pid)
    pid_f.close()

try:
    # -------------------------------------------------------------------------
    # Read configuration parameter:
    # -------------------------------------------------------------------------
    cfg_file = os.path.expanduser('../odoo.cfg')

    config = ConfigParser.ConfigParser()
    config.read([cfg_file])
    dbname = config.get('dbaccess', 'dbname')
    user = config.get('dbaccess', 'user')
    pwd = config.get('dbaccess', 'pwd')
    server = config.get('dbaccess', 'server')
    port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

    # -------------------------------------------------------------------------
    # Connect to ODOO:
    # -------------------------------------------------------------------------
    odoo = erppeek.Client(
        'http://%s:%s' % (server, port),
        db=dbname,
        user=user,
        password=pwd,
        )
    odoo.context = {
        'erppeek': True,
        # 'lang': 'it_IT',
    }
    order_pool = odoo.model('sale.order')
    company_pool = odoo.model('res.company')

    # -------------------------------------------------------------------------
    # Read parameters:
    # -------------------------------------------------------------------------
    company_ids = company_pool.search([])
    company = company_pool.browse(company_ids)[0]
    block = company.auto_print
    wait = company.auto_wait

    # -------------------------------------------------------------------------
    # Print order:
    # -------------------------------------------------------------------------
    auto_order_ids = order_pool.search([
        ('auto_print_order', '=', True)
    ])
    counter = 0
    for order_id in auto_order_ids:
        # Read order internally (maybe yet printed from ODOO)
        order = order_pool.browse(order_id)

        if order.locked_delivery:
            write_log('Order %s in locked delivery' % order.name, log_file=log_exec_f)
            continue  # Leave in automatic order

        if not order.carrier_ok:
            continue  # Jump this order

        if not order.carrier_supplier_id:  # No supplier no management delivery
            continue  # Jump this order

        if not order.auto_print_order:  # Yet printed
            # write_log(
            #    'Order %s not in ready status' % order.name,
            #    log_file=log_exec_f)

            # 6 mar. 2026: Micronaet remove raise error:
            # order.write_log_chatter_message(
            #    'Rimosso dagli automatici dato che non si trova in stato "Pronto"')
            #order_pool.write([order.id], {
            #    'auto_print_order': False,
            #})
            continue

        counter += 1  # Counter really printed record!

        # Print N order and wait after print block:
        if counter > block:
            counter = 1  # Restart
            write_log('In attesa per %s secondi' % wait, log_file=log_exec_f)
            time.sleep(wait)

        # Press the send to delivery button:
        try:
            if order.erppeek_workflow_ready_to_done_current_order():
                write_log('Elaborazione ordine %s' % order.name,
                          log_file=log_exec_f)
            else:
                write_log('Errore elaborazione ordine %s' % order.name,
                          log_file=log_exec_f)
        except:
            write_log('Errore non gestito ordine %s' % order.name,
                      log_file=log_exec_f)
            continue
finally:
    os.unlink(pidfile)
    message = '[%s] Invoice Daemon stopped [%s]\n' % (pid, pidfile)
    write_log(message, log_file=log_exec_f)
    if log_exec_f:
        log_exec_f.close()
