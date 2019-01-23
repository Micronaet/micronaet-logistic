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
from odoo import api, models, fields
from odoo import tools
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class FatturapaFormat(models.Model):
    ''' Fattura PA Format and utility for formatting
        ['1.1.3']
    '''
    _name = 'fatturapa.format'
    _description = 'FatturaPA Format'

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    @api.model
    def format_pa_date(self, value):
        ''' Date ISO format YYYY-MM-GG
        '''        
        return value

    @api.model
    def format_pa_float(self, value):
        ''' Date ISO format 0.00
        '''
        if not value or type(value) != float:
            return '0.00'
        else:
            return ('%10.2f' % value).strip()

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=5)
    doc_part = fields.Text('Doc Part')

class FatturapaDocumentType(models.Model):
    ''' Document type (invoice, credit note):
        ['2.1.1.1'] (Startup data)
    '''
    _name = 'fatturapa.document_type'
    _description = 'FatturaPA Document Type'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=4)

class FatturapaPaymentTerm(models.Model):
    ''' Payment term
        ['2.4.1']
    '''
    _name = 'fatturapa.payment_term'
    _description = 'FatturaPA Payment Term'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=4)

class FatturapaPaymentMethod(models.Model):
    ''' Payment method
        ['2.4.2.2']
    '''
    _name = 'fatturapa.payment_method'
    _description = 'FatturaPA Payment Method'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=4)

class WelfareFundType(models.Model):
    ''' Welfare fund
        ['2.1.1.7.1']
    '''
    _name = 'welfare.fund.type'
    _description = 'welfare fund type'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Name')
    description = fields.Char('Description')

class FatturapaFiscalPosition(models.Model):
    ''' Fiscal position:
        ['2.1.1.7.7', '2.2.1.14']
    '''
    _name = 'fatturapa.fiscal_position'
    _description = 'FatturaPA Fiscal Position'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    name = fields.Char('Description', size=128)
    code = fields.Char('Code', size=4)

class AccountPaymentTerm(models.Model):
    ''' Payment term
        ['2.4.2.2']
    '''
    _inherit = 'account.payment.term'

    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    fatturapa_pt_id = fields.Many2one(
        'fatturapa.payment_term', string='FatturaPA Payment Term')
    fatturapa_pm_id = fields.Many2one(
        'fatturapa.payment_method', string='FatturaPA Payment Method')

class ResPartner(models.Model):
    ''' Extra data for partner 
    '''
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
    fatturapa_unique_code = fields.Char('Unique code SDI', size=7)
    fatturapa_pec = fields.Char('Fattura PA PEC', size=120)
    fatturapa_fiscalcode = fields.Char(
        'Fattura fiscal code', size=13)
    fatturapa_private_fiscalcode = fields.Char(
        'Fattura private fiscal code', size=20)

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
    ''' Company data
    '''
    
    _inherit = 'res.company'
    
    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    fatturapa_name = fields.Char('Partner name', size=80)
    fatturapa_surname = fields.Char('Partner surname', size=80)

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
    fatturapa_tax_representative = fields.Many2one(
        'res.partner', 'Legal Tax Representative'
        )
    fatturapa_sender_partner = fields.Many2one(
        'res.partner', 'Third Party/Sender'
        )

class AccountFiscalPosition(models.Model):
    ''' Fattura PA for fiscal position
    '''
    _inherit = 'account.fiscal.position'
    
    # -------------------------------------------------------------------------
    #                             COLUMNS:
    # -------------------------------------------------------------------------
    fatturapa = fields.Boolean('Fattura PA')

