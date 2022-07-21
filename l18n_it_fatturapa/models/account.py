#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# Copyright (C) 2014 Davide Corio <davide.corio@lsweb.it>
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
import logging
import string
from odoo import api, models, fields
from odoo import tools
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class FatturapaFormat(models.Model):
    """ Fattura PA Format and utility for formatting
        ['1.1.3']
    """
    _name = 'fatturapa.format'
    _description = 'FatturaPA Format'

    # -------------------------------------------------------------------------
    #                             Format utility:
    # -------------------------------------------------------------------------
    @api.model
    def format_date(self, value):
        """ Format date ISO mode
        """
        value = value or ''
        return value[:10]

    @api.model
    def format_decimal(self, value, decimal=2):
        """ Format float data
        """
        if not value:
            return '0.00'

        # if comes as a string, ex.: '12.045'
        if type(value) in (str, ):  # unicode):
            try:
                value = float(value)
            except:
                return '0.00'

        mask = '%%10.%sf' % decimal
        return (mask % value)

    @api.model
    def format_integer(self, value):
        """ Format integer data
        """
        return value

    @api.model
    def format_string(self, value, size=0):
        """ Format text data
            Char used: [a:z, A:Z]
        """
        value = value or ''
        if size:
            return value[:size]
        else:
            return value

    @api.model
    def format_normalized_string(self, value, size=0):
        """ Format text data
        """
        value = value or ''
        if size:
            return value[:size]
        else:
            return value
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=5)
    doc_part = fields.Text('Doc Part')


class FatturapaDocumentType(models.Model):
    """ Document type (invoice, credit note):
        ['2.1.1.1'] (Startup data)
    """
    _name = 'fatturapa.document_type'
    _description = 'FatturaPA Document Type'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=4)


class FatturapaPaymentTerm(models.Model):
    """ Payment term
        ['2.4.1']
    """
    _name = 'fatturapa.payment_term'
    _description = 'FatturaPA Payment Term'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=4)


class FatturapaPaymentMethod(models.Model):
    """ Payment method
        ['2.4.2.2']
    """
    _name = 'fatturapa.payment_method'
    _description = 'FatturaPA Payment Method'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=4)

class WelfareFundType(models.Model):
    """ Welfare fund
        ['2.1.1.7.1']
    """
    _name = 'welfare.fund.type'
    _description = 'welfare fund type'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Name')
    description = fields.Char('Description')


class FatturapaFiscalPosition(models.Model):
    """ Fiscal position:
        ['2.1.1.7.7', '2.2.1.14']
    """
    _name = 'fatturapa.fiscal_position'
    _description = 'FatturaPA Fiscal Position'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=4)


class AccountPaymentTerm(models.Model):
    """ Payment term
        ['2.4.2.2']
    """
    _inherit = 'account.payment.term'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    fatturapa_pt_id = fields.Many2one(
        'fatturapa.payment_term', string='FatturaPA Payment Term')
    fatturapa_pm_id = fields.Many2one(
        'fatturapa.payment_method', string='FatturaPA Payment Method')


class ProductUom(models.Model):
    """ Product UOM
        ['2.2.1.6']
    """
    _inherit = 'product.uom'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    fatturapa_code = fields.Char('Fattura PA code', size=10)


class ResPartner(models.Model):
    """ Extra data for partner
    """
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    # REA:
    rea_office = fields.Many2one(
        'res.country.state', string='Office Province')
    rea_code = fields.Char('REA Code', size=20)
    rea_capital = fields.Float('Capital')
    rea_member_type = fields.Selection(
        [('SU', 'Unique Member'),
         ('SM', 'Multiple Members')], 'Member Type')
    rea_liquidation_state = fields.Selection(
        [('LS', 'In liquidation'),
         ('LN', 'Not in liquidation')], 'Liquidation State')

    # Fattura PA:
    fatturapa_name = fields.Char('Partner name', size=80)
    fatturapa_surname = fields.Char('Partner surname', size=80)

    fatturapa_unique_code = fields.Char('Unique code SDI', size=7)
    fatturapa_pec = fields.Char('Fattura PA PEC', size=120)
    fatturapa_fiscalcode = fields.Char(
        'Fattura fiscal code', size=16)
    fatturapa_private_fiscalcode = fields.Char(
        'Fattura private fiscal code', size=16)

    eori_code = fields.Char('EORI Code', size=20)
    license_number = fields.Char('License Code', size=20)
    # 1.2.6 RiferimentoAmministrazione
    pa_partner_code = fields.Char('PA Code for partner', size=20)
    # 1.2.1.4
    register = fields.Char('Professional Register', size=60)
    # 1.2.1.5
    register_province = fields.Many2one(
        'res.country.state', string='Register Province')
    # 1.2.1.6
    register_code = fields.Char('Register Code', size=60)
    # 1.2.1.7
    register_regdate = fields.Date('Register Registration Date')
    # 1.2.1.8
    register_fiscalpos = fields.Many2one(
        'fatturapa.fiscal_position',
        string='Register Fiscal Position')

    # -------------------------------------------------------------------------
    # Contraints:
    # -------------------------------------------------------------------------
    _sql_constraints = [
        ('rea_code_uniq', 'unique (rea_code, company_id)',
         'The rea code code must be unique per company !'),
        ]


class ResCompany(models.Model):
    """ Company data
    """

    _inherit = 'res.company'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    fatturapa_fiscal_position_id = fields.Many2one(
        'fatturapa.fiscal_position', 'Fiscal Position',
        help='Fiscal position used by FatturaPA',
        )
    fatturapa_format_id = fields.Many2one(
        'fatturapa.format', 'Format',
        help='FatturaPA Format',
        )
    fatturapa_sequence_id = fields.Many2one(
        'ir.sequence', 'Sequence',
        help='Il progressivo univoco del file è rappresentato da una '
             'stringa alfanumerica di lunghezza massima di 5 caratteri '
             'e con valori ammessi da "A" a "Z" e da "0" a "9".',
        )
    fatturapa_art73 = fields.Boolean('Art73')
    fatturapa_pub_administration_ref = fields.Char(
        'Public Administration Reference Code', size=20,
        )
    fatturapa_rea_office = fields.Many2one('res.country.state',
        related='partner_id.rea_office', string='REA office')
    fatturapa_rea_number = fields.Char(
        related='partner_id.rea_code', string='Rea Number')
    fatturapa_rea_capital = fields.Float(
        related='partner_id.rea_capital', string='Rea Capital')
    fatturapa_rea_partner = fields.Selection([
        ('SU', 'Unique Member'),
        ('SM', 'Multiple Members'),
        ], related='partner_id.rea_member_type', string='Member Type')
    fatturapa_rea_liquidation = fields.Selection([
        ('LS', 'In liquidation'),
        ('LN', 'Not in liquidation'),
        ], related='partner_id.rea_liquidation_state',
        string='Liquidation State')
    fatturapa_vat_sender = fields.Char('VAT Sender', size=13)

    fatturapa_tax_representative = fields.Many2one(
        'res.partner', 'Legal Tax Representative'
        )
    fatturapa_sender_partner = fields.Many2one(
        'res.partner', 'Third Party/Sender'
        )


class AccountFiscalPosition(models.Model):
    """ Fattura PA for fiscal position
    """
    _inherit = 'account.fiscal.position'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    fatturapa = fields.Boolean('Fattura PA', help='Managed with Fattura PA')
    fatturapa_empty_code = fields.Char('Empty code',
        help='Ex. XXXXXXX for not Italy, 0000000 for Italy',
        default='0000000')
    invoice_id = fields.Many2one(
        'fatturapa.document_type', 'Invoice document type')
    credit_note_id = fields.Many2one(
        'fatturapa.document_type', 'Credit note document type')


class AccountTax(models.Model):
    """ Account tax fattura PA data
    """
    _inherit = 'account.tax'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    non_taxable_nature = fields.Selection([
        ('N1', 'escluse ex art. 15'),
        ('N2', 'non soggette'),
        ('N3', 'non imponibili'),
        ('N4', 'esenti'),
        ('N5', 'regime del margine'),
        ('N6', 'inversione contabile (reverse charge)'),
        ], string="Non taxable nature")
    payability = fields.Selection([
        ('I', 'Immediate payability'),
        ('D', 'Deferred payability'),
        ('S', 'Split payment'),
        ], string="VAT payability")
    law_reference = fields.Char(
        'Law reference', size=128)

    """@api.model
    def get_tax_by_invoice_tax(self, invoice_tax):
        if ' - ' in invoice_tax:
            tax_descr = invoice_tax.split(' - ')[0]
            tax_ids = self.search(cr, uid, [
                ('description', '=', tax_descr),
                ], context=context)
            if not tax_ids:
                raise orm.except_orm(
                    _('Error'), _('No tax %s found') %
                    tax_descr)
            if len(tax_ids) > 1:
                raise orm.except_orm(
                    _('Error'), _('Too many tax %s found') %
                    tax_descr)
        else:
            tax_name = invoice_tax
            tax_ids = self.search(cr, uid, [
                ('name', '=', tax_name),
                ], context=context)
            if not tax_ids:
                raise orm.except_orm(
                    _('Error'), _('No tax %s found') %
                    tax_name)
            if len(tax_ids) > 1:
                raise orm.except_orm(
                    _('Error'), _('Too many tax %s found') %
                    tax_name)
        return tax_ids[0]"""


