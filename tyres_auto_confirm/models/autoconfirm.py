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
import pdb
import logging
from datetime import datetime
from odoo import api, fields, models, tools, exceptions, SUPERUSER_ID
from odoo.tools.translate import _
from dateutil.easter import easter
_logger = logging.getLogger(__name__)


class AutoConfirmTemplate(models.Model):
    """ Auto confirm working template
    """
    _name = 'auto.confirm.template'
    _description = 'Working template'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Name', size=35, required=True)
    note = fields.Text(string='Note')


class AutoConfirmTemplateLine(models.Model):
    """ Auto confirm working template line
    """
    _name = 'auto.confirm.template.line'
    _description = 'Working line'
    _rec_name = 'day'
    _order = 'day, from_hour'

    day = fields.Selection(
        string='Day',
        selection=[
            ('mon', 'Monday'),
            ('tue', 'Tuesday'),
            ('wed', 'Wednesday'),
            ('thu', 'Thursday'),
            ('fri', 'Friday'),
            ('sat', 'Saturday'),
            ('sun', 'Sunday'),
        ],
        required=True,
    )
    from_hour = fields.Float(
        string='From hour (morning)',
        required=True,
    )
    to_hour = fields.Float(
        string='From hour (morning)',
        required=True,
    )
    template_id = fields.Many2one(
        comodel_name='auto.confirm.template',
        string='Template',
    )


class AutoConfirmWorkingRelations(models.Model):
    """ Auto confirm working template relations
    """
    _inherit = 'auto.confirm.template'

    day_ids = fields.One2many(
        comodel_name='auto.confirm.template.line',
        inverse_name='template_id',
        string='Days'
    )


class AutoConfirmPeriod(models.Model):
    """ Auto period
    """
    _name = 'auto.confirm.period'
    _description = 'Auto confirm period'
    _rec_name = 'name'
    _order = 'passed, from_date'

    name = fields.Char(string='Name', size=35)
    passed = fields.Boolean(
        string='Passed',
        help='If range date is passed remove from list'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        )
    from_date = fields.Date(
        string='From date',
        required=True)
    to_date = fields.Date(
        string='To date',
        required=True)


class ResCompany(models.Model):
    """ Add configuration part
    """
    _inherit = 'res.company'

    # Button event:
    @api.multi
    def setup_this_year(self):
        """ Create this year date (not used for now)
        """
        period_pool = self.env['auto.confirm.period']
        year = fields.Datetime.now()[:4]

        date_excluded = {
            ('01-01', ): 'Capodanno',
            ('01-06', ): 'Befana',
            ('04-25', ): '25 Aprile',
            ('05-01', ): 'I Maggio',
            ('06-02', ): 'Festa della Repubblica',
            ('08-15', ): 'Ferragosto',
            ('12-08', ): 'Immacolata concezione',
            ('12-25', '12-26'): 'Natale',
        }
        easter_date = easter(int(year))
        easter_record = '%02d-%02d' % (easter_date.month, easter_date.day)
        date_excluded[easter_record] = 'Pasqua'

        if self.patron_day:
            patron_day = self.patron_day
            date_excluded[patron_day] = 'Festa patronale'

        for date in sorted(date_excluded, key=lambda r: r[0]):
            if len(date) == 2:
                from_date, to_date = date
            else:
                from_date = to_date = date
            name = date_excluded[date]
            periods = period_pool.search([('from_date', '=', from_date)])
            data = {
                'name': name,
                'company_id': self.env.user.company_id.id,
                'from_date': '{}-{}'.format(year, from_date),
                'to_date': '{}-{}'.format(year, to_date),
                }
            if periods:
                period_pool.write(data)
            else:
                period_pool.create(data)
        return True

    @api.multi
    def enable_auto_confirm(self):
        """ Create this year date
        """
        line = self.env['auto.confirm.template.line']

        translate = [
            'sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

        company = self
        gmt_correct = company.auto_gmt_correct
        daylight_correct = -1 if company.auto_daylight_correct else 0
        hour_correct = gmt_correct + daylight_correct

        now = datetime.now()
        hour = (now.hour - daylight_correct - gmt_correct) + now.minute / 60.0
        weekday = translate[now.isoweekday()]
        lines = line.search([
            ('day', '=', weekday),
            ('to_hour', '>', hour),
        ])
        if not lines:
            raise exceptions.UserError(
                'Not activated, no working period available today')

        now_text = now.strftime('%Y-%m-%d')
        from_hour = lines[0].from_hour + hour_correct
        to_hour = lines[0].to_hour + hour_correct
        auto_start_period = '%s %02d:%02d:00' % (
            now_text,
            int(from_hour),
            int((from_hour - int(from_hour)) * 60.0),
        )
        auto_end_period = '%s %02d:%02d:00' % (
            now_text,
            int(to_hour),
            int((to_hour - int(to_hour)) * 60.0),
        )
        # Put pending order in queue:
        order_pool = self.env['sale.order']
        sale_orders = order_pool.search([
            ('manage_office_id.code', '=', 'workshop'),
            ('logistic_source', 'not in', ('refund',)),
            ('logistic_state', 'in', ('ready', )),
            ('logistic_done', '=', False),
            ('logistic_source', '!=', 'internal'),
        ])
        if sale_orders:
            for order in sale_orders:
                order.write({
                    'auto_print_order': True,
                })
                order.write_log_chatter_message(
                    'Messo nella coda di stampa automatica '
                    '(attivato ora il periodo di stampa auto)'
                )

        return self.write({
            'auto_state': 'enabled',
            'auto_start_period': auto_start_period,
            'auto_end_period': auto_end_period,
        })

    @api.multi
    def disable_auto_confirm(self):
        """ Create this year date
        """
        # Put pending order in queue removed:
        order_pool = self.env['sale.order']
        sale_orders = order_pool.search([
            ('auto_print_order', '=', True),
        ])
        for order in sale_orders:
            order.write({
                'auto_print_order': False,
            })
            order.write_log_chatter_message(
                'Timeout, tolto dalla coda di stampa automatica '
                '(fuori periodo)'
            )
            _logger.warning('Removed from auto %s' % order.name)

        return self.write({
            'auto_state': 'disabled',
            'auto_start_period': False,
            'auto_end_period': False,
        })

    @api.multi
    def check_still_enable(self):
        """ Check if operation need to be still active
        """
        return True

    @api.multi
    def check_exclude_now_period(self):
        """ Check if now can enable the auto button
        """
        return self.write({'auto_enabled': False})

    # Default function:
    '''@api.multi
    def get_default_auto_group(self):
        """ Init setup for basic management group
        """
        group_id = self.env.ref(
            'tyres_auto_confirm.group_auto_confirm_manager').id
        return group_id'''

    @api.multi
    def get_pending_autoconfirmed_order(self):
        """ Auto order pending for printing
        """
        return self.env['sale.order'].search_count([
            ('auto_print_order', '=', True),
        ])

    # Columns:
    auto_gmt_correct = fields.Integer(
        string='Correzione GMT',
        help='Ore aggiunte all\'orario effettivo per salvare in GMT',
        default=-1,
    )
    auto_daylight_correct = fields.Boolean(
        string='Ora legale attiva',
        help='E\' presente l\'ora legale',
    )
    auto_pending_order = fields.Integer(
        string='Pending order',
        help='Order marked for being printed automatically',
        compute='get_pending_autoconfirmed_order',
    )
    patron_day = fields.Char(
        string='Patron day',
        help='Write patron day in format MM-DD, ex.: 02-15 for 15 feb.',
        default='02-15',
    )
    auto_start_period = fields.Datetime(
        string='Start date time',
        help='When enabled this date time is the start of the auto period'
             '(used to check if the button need to be disabled)'
        )
    auto_end_period = fields.Datetime(
        string='End date time',
        help='When enabled this date time is the end of the auto period'
             '(used to check if the button need to be disabled)'
        )
    auto_period = fields.Integer(
        string='Auto period (min.)',
        help='Auto period for enable auto go in delivery',
        default=30,
        required=True)
    auto_print = fields.Integer(
        string='Auto print block',
        help='Every list of ready order will be print with block of X items',
        default=3,
        required=True)
    auto_wait = fields.Integer(
        string='Auto print wait',
        help='All printable orders will be spliced in blocks, every block wait'
             'X seconds before print next',
        default=10,
        required=True)
    auto_group = fields.Many2one(
        comodel_name='res.groups',
        string='Auto group',
        help='Group for user that can manage auto button',
        # default=lambda s: s.get_default_auto_group(),
        )
    date_ids = fields.One2many(
        comodel_name='auto.confirm.period',
        inverse_name='company_id',
        string='Exclude date',
        help='Exclude date list'
    )
    template_id = fields.Many2one(
        comodel_name='auto.confirm.template',
        string='Template',
        help='Template for working period'
        )
    auto_state = fields.Selection([
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
        ], string='State', default='disabled',
        help='Orders go in delivery when ready automatically',
    )


class SaleOrderAutoPrint(models.Model):
    """ Model name: Sale Order
    """

    _inherit = 'sale.order'

    auto_print_order = fields.Boolean(
        string='Auto print',
        help='Auto print order (go in delivery)',
    )

    # Override:
    @api.multi
    def workflow_manual_order_pending(self):
        """ Override original action just to test if there's some dropship
            request, so order will be managed in office
        """
        manage_pool = self.env['sale.order.manage.office']
        manage_offices = manage_pool.search([
            ('code', '=', 'office'),
        ])
        if not manage_offices:
            raise exceptions.UserError(
                'Non esiste la gestione ufficio in anagrafica, inserirla!')
        manage_office_id = manage_offices[0].id
        for order in self:
            dropship = False
            for line in order.order_line:
                for purchase in line.purchase_split_ids:
                    if purchase.dropship_manage:
                        _logger.warning('Dropship manage, managed in office!')
                        dropship = True
                        order.write({
                            'manage_office_id': manage_office_id,
                        })
                        break  # Order (line) managed in dropship
                if dropship:
                    break
        return super(SaleOrderAutoPrint, self).workflow_manual_order_pending()

    @api.multi
    def logistic_check_and_set_ready(self):
        """ Override original action for put in auto print
            TODO use filter?
            ('logistic_state', '=', 'ready'),
            ('locked_delivery', '=', False),
            ('logistic_source', 'not in', ('refund', ))
        """
        # Call super method:
        res = super(SaleOrderAutoPrint, self).logistic_check_and_set_ready()

        # Reload order:
        now = fields.Datetime.now()
        company = self.env.user.company_id
        auto_start = company.auto_start_period
        auto_stop = company.auto_end_period
        if auto_start and auto_stop:
            _logger.info(
                '\n\n\n Set ready: %s [%s:%s]\n\n\n' % (
                    now, auto_start, auto_stop))
            if auto_start <= now <= auto_stop:
                # Setup order for printing:
                order_2_print = self.search([
                    ('logistic_state', '=', 'ready'),
                    ('logistic_source', 'not in', ('refund', )),
                    ('manage_office_id.code', '=', 'workshop'),  # only WS!

                    ('id', 'in', self.mapped('id')),
                ])
                order_2_print.write({
                    'auto_print_order': True,
                })
                _logger.info(
                    '\n Done: %s\n\n' % len(order_2_print))
            else:
                # If extra range disable:
                company.disable_auto_confirm()
        return res

    @api.multi
    def workflow_ready_to_done_current_order(self):
        """ After ready to done remove auto print (if present)
        """
        order = self
        erppeek = self.env.context.get('erppeek')
        if erppeek:
            _logger.info('Erppeek mode enabled!')
        if order.locked_delivery:
            _logger.error('Cannot print, locked delivery!')
            return False

        # Check if is in auto period (instead put in queue)
        if not erppeek and order.company_id.auto_state == 'enabled' and \
                order.manage_office_id.code == 'workshop':
            return order.write({
                'auto_print_order': True,
            })
        else:
            # Call super method:
            res = super(SaleOrderAutoPrint, self).\
                workflow_ready_to_done_current_order()
            self.write({
                'auto_print_order': False,
            })
            return res

    @api.multi
    def erppeek_workflow_ready_to_done_current_order(self):
        """ After ready to done remove auto print (if present)
        """
        order = self
        if not order.auto_print_order:
            _logger.error('Order not in auto print %s!' % order.name)
            return False

        order.workflow_ready_to_done_current_order()
        order.write_log_chatter_message('Lancio stampa automatica ordine')
        return True
