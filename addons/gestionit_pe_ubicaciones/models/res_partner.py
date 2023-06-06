# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, ValidationError
import datetime
from lxml import etree
import math
import pytz
from PIL import Image

from odoo import models, fields, api


class ResPartner(models.Model):
    # _name = 'res.partner'
    _inherit = 'res.partner'

    # street_code = fields.Many2one("res.country.state")
    country_id = fields.Many2one('res.country',default=lambda self:self.env.company.country_id.id)
    state_id = fields.Many2one('res.country.state', 'Departamento')
    province_id = fields.Many2one('res.country.state', 'Provincia')
    district_id = fields.Many2one('res.country.state', 'Distrito')
    ubigeo = fields.Char('Ubigeo')

    # Funcion reemplazada para considerar los nuevos campos en el onchange
    @api.model
    def _address_fields(self):
        """ Returns the list of address fields that are synced from the parent
        when the `use_parent_address` flag is set. """
        # ~ return list(ADDRESS_FIELDS)
        address_fields = ('street', 'street2', 'zip', 'city',
                          'state_id', 'country_id', 'province_id', 'district_id')
        return list(address_fields)


    @api.onchange('district_id')
    def onchange_district(self):
        if self.district_id:
            self.ubigeo = self.district_id.code if self.district_id.code else ""

    # @api.multi
    def _display_address(self, without_company=False):
        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format
        for record in self:
            address_format = record.country_id.address_format or \
                "%(street)s\n%(street2)s\n%(state_name)s-%(province_name)s-%(district_code)s %(zip)s\n%(country_name)s"
            args = {
                'district_code': record.district_id.code or '',
                'district_name': record.district_id.name or '',
                'province_code': record.province_id.code or '',
                'province_name': record.province_id.name or '',
                'state_code': record.state_id.code or '',
                'state_name': record.state_id.name or '',
                'country_code': record.country_id.code or '',
                'country_name': record.country_id.name or '',
                'company_name': record.parent_name or '',
            }
            for field in record._address_fields():
                args[field] = getattr(record, field) or ''
            if without_company:
                args['company_name'] = ''
            elif record.commercial_company_name:
                address_format = '%(company_name)s\n' + address_format
            return address_format % args