class StockPicking(models.Model):
    """ Stock picking extract
    """
    _inherit = 'stock.picking'

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    #@api.multi
    #def get_next_xml_id(self):
    #    ''' Return next number code exadecimal 5 char
    #    '''
    #    self.xml_code

    """@api.multi
    def get_next_xml_id(self):
        ''' Generate CODE progress number
        '''
        # Generate seed data:
        seed = string.digits + string.ascii_uppercase + string.ascii_lowercase
        base = len(seed)

        # Get counter:
        sequence_pool = self.env['ir.sequence']
        sequence = sequence_pool.search([
            ('code', '=', 'stock.picking.fatturapa'),
            ])
        remain = int(sequence.next_by_id())
        res = ''
        while remain >= base:
            division = remain // base             
            remain = remain % base 
            res += seed[division]
        res += seed[division]
        return '0' * (5 - len(res)) + res
    """

    @api.multi
    def get_next_xml_id(self):
        """ Return next number code exadecimal 5 char
        """
        seed = string.digits + string.ascii_uppercase
        base = len(seed)

        sequence_pool = self.env['ir.sequence']
        sequence = sequence_pool.search([
            ('code', '=', 'stock.picking.fatturapa'),
            ])

        res = ''
        remain = int(sequence.next_by_id())
        while remain >= base:
            position = remain % base # Rest of division
            res = seed[position] + res
            remain = remain // base # INT division
        if remain:
            res = seed[remain] + res # Last if present use remain
        res = '0' * (5 - len(res)) + res
        return res

    # COLUMNS:
    xml_code = fields.Char('XML Code', size=5,
        help='Code for sequence of XML invoice')

    # TODO create fields for write DDT / Invoice lines:

    @api.model
    def start_tag(self, block, tag, mode='open', newline='\n',
            init_space=True):
        """ tag: element to create
            value: data to put in tag
            block: XML block, es: 1.2.3.4 (used for extra init space
            mode: open or close
        """
        if init_space:
            extra_space = ' ' * block.count('.')
        else:
            extra_space = ''

        return '%s<%s%s>%s' % (
            extra_space,
            '' if mode == 'open' else '/',
            tag,
            newline,
            )

    @api.model
    def xml_sanitize_text(self, text):
        """ Clean not XML character
            TODO: to be completed
        """
        from xml.sax.saxutils import escape
        return escape(text or '')

    @api.model
    def get_tag(self, block, tag, value, cardinality='1:1', newline='\n',
            init_space=True):
        """ tag: element to create
            value: data to put in tag
            cardinality: 1:1 0:1 0:N (to check if need to return)
            block: XML block, es: 1.2.3.4 (used for extra init space
        """
        value = (value or '').strip().upper()
        value = self.xml_sanitize_text(value)

        #    _logger.error('Extract %s, %s > %s' % (
        #        block, tag, value))
        # Readability of XML:
        if init_space:
            extra_space = ' ' * block.count('.')
        else:
            extra_space = ''

        # Check minimum recurrency:
        if not value and cardinality[:1] == '0':
            return ''

        return '%s<%s>%s</%s>%s' % (
            extra_space,
            tag,
            value,
            tag,
            newline,
            )

    @api.model
    def clean_vat(self, vat, code='IT'):
        """ Add extra code if not present
        """
        return '%s%s' % (
            code if vat[:2].isdigit() else '',
            vat,
            )

    def clean_phone(self, phone, country_code='+39'):
        """ Add extra code if not present
        """
        return phone.replace(' ', '').replace(country_code, '')

    # -------------------------------------------------------------------------
    # XXX IMPORTANT: To be overridden in another module:
    # -------------------------------------------------------------------------
    @api.multi
    def fatturapa_get_details(self):
        """ Extract line detail summary
        """
        # todo NOT USED HERE (OVERRIDDEN) !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.ensure_one()

        picking = self[0]
        # Result dict:
        detail_table = {}
        vat_table = {}
        ddt_reference = {}
        # TODO order?

        # XXX Always present and one only!
        ddt_number = picking.ddt_number or ''
        # Keep only number:
        ddt_number = picking.ddt_number.split('/')[-1]

        ddt_date = picking.ddt_date

        i = 0 # Row sequence
        for line in picking.move_lines:
            # Parameters:
            price = line.price_unit # TODO!
            qty = line.product_uom_qty
            subtotal = price * qty
            vat = 22.0 # TODO
            subtotal_vat = subtotal * vat / 100.0

            # -----------------------------------------------------------------
            # Detail data:
            # -----------------------------------------------------------------
            i += 1
            detail_table[str(i)] = {
                'mode': '',  # No mode = product line (else SC, PR, AB, AC)
                'discount': '',  # No discount
                'nature': '',  # No nature (always 22)
                'product': line.product_id, # Browse
                'price': price,
                'qty': qty,
                'vat': vat,  # %
                'retention': '',  # No retention
                'subtotal': subtotal, # VAT excluded
                }

            # -----------------------------------------------------------------
            # Vat data:
            # -----------------------------------------------------------------
            if vat in vat_table:
                vat_table[vat][0] += subtotal
                vat_table[vat][1] += subtotal_vat
            else:
                vat_table[vat] = [
                    subtotal, # Subtotal
                    subtotal_vat, # VAT total
                    '', # Nature
                    '', # Extra expense
                    '', # Round
                    ]

            # -----------------------------------------------------------------
            # DDT reference:
            # -----------------------------------------------------------------
            if ddt_number in ddt_reference:
                # Update list of row number
                ddt_reference[ddt_number][0].append(str(i))
            else:
                # Create record reference
                ddt_reference[ddt_number] = [
                    [str(i), ], ddt_date]

        return detail_table, vat_table, ddt_reference

    @api.model
    def fatturapa_get_vat_table(self, picking):
        """ Extract vat sumary
        """
        res = []
        return res

    @api.model
    def fatturapa_get_payments(self, picking):
        """ Extract payment sumary
        """
        res = []
        return res

    # -------------------------------------------------------------------------
    # Default path (to be overrided)
    # -------------------------------------------------------------------------
    @api.multi
    def get_default_folder_xml_invoice(self):
        """
        """
        path = os.path.expanduser('~/Account/Invoice/XML')
        os.system('mkdir -p %s' % path)
        return path

    # -------------------------------------------------------------------------
    # Electronic Invoice extract:
    # -------------------------------------------------------------------------
    @api.multi
    def extract_account_electronic_invoice(self):
        """ Extract electronic invoice (or interchange file)
        """
        # ---------------------------------------------------------------------
        # Parameter:
        # ---------------------------------------------------------------------
        company_pool = self.env['res.company']
        italy_code = 'IT'
        italy_prefix = '+39'

        # ---------------------------------------------------------------------
        # Readability:
        # ---------------------------------------------------------------------
        picking = self
        company = company_pool.search([])[0]
        partner = picking.partner_id
        fiscal_position = partner.property_account_position_id
        sale = picking.sale_order_id

        # Check if needed:
        if not fiscal_position or not fiscal_position.fatturapa:
            _logger.warning('No need XML invoice: %s' % picking.name)
            return True

        # ---------------------------------------------------------------------
        # Params database:
        # ---------------------------------------------------------------------
        params = {}

        # Send code:
        xml_code = picking.get_next_xml_id()
        picking.xml_code = xml_code  # Save code for next print (always updated)

        # ---------------------------------------------------------------------
        #                          COMPANY PARAMETERS:
        # ---------------------------------------------------------------------
        format_param = company.fatturapa_format_id
        newline = '\n'
        doc_part = format_param.doc_part + newline

        # ---------------------------------------------------------------------
        # Variable to manage:
        # ---------------------------------------------------------------------
        company_vat = self.clean_vat(company.vat, italy_code)
        params['company'] = {
            # Anagrafic:
            # Sede:
            'company': company.name or '',
            'street': company.street,
            'number': '', # XXX Not used

            'city': company.city,
            'zip': company.zip,
            'province': 'BS', # TODO
            'country': italy_code, #TODO
            'rea_office': 'BS', # company.fatturapa_rea_number
            'rea_number': company.fatturapa_rea_number,
            'rea_capital': company.fatturapa_rea_capital,
            'rea_partner': company.fatturapa_rea_partner,
            'rea_liquidation': company.fatturapa_rea_liquidation,

            # TODO company or destin.?
            # 'unique_code': company.partner_id.fatturapa_unique_code,
            'vat_sender': company.fatturapa_vat_sender, # TODO use partner!!! <<< for filename!!

            'vat': company_vat,
            'vat_code' : company_vat[:2],
            'vat_number':  company_vat[2:],

            # TODO change fiscal code (add field, for now VAT)
            'fiscalcode': (company_vat).lstrip(italy_code),

            # TODO change (add list field in company)
            'mode': 'RF01',

            # TODO add field:
            'esigibility': 'I',

            # Contact:
            # (12 char max!)
            'phone': self.clean_phone(company.phone or '', italy_prefix),
            # TODO create field
            'fax': self.clean_phone('', italy_prefix),

            'email': company.email or '',
            }
        # Update for test:
        params['company']['has_contact'] = params['company']['phone'] or \
            params['company']['fax'] or params['company']['mail']

        # ---------------------------------------------------------------------
        #                          SENDER PARAMETERS:
        # ---------------------------------------------------------------------
        # TODO Sender change reference now company:
        sender_vat = self.clean_vat(company_vat, italy_code)
        params['sender'] = {
            'vat': sender_vat,
            'vat_code': sender_vat[:2],
            'vat_number': sender_vat[2:],
            }

        # ---------------------------------------------------------------------
        # Payment:
        # ---------------------------------------------------------------------
        payment = sale.payment_term_id
        params['payment'] = {
            'pt': payment.fatturapa_pt_id.code,  # Payment term TP*
            'pm': payment.fatturapa_pm_id.code,  # Payment method MP*
            }

        # ---------------------------------------------------------------------
        # Loop elements:
        # ---------------------------------------------------------------------
        # Extra table from picking:
        detail_table, vat_table, ddt_reference = \
            picking.fatturapa_get_details()

        # Extract totals:
        total_db = picking.move_lines_for_report_total()

        # ---------------------------------------------------------------------
        # Invoice / Picking parameters: TODO Put in loop
        # ---------------------------------------------------------------------
        invoice_number = (picking.invoice_number or '').split('/')[-1]
        params['invoice'] = {
            # Format used for invoice:
            'number': '%s/%s' % (
                int(invoice_number),
                'NC' if picking.stock_mode == 'in' else 'FE',
                ),

            'date': picking.invoice_date,  # todo prepare
            'type': 'TD04' if picking.stock_mode == 'in' else 'TD01',
            'currency': 'EUR',
            'causal': 'VENDITA',

            # Amount:
            'amount': total_db['total'],
            'vat_total': 0.0,  # todo
            }

        # ---------------------------------------------------------------------
        # Partner:
        # ---------------------------------------------------------------------
        partner_vat = self.clean_vat(partner.vat, italy_code)
        fiscalcode = (
            partner_vat or partner.fatturapa_private_fiscalcode
            or partner.fatturapa_fiscalcode).lstrip(italy_code)
        params['partner'] = {
            'company': '' if partner.fatturapa_name else partner.name,
            # name:
            'name': partner.fatturapa_name,
            'surname': partner.fatturapa_surname,

            # Address:
            'street': partner.street,
            'number': '',  # in street!
            'city': partner.city,
            'zip': partner.zip,
            'province': '',  # 'BS' # 0.1 TODO
            'country': italy_code, #TODO

            # 'empty_unique': fiscal_position.fatturapa_empty_code,
            'unique_code': partner.fatturapa_unique_code, # TODO company or destin.?
            'unique_pec': partner.fatturapa_pec,
            'fiscalcode': fiscalcode,


            'vat': partner_vat,
            'vat_code': partner_vat[:2],
            'vat_number': partner_vat[2:],
            }

        # partner_fiscal = 'RF01' # TODO Regime ordinario
        # TODO parametrize:
        params['partner']['unique_text'] = \
            params['partner']['unique_code'] or '0000000'

        # ---------------------------------------------------------------------
        # Check parameter:
        # ---------------------------------------------------------------------
        # format_param
        # doc_part
        # VAT 13 char UPPER
        # unique_pec or params['partner']['unique_code']!!
        # partner_unique_code = '0000000'   or 'XXXXXXX'
        # need vat, fiscalcode, pec check
        # check partner_vat | partner_fiscal

        # ---------------------------------------------------------------------
        # Generate filename for invoice:
        # ---------------------------------------------------------------------
        # TODO
        path = self.get_default_folder_xml_invoice()

        # XXX Note: ERROR external field not declared here:
        filename = '%s_%s.xml' % (
            params['company']['vat_sender'] or params['company']['vat'],
            xml_code,
            )
        # filename = (
        #    '%s.xml' % (self.invoice_number or 'no_number')).replace('/', '_')
        fullname = os.path.join(path, filename)
        f_invoice = open(fullname, 'w')
        _logger.warning('Output invoice XML: %s' % fullname)

        send_format = 'FPR12'  # always!

        # ---------------------------------------------------------------------
        #                         WRITE INVOICE:
        # ---------------------------------------------------------------------
        # Doc part:
        f_invoice.write(doc_part)

        # ---------------------------------------------------------------------
        # Header part:
        # ---------------------------------------------------------------------
        f_invoice.write(
            self.start_tag('1', 'FatturaElettronicaHeader'))
        f_invoice.write(
            self.start_tag('1.1', 'DatiTrasmissione'))
        f_invoice.write(
            self.start_tag('1.1.1', 'IdTrasmittente'))

        f_invoice.write(self.get_tag('1.1.1.1', 'IdPaese',
            params['sender']['vat_code']))
        f_invoice.write(self.get_tag('1.1.1.2', 'IdCodice',
            params['sender']['vat_number']))

        f_invoice.write(
            self.start_tag('1.1.1', 'IdTrasmittente', mode='close'))

        f_invoice.write( # Invoice number
            self.get_tag('1.1.2', 'ProgressivoInvio', xml_code))
        f_invoice.write(
            self.get_tag('1.1.3', 'FormatoTrasmissione', send_format))
        # Codice univoco destinatario (7 caratteri PR, 6 PA) tutti 0 alt.
        f_invoice.write(
            self.get_tag('1.1.4', 'CodiceDestinatario',
            params['partner']['unique_text']))

        # ---------------------------------------------------------------------
        # 1.1.5 (alternative 1.1.6) <ContattiTrasmittente>
        # 1.1.5.1 <Telefono>
        # 1.1.5.2 <Email>
        #        </ContattiTrasmittente>

        # ---------------------------------------------------------------------
        # 1.1.6 (alternative 1.1.5)
        f_invoice.write(
            self.get_tag('1.1.4', 'PECDestinatario',
            params['partner']['unique_pec'],
                cardinality='0:1'))
        f_invoice.write(
            self.start_tag('1.1', 'DatiTrasmissione', mode='close'))

        # ---------------------------------------------------------------------
        f_invoice.write(
            self.start_tag('1.2', 'CedentePrestatore'))

        f_invoice.write(
            self.start_tag('1.2.1', 'DatiAnagrafici'))
        f_invoice.write(
            self.start_tag('1.2.1.1', 'IdFiscaleIVA'))
        f_invoice.write(
            self.get_tag('1.2.1.1.1', 'IdPaese',
            params['company']['vat_code']))
        f_invoice.write(
            self.get_tag('1.2.1.1.2', 'IdCodice',
            params['company']['vat_number']))
        f_invoice.write(
            self.start_tag('1.2.1.1', 'IdFiscaleIVA', mode='close'))
        # TODO strano!
        f_invoice.write(
            self.get_tag('1.2.1.2', 'CodiceFiscale',
            params['company']['fiscalcode']))
        f_invoice.write(
            self.start_tag('1.2.1.3', 'Anagrafica'))
        # ---------------------------------------------------------------------
        if params['company']['company']: # 1.2.1.3.1 (alt. 1.2.1.3.2-1.2.1.3.3)
            f_invoice.write(
                self.get_tag('1.2.1.3.1', 'Denominazione',
                params['company']['company']))
        else:
            f_invoice.write(
                self.get_tag('1.2.1.3.1.2', 'Nome',
                params['company']['name']))
            f_invoice.write(
                self.get_tag('1.2.1.3.1.3', 'Cognome',
                params['company']['surname']))

        # 1.2.3.1.4 <Titolo> partner_title
        # 1.2.3.1.5 <CodEORI> newline
        f_invoice.write(
            self.start_tag('1.2.1.3', 'Anagrafica', mode='close'))
        # 1.2.1.4 <AlboProfessionale>
        # 1.2.1.5 <ProvinciaAlbo>
        # 1.2.1.6 <NumeroIscrizioneAlbo>
        # 1.2.1.7 <DataIscrizioneAlbo>
        f_invoice.write(
            self.get_tag('1.2.1.8', 'RegimeFiscale',
            params['company']['mode']))
        f_invoice.write(
            self.start_tag('1.2.1', 'DatiAnagrafici', mode='close'))

        f_invoice.write(
            self.start_tag('1.2.2', 'Sede'))
        f_invoice.write(
            self.get_tag('1.2.2.1', 'Indirizzo',
            params['company']['street']))
        #f_invoice.write(
        #    self.get_tag('1.2.2.2', 'NumeroCivico',
        #        params['company']['number']))
        f_invoice.write(
            self.get_tag('1.2.2.3', 'CAP',
            params['company']['zip']))
        f_invoice.write(
            self.get_tag('1.2.2.4', 'Comune',
            params['company']['city']))
        f_invoice.write(
            self.get_tag('1.2.2.5', 'Provincia',
            params['company']['province'], cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.2.2.6', 'Nazione',
            params['company']['country']))
        f_invoice.write(
            self.start_tag('1.2.2', 'Sede', mode='close'))

        # ---------------------------------------------------------------------
        # IF PRESENTE STABILE:
        # 1.2.3 <StabileOrganizzazione>
        # 1.2.3.1 <Indirizzo>
        # 1.2.3.2 <NumeroCivico>
        # 1.2.3.3 <CAP>
        # 1.2.3.4 <Comune>
        # 1.2.3.5 <Provincia>
        # 1.2.3.6 <Nazione>
        #       </StabileOrganizzazione>
        # ---------------------------------------------------------------------

        f_invoice.write(
            self.start_tag('1.2.4', 'IscrizioneREA'))
        f_invoice.write(
            self.get_tag('1.2.4.1', 'Ufficio',
            params['company']['rea_office']))
        f_invoice.write(
            self.get_tag('1.2.4.2', 'NumeroREA',
            params['company']['rea_number']))
        f_invoice.write(
            self.get_tag('1.2.4.3', 'CapitaleSociale',
            format_param.format_decimal(
                params['company']['rea_capital']), cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.2.4.4', 'SocioUnico',
            params['company']['rea_partner'],
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.2.4.5', 'StatoLiquidazione',
            params['company']['rea_liquidation'],
                cardinality='0:1'))
        f_invoice.write(
            self.start_tag('1.2.4', 'IscrizioneREA', mode='close'))

        # NOT MANDATORY:
        if params['company']['has_contact']:
            f_invoice.write(
                self.start_tag('1.2.5', 'Contatti'))
            f_invoice.write(
                self.get_tag('1.2.5.1', 'Telefono',
                params['company']['phone'], cardinality='0:1'))
            f_invoice.write(
                self.get_tag('1.2.5.2', 'Fax',
                params['company']['fax'], cardinality='0:1'))
            f_invoice.write(
                self.get_tag('1.2.5.3', 'Email',
                params['company']['email'], cardinality='0:1'))
            f_invoice.write(
                self.start_tag('1.2.5', 'Contatti', mode='close'))

        # NOT MANDATORY:
        # 1.2.6 RiferimentoAmministrazione

        # NOT MANDATORY:
        # 1.3 <RappresentanteFiscale
        # 1.3.1 <DatiAnagrafici
        # 1.3.1.1 <IdFiscaleIVA>
        # 1.3.1.1.1 <IdPaese
        # 1.3.1.1.2 <Idcodice
        #         </IdFiscaleIVA>
        # 1.3.1.2 <CodiceFiscale>
        # 1.3.1.3 <Anagrafica
        # 1.3.1.3.1 <Denominazione
        # 1.3.1.3.2 <Nome
        # 1.3.1.3.3 <Cognome
        # 1.3.1.3.4 <Titolo
        # 1.3.1.3.5 <CodEORI
        #         </Anagrafica
        #         </IdFiscaleIVA>
        #       </DatiAnagrafici
        #     </RappresentanteFiscale

        f_invoice.write(
            self.start_tag('1.2', 'CedentePrestatore', mode='close'))

        # ---------------------------------------------------------------------
        #                             CUSTOMER DATA:
        # ---------------------------------------------------------------------
        f_invoice.write(
            self.start_tag('1.4', 'CessionarioCommittente'))
        f_invoice.write(
            self.start_tag('1.4.1', 'DatiAnagrafici'))

        if params['partner']['vat']:  # Alternativo al blocco 1.4.1.2
            f_invoice.write(
                self.start_tag('1.4.1.1', 'IdFiscaleIVA'))
            f_invoice.write(
                self.get_tag('1.4.1.1.1', 'IdPaese',
                    params['partner']['vat_code']))
            f_invoice.write(
                self.get_tag('1.4.1.1.2', 'IdCodice',
                    params['partner']['vat_number']))
            f_invoice.write(
                self.start_tag('1.4.1.1', 'IdFiscaleIVA', mode='close'))
        else: # partner_fiscal Alternativo al blocco 1.4.1.1
            f_invoice.write(
                self.get_tag('1.4.1.2', 'CodiceFiscale',
                params['partner']['fiscalcode']))

        f_invoice.write(
            self.start_tag('1.4.1.3', 'Anagrafica'))
        if params['partner']['company']:  # 1.4.1.3.1 (alternative 1.2.1.3.2   1.2.1.3.3)
            f_invoice.write(
                self.get_tag('1.4.1.3.1', 'Denominazione',
                params['partner']['company']))
        else:  # 1.4.3.1.2 (altenative 1.2.1.3.1)
            f_invoice.write(
                self.get_tag('1.4.1.3.2', 'Nome',
                params['partner']['name']))
            f_invoice.write(
                self.get_tag('1.4.1.3.3', 'Cognome',
                params['partner']['surname']))
            # 1.4.3.1.4 <Titolo>partner_title
            # 1.4.3.1.5 <CodEORI> partner_eori
        f_invoice.write(
            self.start_tag('1.4.1.3', 'Anagrafica', mode='close'))
        f_invoice.write(
            self.start_tag('1.4.1', 'DatiAnagrafici', mode='close'))

        f_invoice.write(
            self.start_tag('1.4.2', 'Sede'))
        f_invoice.write(
            self.get_tag('1.4.2.1', 'Indirizzo',
            params['partner']['street']))
        f_invoice.write(
            self.get_tag('1.4.2.2', 'NumeroCivico',
            params['partner']['number'],
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.4.2.3', 'CAP',
            params['partner']['zip']))
        f_invoice.write(
            self.get_tag('1.4.2.4', 'Comune',
            params['partner']['city']))
        f_invoice.write(
            self.get_tag('1.4.2.5', 'Provincia',
            params['partner']['province'],
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.4.2.6', 'Nazione',
            params['partner']['country']))
        f_invoice.write(
            self.start_tag('1.4.2', 'Sede', mode='close'))

        # ---------------------------------------------------------------------
        # IF PRESENT:
        # 1.4.3 <StabileOrganizzazione>'
        # 1.4.3.1 <Indirizzo>
        # 1.4.3.2 <NumeroCivico>
        # 1.4.3.3 <CAP>
        # 1.4.3.4 <Comune>
        # 1.4.3.5 <Provincia>
        # 1.4.3.6 <Nazione>
        #       </StabileOrganizzazione>

        # NOT MANDATORY:
        # 1.4.4 <RappresentanteFiscale>
        # 1.4.4.1 <IdFiscaleIVA>
        # 1.4.4.1.1 <IdPaese>
        # 1.4.4.1.2 <IdCodice>
        #         <IdFiscaleIVA>
        # 1.4.4.2 <Denominazione>
        # 1.4.4.3 <Nome>
        # 1.4.4.4 <Cognome>
        #       <RappresentanteFiscale>
        f_invoice.write(
            self.start_tag('1.4', 'CessionarioCommittente', mode='close'))

        # NOT MANDATORY:
        # 1.5 TerzoIntermediarioOSoggettoEmittente
        # 1.5.1 DatiAnagrafici
        # 1.5.1.1 IdFiscaleIVA
        # 1.5.1.1.1 IdPaese
        # 1.5.1.1.2 IdCodice
        # 1.5.1.2 CodiceFiscale
        # 1.5.1.3 Anagrafica
        # 1.5.1.3.1 Denominazione
        # 1.5.1.3.2 Nome
        # 1.5.1.3.3 Cognome
        # 1.5.1.3.4 Titolo
        # 1.5.1.3.5 CodEORI

        # NOT MANDATORY:
        # 1.6 SoggettoEmittente

        f_invoice.write(
            self.start_tag('1', 'FatturaElettronicaHeader', mode='close'))
        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        #                                BODY:
        # ---------------------------------------------------------------------
        f_invoice.write(
            self.start_tag('2', 'FatturaElettronicaBody'))
        f_invoice.write(
            self.start_tag('2.1', 'DatiGenerali'))
        f_invoice.write(
            self.start_tag('2.1.1', 'DatiGeneraliDocumento'))

        f_invoice.write(
            self.get_tag('2.1.1.1', 'TipoDocumento',
            params['invoice']['type']))
        f_invoice.write(
            self.get_tag('2.1.1.2', 'Divisa',
            params['invoice']['currency']))
        f_invoice.write(
            self.get_tag('2.1.1.3', 'Data',
            format_param.format_date(
                params['invoice']['date'])))
        f_invoice.write(
            self.get_tag('2.1.1.4', 'Numero',
            params['invoice']['number']))

        # 2.1.1.5 <DatiRitenuta>
        # 2.1.1.5.1 <TipoRitenuta
        # 2.1.1.5.1 <ImportoRitenuta
        # 2.1.1.5.1 <AliquotaRitenuta
        # 2.1.1.5.1 <CausaleRitenuta
        #         </DatiRitenuta>

        # TODO Valutare questione bollo:
        # 2.1.1.6 <DatiBollo>
        # 2.1.1.6.1 <BolloVirtuale>
        # 2.1.1.6.2 <ImportoBollo>
        #         </DatiBollo>

        # 2.1.1.7 <DatiCassaPrevidenziale>
        # 2.1.1.7.1 <TipoCassa>
        # 2.1.1.7.2 <AlCassa>
        # 2.1.1.7.3 <ImportoContributoCassa>
        # 2.1.1.7.4 <ImponibileCassa>
        # 2.1.1.7.5 <AliquotaIVA>
        # 2.1.1.7.6 <Ritenuta>
        # 2.1.1.7.7 <Natura>
        # 2.1.1.7.8 <RiferimentoAmministrazione>

        # ---------------------------------------------------------------------
        # VALUTARE: Abbuoni attivi / passivi:
        # 2.1.1.8 <ScontoMaggiorazione>
        # 2.1.1.8.1 <Tipo>
        # ---------------------------------------------------------------------
        # 2.1.1.8.2 >>> Alternative 2.1.1.8.3
        # <Percentuale>
        # ---------------------------------------------------------------------
        # 2.1.1.8.3 <Importo>>>> Alternative 2.1.1.8.2
        #         </ScontoMaggiorazione>

        f_invoice.write( # Tot - Discount + VAT
            self.get_tag('2.1.1.9', 'ImportoTotaleDocumento',
            format_param.format_decimal(params['invoice']['amount'])))
        # f_invoice.write(
        #    self.get_tag('2.1.1.10', 'Arrotondamento', ))
        f_invoice.write(
            self.get_tag('2.1.1.11', 'Causale',
            params['invoice']['causal'],
            cardinality='0:N'))

        # 2.1.1.12 <Art73> Reverse Charge
        f_invoice.write(
            self.start_tag('2.1.1', 'DatiGeneraliDocumento', mode='close'))

        # ---------------------------------------------------------------------
        # RIFERIMENTO ORDINE: (0:N)
        # ---------------------------------------------------------------------
        """ 
        f_invoice.write(
            self.start_tag('2.1.2', 'DatiOrdineAcquisto'))
        
        # TODO LOOP LINE
        f_invoice.write(
            self.get_tag('2.1.2.1', 'RiferimentoNumeroLinea', ))

        f_invoice.write(
            self.get_tag('2.1.2.2', 'IdDocumento', ))
        f_invoice.write(
            self.get_tag('2.1.2.3', 'Data', ))
        f_invoice.write(
            self.get_tag('2.1.2.4', 'NumItem', ))
        f_invoice.write(
            self.get_tag('2.1.2.5', 'CodiceCommessaConvenzione', ))
        f_invoice.write(
         PA ONLY:
            self.get_tag('2.1.2.6', 'CodiceCUP', ))
        f_invoice.write(
            self.get_tag('2.1.2.7', 'CodiceCIG', ))
 
        f_invoice.write(
            self.start_tag('2.1.2', 'DatiOrdineAcquisto', mode='close'))
        """
        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        # RIFERIMENTO CONTRATTO: (0:N)
        # ---------------------------------------------------------------------
        """
        f_invoice.write(
            self.get_tag('2.1.3', 'DatiContratto', ))
        f_invoice.write(
            self.get_tag('2.1.4', 'DatiConvenzione', ))
        f_invoice.write(
            self.get_tag('2.1.5', 'DatiRicezione', ))
        f_invoice.write(
            self.get_tag('2.1.6', 'DatiFattureCollegate', ))

        f_invoice.write(
            self.start_tag('2.1.7', 'DatiSAL'))
        f_invoice.write(
            self.get_tag('2.1.7.1', 'RiferimentoFase', ))
        f_invoice.write(
            self.start_tag('2.1.7', 'DatiSAL', mode='close'))
        """
        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        # RIFERIMENTO DDT: (0:N) >> 1:N se non accompagnatoria
        # ---------------------------------------------------------------------
        for ddt_number in ddt_reference:
            ddt_lines, ddt_date = ddt_reference[ddt_number]

            f_invoice.write(
                self.start_tag('2.1.8', 'DatiDDT'))
            f_invoice.write(
                self.get_tag('2.1.8.1', 'NumeroDDT', ddt_number))
            f_invoice.write(
                self.get_tag('2.1.8.2', 'DataDDT',
                format_param.format_date(ddt_date)))

            # LOOP ON LINE REF
            for line in ddt_lines:
                f_invoice.write(
                    self.get_tag('2.1.8.3', 'RiferimentoNumeroLinea', line))

            f_invoice.write(
                self.start_tag('2.1.8', 'DatiDDT', mode='close'))
        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        # FATTURA ACCOMPAGNATORIA:
        # ---------------------------------------------------------------------
        """
        # 2.1.9 <DatiTrasporto>        
        # 2.1.9.1 <DatiAnagraficiVettore>
        # 2.1.9.1.1 <IdFiscaleIVA>        
        # 2.1.9.1.1.1 <IdPaese> DATA
        # 2.1.9.1.1.2 <IdCodice> DATI
        #           </IdFiscaleIVA>
        # 2.1.9.1.2 <CodiceFiscale> DATA        
        # 2.1.9.1.3 <Anagrafica>
        # ---------------------------------------------------------------------
        # 2.1.9.1.3.1 <Denominazione> (alternative 2.1.9.1.3.2    2.1.9.1.3.3)
        # ---------------------------------------------------------------------
        # 2.1.9.1.3.2 <Nome>(altenative 2.1.9.1.3.1)
        # 2.1.9.1.3.3 <Cognome>(altenative 2.1.9.1.3.1)
        # 2.1.9.1.3.4 <Titolo>
        # 2.1.9.1.3.5 <CodEORI>
        # 2.1.9.1.4 <NumeroLicenzaGuida>
        #           </Anagrafica>
        #       </DatiAnagraficiVettore>
        # 2.1.9.2 <MezzoTrasporto> 
        # 2.1.9.3 <CausaleTrasporto>
        # 2.1.9.4 <NumeroColli>
        # 2.1.9.5 <Descrizione>
        # 2.1.9.6 <UnitaMisuraPeso>
        # 2.1.9.7 <PesoLordo>
        # 2.1.9.8 <PesoNetto>
        # 2.1.9.9 <DataOraRitiro>
        # 2.1.9.10 <DataInizioTrasporto>
        # 2.1.9.11 <TipoResa>
        # 2.1.9.12 <IndirizzoResa>
        # 2.1.9.12.1 <Indirizzo>
        # 2.1.9.12.2 <NumeroCivico>
        # 2.1.9.12.3 <CAP>
        # 2.1.9.12.4 <Comune> 
        # 2.1.9.12.5 <Provincia>
        # 2.1.9.12.6 <Nazione>                
        #          </IndirizzoResa>
        # 2.1.9.13 <DataOraConsegna>
        #       </DatiTrasporto>'

        # ---------------------------------------------------------------------
        # NOT MANADATORY: Agevolazione trasportatore:
        # 2.1.10 <FatturaPrincipale>        
        # 2.1.10.1 <NumeroFatturaPrincipale>
        # 2.1.10.2 <DataFatturaPrincipale>
        #        </FatturaPrincipale>
        # ---------------------------------------------------------------------
        #    f_invoice.write(' </DatiGenerali>' + newline)
        """
        f_invoice.write(
            self.start_tag('2.1', 'DatiGenerali', mode='close'))

        f_invoice.write(
            self.start_tag('2.2', 'DatiBeniServizi'))

        # ---------------------------------------------------------------------
        #                        INVOICE DETAILS:
        # ---------------------------------------------------------------------
        for seq in sorted(detail_table):
            record = detail_table[seq]
            product = record['product']
            default_code = product.product_tmpl_id.default_code
            name = record.get('name', product.name)  # Name from sale
            uom = product.uom_id.fatturapa_code or product.uom_id.name

            f_invoice.write(
                self.start_tag('2.2.1', 'DettaglioLinee'))

            f_invoice.write(
                self.get_tag('2.2.1.1', 'NumeroLinea', seq))

            f_invoice.write(  # Solo se SC PR AB AC (spesa accessoria)
                self.get_tag('2.2.1.2', 'TipoCessionePrestazione',
                    record['mode'], cardinality='0:1'))

            # XXX Loop on every code passed:
            f_invoice.write(
                self.start_tag('2.2.1.3', 'CodiceArticolo'))
            f_invoice.write(  # PROPRIETARIO EAN TARIC SSC
                self.get_tag('2.2.1.3.1', 'CodiceTipo', 'PROPRIETARIO')) # todo
            f_invoice.write(
                self.get_tag('2.2.1.3.2', 'CodiceValore', default_code))
            f_invoice.write(
                self.start_tag('2.2.1.3', 'CodiceArticolo', mode='close'))

            f_invoice.write(
                self.get_tag('2.2.1.4', 'Descrizione', name))
            f_invoice.write(
                self.get_tag('2.2.1.5', 'Quantita',
                format_param.format_decimal(record['qty'])))
            f_invoice.write(
                self.get_tag('2.2.1.6', 'UnitaMisura', uom))
            # f_invoice.write(
            #    self.get_tag('2.2.1.7', 'DataInizioPeriodo', ,
            #        cardinality='0:1'))
            # f_invoice.write(
            #    self.get_tag('2.2.1.8', 'DataFinePeriodo', ,
            #        cardinality='0:1'))
            f_invoice.write(  # unitario, totale sconto (anche negativo)
                # Anche negativo # Vedi 2.2.1.2
                self.get_tag('2.2.1.9', 'PrezzoUnitario',
                format_param.format_decimal(record['price'], decimal=6)))

            """
            # -----------------------------------------------------------------
            # Sconto manuale (opzionale:
            f_invoice.write(
                self.start_tag('2.2.1.10', 'ScontoMaggiorazione'))

            f_invoice.write(# SC o MG
                self.get_tag('2.2.1.10.1', 'Tipo', ))
            f_invoice.write(# Alternativo a 2.2.1.10.3
                self.get_tag('2.2.1.10.2', 'Percentuale', ))
            f_invoice.write(# Alternativo a 2.2.1.10.2
                self.get_tag('2.2.1.10.3', 'Importo', ))
                
            f_invoice.write(
                self.start_tag('2.2.1.10', 'ScontoMaggiorazione', mode='close'))
            # ---------------------------------------------------------------------
            """
            f_invoice.write(# Subtotal for line
                self.get_tag('2.2.1.11', 'PrezzoTotale',
                format_param.format_decimal(record['subtotal'])))
            f_invoice.write(  # % VAT 22.00 format
                self.get_tag('2.2.1.12', 'AliquotaIVA',
                format_param.format_decimal(record['vat'])))
            # f_invoice.write(# % 22.00 format
            #    self.get_tag('2.2.1.13', 'Ritenuta', format_param.format_decimal))

            # Obbligatorio se IVA 0:
            f_invoice.write(# TODO Descrizione eventuale esenzione
                self.get_tag('2.2.1.14', 'Natura', record['nature'],
                cardinality='0:1'))
            # f_invoice.write(# Codice identificativo ai fini amministrativi
            #    self.get_tag('2.2.1.15', 'RiferimentoAmministrazione', ))

            """
            # ---------------------------------------------------------------------
            # Non obbligatorio: note e riferimenti
            f_invoice.write(
                self.start_tag('2.2.1.16', 'AltriDatiGestionali'))
            #f_invoice.write(# % 22.00 format
            #    self.get_tag('2.2.1.16.1', 'TipoDato', ))
            #f_invoice.write(# % 22.00 format
            #    self.get_tag('2.2.1.16.2', 'RiferimentoTesto', ))
            #f_invoice.write(# % 22.00 format
            #    self.get_tag('2.2.1.16.3', 'RiferimentoNumero', ))
            #f_invoice.write(# % 22.00 format
            #    self.get_tag('2.2.1.16.4', 'RiferimentoData', ))
            f_invoice.write(
                self.start_tag('2.2.1.16', 'AltriDatiGestionali', mode='close'))
            """

            f_invoice.write(
                self.start_tag('2.2.1', 'DettaglioLinee', mode='close'))

        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        # Obbligatorio: Elenco riepilogativo IVA del documento (1:N):
        # ---------------------------------------------------------------------
        for vat_key in vat_table:
            (item_subtotal, item_subtotal_vat, item_nature, item_round, extra) = \
                vat_table[vat_key]
            f_invoice.write(
                self.start_tag('2.2.2', 'DatiRiepilogo'))
            f_invoice.write(# % 22.00 format
                self.get_tag('2.2.2.1', 'AliquotaIVA',
                format_param.format_decimal(vat_key)))
            #f_invoice.write(# % Tabella Natura (se non idicata l'IVA)
            #    self.get_tag('2.2.2.2', 'Natura', ))
            #f_invoice.write(# % Tabella
            #    self.get_tag('2.2.2.3', 'SpeseAccessorie', ))
            #f_invoice.write(# % Tabella
            #    self.get_tag('2.2.2.4', 'Arrotondamento', ))
            f_invoice.write(# % Tabella
                self.get_tag('2.2.2.5', 'ImponibileImporto',
                format_param.format_decimal(item_subtotal)))
            f_invoice.write(# % Tabella
                self.get_tag('2.2.2.6', 'Imposta',
                format_param.format_decimal(item_subtotal_vat)))
            f_invoice.write(# % Tabella
                self.get_tag('2.2.2.7', 'EsigibilitaIVA',
                params['company']['esigibility']))
            #f_invoice.write(# % Tabella se presente Natura
            #    self.get_tag('2.2.2.8', 'RiferimentoNormativo', ))
            f_invoice.write(
                self.start_tag('2.2.2', 'DatiRiepilogo', mode='close'))
        # ---------------------------------------------------------------------

        f_invoice.write(
            self.start_tag('2.2', 'DatiBeniServizi', mode='close'))

        """
        # 2.3 <DatiVeicoli>
        # 2.3.1 <Data>'
        # 2.3.2 <TotalePercorso>
        #     </DatiVeicoli>
        """

        # ---------------------------------------------------------------------
        # Pagamento:
        # ---------------------------------------------------------------------
        f_invoice.write(
            self.start_tag('2.4', 'DatiPagamento'))
        f_invoice.write(# TODO tabelle TP01 a rate TP02 pagamento completo TP03 anticipo
            self.get_tag('2.4.1', 'CondizioniPagamento',
            params['payment']['pt']))

        # LOOP RATE (1:N): XXX now 1!
        f_invoice.write(
            self.start_tag('2.4.2', 'DettaglioPagamento'))
        #f_invoice.write( # TODO se differente dal cedente
        #    self.get_tag('2.4.2.1', 'Beneficiario', '', # TODO
        #    cardinality='0:1'))
        f_invoice.write( # TODO Tabella MP
            self.get_tag('2.4.2.2', 'ModalitaPagamento',
            params['payment']['pm']))
        f_invoice.write( # TODO Tabella MP
            self.get_tag('2.4.2.3', 'DataRiferimentoTerminiPagamento',
                format_param.format_date(params['invoice']['date'])))
        #f_invoice.write( # TODO Tabella MP
        #    self.get_tag('2.4.2.4', 'GiorniTerminiPagamento', ))
        #f_invoice.write( # TODO Tabella MP
        #    self.get_tag('2.4.2.5', 'DataScadenzaPagamento', ))
        f_invoice.write( # TODO Tabella MP
            self.get_tag('2.4.2.6', 'ImportoPagamento',
            format_param.format_decimal(params['invoice']['amount'])))

        # ---------------------------------------------------------------------
        # Ufficio postale:
        # ---------------------------------------------------------------------
        # 2.4.2.7 <CodUfficioPostale>
        # 2.4.2.8 <CognomeQuietanzante>
        # 2.4.2.9 <NomeQuietanzante>
        # 2.4.2.10 <CFQuietanzante>
        # 2.4.2.11 <TitoloQuietanzante>
        """
        # ---------------------------------------------------------------------

        f_invoice.write( # (0.1)
            self.get_tag('2.4.2.12', 'IstitutoFinanziario', ))
        f_invoice.write( 
            self.get_tag('2.4.2.13', 'IBAN', ))
        f_invoice.write( 
            self.get_tag('2.4.2.14', 'ABI', ))
        f_invoice.write( 
            self.get_tag('2.4.2.15', 'CAB', ))
        f_invoice.write( 
            self.get_tag('2.4.2.16', 'BIC', ))
        """
        # ---------------------------------------------------------------------
        # Pagamento anticipato:
        """
        # 2.4.2.17 <ScontoPagamentoAnticipato>
        # 2.4.2.18 <DataLimitePagamentoAnticipato>        
        # 2.4.2.19 <PenalitaPagamentiRitardati>
        # 2.4.2.20 <DataDecorrenzaPenale>
        # 2.4.2.21 <CodicePagamento>
        """
        # ---------------------------------------------------------------------
        f_invoice.write(
            self.start_tag('2.4.2', 'DettaglioPagamento', mode='close'))
        f_invoice.write(
            self.start_tag('2.4', 'DatiPagamento', mode='close'))

        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        # LOOP ATTACHMENTS:
        # ---------------------------------------------------------------------
        '''
        f_invoice.write(
            self.start_tag('2.5', 'Allegati'))
        f_invoice.write( 
            self.get_tag('2.5.1', 'NomeAttachment', ))
        f_invoice.write( # ZIP RAR
            self.get_tag('2.5.2', 'AlgoritmoCompressione', ))
        f_invoice.write(  # TXT XML DOC PDF
            self.get_tag('2.5.3', 'FormatoAttachment', ))
        f_invoice.write( 
            self.get_tag('2.5.4', 'DescrizioneAttachment', ))
        f_invoice.write( 
            self.get_tag('2.5.5', 'Attachment', ))
        f_invoice.write(
            self.start_tag('2.4', 'Allegati', mode='close'))
        '''

        f_invoice.write(
            self.start_tag('2', 'FatturaElettronicaBody', mode='close'))
        f_invoice.write(
            self.start_tag('1', 'p:FatturaElettronica', mode='close'))

        f_invoice.close()
