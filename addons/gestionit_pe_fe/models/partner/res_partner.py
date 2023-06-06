# -*- coding: utf-8 -*-
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
from odoo import fields, models, api, _
import logging
import re
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains('vat','l10n_latam_identification_type_id', 'name', 'registration_name', 'estado_contribuyente')
    def _check_limitation_partners(self):
        for record in self:
            check_flag = self.env.context.get('check_flag', False)
            group_change_partner = self.env.ref('gestionit_pe_fe.res_groups_change_partners')
            if check_flag is False:
                if self.env.uid in group_change_partner.users.ids:
                    if record.total_invoiced:
                        raise UserError("No puede modificar datos de un contacto que ya ha completado alguna factura.")

    @api.model
    def default_get(self,field_list):
        res = super(ResPartner, self).default_get(field_list)
        if self.env.context.get("parent_id"):
            res.update({"parent_id": self.env.context.get("parent_id")})
        return res

    def create_address_contact(self):

        self.create({
            'parent_id': self.id,
            'name': self.name+' - Entrega',
            'type': 'other',
            'street': self.street,
            'company_type': 'person',
            'ubigeo': self.ubigeo,
            'district_id': self.district_id.id,
            'province_id':self.province_id.id,
            'state_id':self.state_id.id,
            'country_id':self.country_id.id
        })


    ####################################### RESTRICCIONES DE TIPO DOC PARTNERS #############
    @api.constrains('vat','l10n_latam_identification_type_id','l10n_latam_identification_type_id.l10n_pe_vat_code')
    def _check_limitation_partners(self):
        for rec in self:
            #current_user = record.env.user
            #if not current_user.has_group('gestionit_pe_fe.group_user_sunat_restrict_format_number_document'):
            if rec.l10n_latam_identification_type_id and rec.vat:
                vat_code = rec.l10n_latam_identification_type_id.l10n_pe_vat_code
                if  vat_code == '6':
                    if not bool(re.compile("\d{11}$").match(rec.vat or '')):
                         raise UserError("El tipo de Documento RUC debe ser numérico y tener 11 dígitos.")
                elif vat_code== '1':
                    if not bool(re.compile("\d{8}$").match(rec.vat or '')):
                         raise UserError("El tipo de Documento DNI debe ser numérico y tener 8 dígitos.")
                elif vat_code== 'A':
                    if not bool(re.compile("\d{15}$").match(rec.vat or '')):
                         raise UserError("El tipo de Documento CÉDULA DIPLOMÁTICA debe ser numérico y tener 15 dígitos.")