class AccountTax(models.Model):
    ''' Account tax fattura PA data
    '''
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
    ''' Stock picking extract
    '''
    _inherit = 'stock.picking'

    # TODO create fields for write DDT / Invoice lines:

    @api.model
    def start_tag(self, block, tag, mode='open', newline='\n', 
            init_space=True):
        ''' tag: element to create
            value: data to put in tag
            block: XML block, es: 1.2.3.4 (used for extra init space
            mode: open or close
        ''' 
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
    def get_tag(self, block, tag, value, cardinality='1:1', newline='\n', 
            init_space=True):
        ''' tag: element to create
            value: data to put in tag
            cardinality: 1:1 0:1 0:N (to check if need to return)
            block: XML block, es: 1.2.3.4 (used for extra init space
        ''' 
        value = (value or '').strip().upper()

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
        
    # -------------------------------------------------------------------------
    # Default path (to be overrided)
    # -------------------------------------------------------------------------
    @api.multi
    def get_default_folder_xml_invoice(self):
        '''
        '''
        path = os.path.expanduser('~/Account/Invoice/XML')
        os.system('mkdir -p %s' % path)
        return path

    # -------------------------------------------------------------------------
    # Electronic Invoice extract:
    # -------------------------------------------------------------------------
    @api.multi
    def extract_account_electronic_invoice(self):
        ''' Extract electronic invoice (or interchange file)
        '''
        # ---------------------------------------------------------------------
        # Parameter:
        # ---------------------------------------------------------------------
        company_pool = self.env['res.company']
        company = company_pool.search([])[0]

        # ---------------------------------------------------------------------
        # Company parameters:                
        # ---------------------------------------------------------------------
        format_param = company.fatturapa_format_id
        newline = '\n'        
        doc_part = format_param.doc_part + newline
        vat = company.vat
        company_fiscal = company.vat
        company_fiscal_mode = 'RF01' # TODO 

        # Sede:        
        company_company = company.name
        company_street = company.street
        # company_number = '' # in street!
        company_city = company.city
        company_zip = company.zip
        company_provice = 'BS' # TODO 
        company_country = 'IT' #TODO
        rea_office = 'BS' # company.fatturapa_rea_number
        rea_number = company.fatturapa_rea_number
        rea_capital = company.fatturapa_rea_capital
        rea_partner = company.fatturapa_rea_partner.code
        rea_liquidation = company.fatturapa_rea_liquidation.code
        
        #unique_code = company.fatturapa_unique_code # TODO company or destin.?

        # ---------------------------------------------------------------------
        # Invoice / Picking parameters: TODO Put in loop
        # ---------------------------------------------------------------------
        picking = self
        invoice_number = picking.invoice_number
        invoice_date = picking.invoice_date # TODO prepare
        invoice_type = 'TD01' # TODO 
        invoice_currency = 'EUR'
        invoice_causal = 'VENDITA'
        
        # amount:
        invoice_amount = 0.0 # TODO 
        invoice_vat_total = 0.0 # TODO 

        # ---------------------------------------------------------------------
        # Partner:
        # ---------------------------------------------------------------------
        partner = picking.partner_id
        
        # sede:
        partner_street = partner.street
        # partner_number = '' # in street!
        partner_city = partner.city
        partner_zip = partner.zip
        partner_provice = '' #'BS' # 0.1 TODO 
        partner_country = 'IT' #TODO
        
        # codes:
        unique_code = partner.fatturapa_unique_code # TODO company or destin.?
        unique_pec = partner.fatturapa_pec
        fatturapa_private_fiscalcode = partner.fatturapa_private_fiscalcode

        partner_fiscal = 'RF01' # TODO Regime ordinario
        
        # name:
        partner_name = partner.fatturapa_name
        partner_surname = partner.fatturapa_surname
        if partner_name:
            partner_company = ''
        else:
            partner_company = partner.name # No Company name written    
        
        # Reference:
        partner_vat = partner.client_vat # XXX needed?
        partner_fiscal = partner_vat or \
            partner.fatturapa_private_fiscalcode or \
            partner.fatturapa_fiscalcode

        # ---------------------------------------------------------------------
        # Check parameter:
        # ---------------------------------------------------------------------
        # format_param
        # doc_part
        # VAT 13 char UPPER
        # unique_pec or unique_code!!
        # unique_code = '0000000'
        # need vat, fiscalcode, pec check
        # check partner_vat | partner_fiscal
                
        # ---------------------------------------------------------------------
        # Generate filename for invoice:
        # ---------------------------------------------------------------------
        # TODO
        path = self.get_default_folder_xml_invoice()

        # XXX Note: ERROR external field not declared here:
        filename = (
            '%s.xml' % (self.invoice_number or 'no_number')).replace('/', '_')
        fullname = os.path.join(path, filename)
        f_invoice = open(fullname, 'w')
        send_format = 'FPR12' # always!

        # ---------------------------------------------------------------------
        #                         WRITE INVOICE:        
        # ---------------------------------------------------------------------
        # Doc part:
        f_invoice.write(doc_part)

        # ---------------------------------------------------------------------
        # Header part:
        # ---------------------------------------------------------------------
        self.start_tag('1', 'FatturaElettronicaHeader')

        self.start_tag('1.1', 'DatiTrasmissione')

        self.start_tag('1.1.1', 'IdTrasmittente')
        
        f_invoice.write(
            self.get_tag('1.1.1.1', 'IdPaese', vat[:2]))

        f_invoice.write(
            self.get_tag('1.1.1.2', 'IdCodice', vat[2:],))
        
        self.start_tag('1.1.1', 'IdTrasmittente', mode='close')
        
        f_invoice.write( # Invoice number
            self.get_tag('1.1.2', 'ProgressivoInvio', invoice_number))
        
        f_invoice.write(
            self.get_tag('1.1.3', 'FormatoTrasmissione', send_format))

        # Codice univoco destinatario (7 caratteri PR, 6 PA) tutti 0 alt.
        f_invoice.write(
            self.get_tag('1.1.4', 'CodiceDestinatario', unique_code))

        # ---------------------------------------------------------------------
        # 1.1.5 (alternative 1.1.6)
        #f_invoice.write('  <ContattiTrasmittente>' + newline)
        # 1.1.5.1
        #f_invoice.write('   <Telefono>' + newline)
        # DATI
        #f_invoice.write('   </Telefono>' + newline)
        # 1.1.5.2
        #f_invoice.write('   <Email>' + newline)
        # DATI
        #f_invoice.write('   </Email>' + newline)

        #f_invoice.write('  </ContattiTrasmittente>' + newline)
        
        # ---------------------------------------------------------------------
        # 1.1.6 (alternative 1.1.5)
        if unique_pec:
            f_invoice.write('  <PECDestinatario>%s</PECDestinatario>%s' % (
                unique_pec, newline))

        self.start_tag('1.1', 'DatiTrasmissione', mode='close')

        # ---------------------------------------------------------------------
        self.start_tag('1.2', 'CedentePrestatore')
        self.start_tag('1.2.1', 'DatiAnagrafici')
        self.start_tag('1.2.1.1', 'IdFiscaleIVA')
        
        f_invoice.write(
            self.get_tag('1.2.1.1.1', 'IdPaese', company_vat[:2]))

        f_invoice.write( # TODO - IT?
            self.get_tag('1.2.1.1.2', 'IdCodice', company_vat[2:]))

        self.start_tag('1.2.1.1', 'IdFiscaleIVA', mode='close')

        # TODO strano!
        f_invoice.write( # TODO ???
            self.get_tag('1.2.1.2', 'CodiceFiscale', company_fiscal[2:]))

        self.start_tag('1.2.1.3', 'Anagrafica')
        
        # ---------------------------------------------------------------------                
        if company_company: # 1.2.1.3.1 (alternative 1.2.1.3.2 - 1.2.1.3.3)
            f_invoice.write(
                self.get_tag('1.2.1.3.1', 'Denominazione', company_company))
        else:
            f_invoice.write(
                self.get_tag('1.2.1.3.1.2', 'Nome', company_name))
            f_invoice.write(
                self.get_tag('1.2.1.3.1.3', 'Cognome', company_surname))

        # 1.2.3.1.4 <Titolo> partner_title            
        # 1.2.3.1.5 <CodEORI> newline 
        self.start_tag('1.2.1.3', 'Anagrafica', mode='close')

        # 1.2.1.4 <AlboProfessionale>
        # 1.2.1.5 <ProvinciaAlbo>
        # 1.2.1.6 <NumeroIscrizioneAlbo>
        # 1.2.1.7 <DataIscrizioneAlbo>

        f_invoice.write(
            self.get_tag('1.2.1.8', 'RegimeFiscale', company_fiscal_mode))

        self.start_tag('1.2.1', 'DatiAnagrafici', mode='close')

        self.start_tag('1.2.2', 'Sede')
        
        f_invoice.write(
            self.get_tag('1.2.2.1', 'Indirizzo', company_street))
        #f_invoice.write(
        #    self.get_tag('1.2.2.2', 'NumeroCivico', company_number))
        f_invoice.write(
            self.get_tag('1.2.2.3', 'CAP', company_zip))
        f_invoice.write(
            self.get_tag('1.2.2.4', 'Comune', company_city))
        f_invoice.write(
            self.get_tag('1.2.2.5', 'Provincia', company_province, 
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.2.2.6', 'Nazione', company_country))

        self.start_tag('1.2.2', 'Sede', mode='close')

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

        self.start_tag('1.2.4', 'IscrizioneREA')
        f_invoice.write(
            self.get_tag('1.2.4.1', 'Ufficio', rea_office))
        f_invoice.write(
            self.get_tag('1.2.4.2', 'NumeroREA', rea_number))
        f_invoice.write(
            self.get_tag('1.2.4.3', 'CapitaleSociale', rea_capital, 
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.2.4.4', 'SocioUnico', rea_partner, 
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.2.4.5', 'StatoLiquidazione', rea_liquidation, 
                cardinality='0:1'))
        self.start_tag('1.2.4', 'IscrizioneREA', mode='close')
        
        # NOT MANDATORY:
        # 1.2.5 <Contatti>        
        # 1.2.5.1 <Telefono>
        # 1.2.5.2 <Fax>
        # 1.2.5.2 <Email>
        #       </Contatti>
        
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

        self.start_tag('1.2', 'CedentePrestatore', mode='close')
        
        # ---------------------------------------------------------------------
        #                             CUSTOMER DATA:
        # ---------------------------------------------------------------------
        self.start_tag('1.4', 'CessionarioCommittente')
        self.start_tag('1.4.1', 'DatiAnagrafici')
        
        if partner_vat: # Alternativo al blocco 1.4.1.2
            self.start_tag('1.4.1.1', 'IdFiscaleIVA')
            f_invoice.write(
                self.get_tag('1.4.1.1.1', 'IdPaese', partner_vat[:2]))
            f_invoice.write(
                self.get_tag('1.4.1.1.2', 'IdCodice', partner_vat[2:]))
            self.start_tag('1.4.1.1', 'IdFiscaleIVA', mode='close')
        else: # partner_fiscal Alternativo al blocco 1.4.1.1
            f_invoice.write(
                self.get_tag('1.4.1.2', 'CodiceFiscale', partner_fiscal))

        self.start_tag('1.4.1.3', 'Anagrafica')
        if partner_company: # 1.4.1.3.1 (alternative 1.2.1.3.2   1.2.1.3.3)
            f_invoice.write(
                self.get_tag('1.4.1.3.1', 'Denominazione', partner_company))
        else: # 1.4.3.1.2 (altenative 1.2.1.3.1)
            f_invoice.write(
                self.get_tag('1.4.1.3.2', 'Nome', partner_name))
            f_invoice.write(
                self.get_tag('1.4.1.3.3', 'Cognome', partner_surname))
            # 1.4.3.1.4 <Titolo>partner_title
            # 1.4.3.1.5 <CodEORI> partner_eori
        self.start_tag('1.4.1.3', 'Anagrafica', mode='close')

        self.start_tag('1.4.2', 'Sede')
        f_invoice.write(
            self.get_tag('1.4.2.1', 'Indirizzo', partner_street))
        f_invoice.write(
            self.get_tag('1.4.2.2', 'NumeroCivico', partner_number, 
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.4.2.3', 'CAP', partner_zip))
        f_invoice.write(
            self.get_tag('1.4.2.4', 'Comune', partner_city))
        f_invoice.write(
            self.get_tag('1.4.2.5', 'Provincia', partner_province, 
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('1.4.2.6', 'Nazione', partner_country))
        self.start_tag('1.4.2', 'Sede', mode='close')

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
        self.start_tag('1.4.1', 'DatiAnagrafici', mode='close')
        self.start_tag('1.4', 'CessionarioCommittente', mode='close')

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

        self.start_tag('1', 'FatturaElettronicaHeader', mode='close')
        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        #                                BODY:
        # ---------------------------------------------------------------------
        self.start_tag('2', 'FatturaElettronicaBody')
        self.start_tag('2.1', 'DatiGenerali')
        self.start_tag('2.1.1', 'DatiGeneraliDocumento')

        f_invoice.write(
            self.get_tag('2.1.1.1', 'TipoDocumento', invoice_type))
        f_invoice.write(
            self.get_tag('2.1.1.2', 'Divisa', invoice_currency))
        f_invoice.write(
            self.get_tag('2.1.1.3', 'Data', invoice_date))
        f_invoice.write(
            self.get_tag('2.1.1.4', 'Numero', invoice_number))

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
            self.get_tag('2.1.1.9', 'ImportoTotaleDocumento', invoice_amount))
        #f_invoice.write(
        #    self.get_tag('2.1.1.10', 'Arrotondamento', ))
        f_invoice.write(
            self.get_tag('2.1.1.11', 'Causale', invoice_causal, 
                cardinality='0:N'))

        # 2.1.1.12 <Art73>

        self.start_tag('2.1.1', 'DatiGeneraliDocumento', mode='close')

        # ---------------------------------------------------------------------        
        # RIFERIMENTO ORDINE: (0:N)
        # ---------------------------------------------------------------------
        """ 
        self.start_tag('2.1.2', 'DatiOrdineAcquisto')
        
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
 
        self.start_tag('2.1.2', 'DatiOrdineAcquisto', mode='close')
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

        self.start_tag('2.1.7', 'DatiSAL')
        f_invoice.write(
            self.get_tag('2.1.7.1', 'RiferimentoFase', ))
        self.start_tag('2.1.7', 'DatiSAL', mode='close')
        """
        # ---------------------------------------------------------------------        

        # ---------------------------------------------------------------------        
        # RIFERIMENTO DDT: (0:N) >> 1:N se non accompagnatoria
        # ---------------------------------------------------------------------
        """
        # TODO LOOP DDT
        self.start_tag('2.1.8', 'DatiDDT')
        f_invoice.write(
            self.get_tag('2.1.8.1', 'NumeroDDT', ))
        f_invoice.write(
            self.get_tag('2.1.8.2', 'DataDDT', ))
            
        # LOOP ON LINE REF
        f_invoice.write(
            self.get_tag('2.1.8.3', 'RiferimentoNumeroLinea', ))

        self.start_tag('2.1.8', 'DatiDDT', mode='close')
        """
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
        
        # TODO LOOP ON LINE 
        """
        self.start_tag('2.2', 'DatiBeniServizi')
        self.start_tag('2.2.1', 'DettaglioLinee')
        f_invoice.write(
            self.get_tag('2.2.1.1', 'NumeroLinea', ))

        f_invoice.write(# Solo se SC PR AB AC (spesa accessoria)
            self.get_tag('2.2.1.2', 'TipoCessionePrestazione', ))
            
        # Loop on every code passed:    
        self.start_tag('2.2.1.3', 'CodiceArticolo')
        f_invoice.write(# PROPRIETARIO EAN TARIC SSC
            self.get_tag('2.2.1.3.1', 'CodiceTipo', 'PROPRIETARIO')) # TODO
        f_invoice.write(# PROPRIETARIO EAN TARIC SSC
            self.get_tag('2.2.1.3.2', 'CodiceValore', )) # TODO
        self.start_tag('2.2.1.3', 'CodiceArticolo', mode='close')

        f_invoice.write(
            self.get_tag('2.2.1.4', 'Descrizione', ))
        f_invoice.write(
            self.get_tag('2.2.1.5', 'Quantita', ))
        f_invoice.write(
            self.get_tag('2.2.1.6', 'UnitaMisura', ))
        f_invoice.write(
            self.get_tag('2.2.1.7', 'DataInizioPeriodo', , 
                cardinality='0:1'))
        f_invoice.write(
            self.get_tag('2.2.1.8', 'DataFinePeriodo', , 
                cardinality='0:1'))
        f_invoice.write(
            # TODO prezzo unitario, totale sconto (anche negativo)
            # Anche negativo # Vedi 2.2.1.2
            self.get_tag('2.2.1.9', 'PrezzoUnitario', ))
        """
        """
        # ---------------------------------------------------------------------
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

        f_invoice.write(# Subtotal for line
            self.get_tag('2.2.1.11', 'PrezzoTotale', ))
        f_invoice.write(# % VAT 22.00 format
            self.get_tag('2.2.1.12', 'AliquotaIVA', ))
        #f_invoice.write(# % 22.00 format
        #    self.get_tag('2.2.1.13', 'Ritenuta', ))

        # Obbligatorio se IVA 0:
        f_invoice.write(# TODO Descrizione eventuale esenzione
            self.get_tag('2.2.1.14', 'Natura', ))
        #f_invoice.write(# Codice identificativo ai fini amministrativi
        #    self.get_tag('2.2.1.15', 'RiferimentoAmministrazione', ))

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
        self.start_tag('2.2.1', 'DettaglioLinee', mode='close')

        # ---------------------------------------------------------------------
        # Obblicatorio: Elenco riepilogativo IVA del documento (1:N):
        # LOOP RIEPILOGO IVA:
        self.start_tag('2.2.2', 'DatiRiepilogo')
        f_invoice.write(# % 22.00 format
            self.get_tag('2.2.2.1', 'AliquotaIVA', ))
        #f_invoice.write(# % Tabella Natura (se non idicata l'IVA)
        #    self.get_tag('2.2.2.2', 'Natura', ))
        #f_invoice.write(# % Tabella
        #    self.get_tag('2.2.2.3', 'SpeseAccessorie', ))
        #f_invoice.write(# % Tabella
        #    self.get_tag('2.2.2.4', 'Arrotondamento', ))
        f_invoice.write(# % Tabella
            self.get_tag('2.2.2.5', 'ImponibileImporto', ))
        f_invoice.write(# % Tabella
            self.get_tag('2.2.2.6', 'Imposta', ))
        f_invoice.write(# % Tabella
            self.get_tag('2.2.2.7', 'EsigibilitaIVA', ))
        f_invoice.write(# % Tabella
            self.get_tag('2.2.2.8', 'RiferimentoNormativo', ))


        self.start_tag('2.2.2', 'DatiRiepilogo', mode='close')
        self.start_tag('2.2', 'DatiBeniServizi', mode='close')

        """
        # 2.3 <DatiVeicoli>
        # 2.3.1 <Data>'
        # 2.3.2 <TotalePercorso>
        #     </DatiVeicoli>
        """

        # ---------------------------------------------------------------------
        # Pagamento:
        # ---------------------------------------------------------------------
        self.start_tag('2.4', 'DatiPagamento')
        f_invoice.write(# TODO tabelle TP01 a rate TP02 pagamento completo TP03 anticipo
            self.get_tag('2.4.1', 'CondizioniPagamento', ))

            
        # LOOP RATE (1:N):
        self.start_tag('2.4.2', 'DettaglioPagamento')
        f_invoice.write( # TODO se differente dal cedente
            self.get_tag('2.4.2.1', 'Beneficiario', '', # TODO
            cardinality='0:1'))
        f_invoice.write( # TODO Tabella MP
            self.get_tag('2.4.2.2', 'ModalitaPagamento', ))
        f_invoice.write( # TODO Tabella MP
            self.get_tag('2.4.2.3', 'DataRiferimentoTerminiPagamento', ))
        f_invoice.write( # TODO Tabella MP
            self.get_tag('2.4.2.4', 'GiorniTerminiPagamento', ))
        f_invoice.write( # TODO Tabella MP
            self.get_tag('2.4.2.5', 'DataScadenzaPagamento', ))
        f_invoice.write( # TODO Tabella MP
            self.get_tag('2.4.2.6', 'ImportoPagamento', ))

        # ---------------------------------------------------------------------
        # Ufficio postale:        
        # ---------------------------------------------------------------------
        """
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

        self.start_tag('2.4.2', 'DettaglioPagamento', mode='close')
        self.start_tag('2.4', 'DatiPagamento', mode='close')
        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        # LOOP ATTACHMENTS:
        '''
        self.start_tag('2.5', 'Allegati')
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
        self.start_tag('2.4', 'Allegati', mode='close')
        '''

        self.start_tag('2', 'FatturaElettronicaBody', mode='close')
        self.start_tag('1', 'p:FatturaElettronica', mode='close')

        f_invoice.close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: