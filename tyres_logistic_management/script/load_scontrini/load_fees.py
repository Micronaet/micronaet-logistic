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

# ======================================================================================================================
# LOCK FILE Management (first operation)
# ======================================================================================================================
lock_file = './script_running.lock'
if os.path.exists(lock_file):
    print("Script gia in esecuzione (Semaforo attivo). Uscita.")
    sys.exit()

# Crea il file semaforo
with open(lock_file, 'w') as f:
    f.write(str(datetime.now()))

# ----------------------------------------------------------------------------------------------------------------------
# Read configuration parameter:
# ----------------------------------------------------------------------------------------------------------------------
cfg_file = os.path.expanduser('../odoo.cfg')

config = configparser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')  # verify if it's necessary: getint

not_necessary = False
try:
    # ==================================================================================================================
    # Connect to ODOO:
    # ==================================================================================================================
    print('Connect to ODOO')
    odoo = erppeek.Client(
        'http://%s:%s' % (server, port),
        db=dbname,
        user=user,
        password=pwd,
    )

    fees_pool = odoo.model('logistic.fees.api')
    fees_ids = fees_pool.search([
        ('state', '=', 'draft'),
        ('direct_fee', '=', False),
    ])

    if not fees_ids:
        print('Not necessary')
        not_necessary = True  # Segnaliamo che non c'è lavoro da fare senza chiamare sys.exit() qui

    # Eseguiamo l'elaborazione solo se ci sono dati
    if not not_necessary:
        now = str(datetime.now()).replace('/', '_').replace('-', '').replace(':', '_')
        log_f = codecs.open('./log/scontrino_%s.log' % now, 'w', 'utf-8')
        for fee in fees_pool.browse(fees_ids):
            fee_id = fee.id
            fees_pool.api_sync([fee_id])
            message = 'Caricato scontrino ID: {}'.format(fee_id)
            print(message)
            log_f.write(message)
            log_f.write('\n')
            log_f.flush()
finally:
    # Pulizia del file semaforo: viene eseguita SEMPRE
    if os.path.exists(lock_file):
        os.remove(lock_file)
