# -*- coding: utf-8 -*-
import logging

from odoo import http, tools, _
from odoo.http import request, Response
import json


_logger = logging.getLogger(__name__)


class CustomLibroReclamaciones(http.Controller):

    @http.route('/reclamacion-enviada/<string:code>', type='http', auth='public', methods=['GET', 'POST'], website=True, csrf=False)
    def LibroReclamacionesEnviada(self, code, **kw):
        # days = request.env.company.default_claim_days_response
        post_info = request.env.company.default_post_info_claim
        return request.render('bo_libro_reclamaciones.reclamacion_enviada', {"code": code, "post_info": post_info})
        # if request.env.user._is_public():
        #     return request.render('bo_libro_reclamaciones.reclamacion_enviada')
        # else:
        #     partner_id = request.env.user.partner_id.id
        #     return request.render('bo_libro_reclamaciones.reclamacion_enviada', {"partner": partner_id})

    def _fields_required_main(self):
        return ['consumer_type', 'consumer_name', 'consumer_lastname', 'consumer_email', 'consumer_document_type', 'consumer_document',
                'consumer_phone', 'consumer_address', 'consumer_state_id', 'consumer_province_id', 'consumer_district_id',
                'product_type', 'product_code', 'order_name', 'date_order', 'product_name',
                'claim_type', 'claim_amount', 'claim_detail', 'claim_request']

    def _fields_required_consumer_type_company(self):
        return ['consumer_company_name', 'consumer_company_document']

    def _fields_required_consumer_younger(self):
        return ['consumer_younger_name', 'consumer_younger_lastname', 'consumer_younger_document']

    def validate_data_claim(self, claim):
        errors = {}
        for fld in self._fields_required_main():
            if fld not in claim or not bool(claim.get(fld, '')):
                errors[fld] = "Campo obligatorio"

        if claim.get("consumer_type", '') == 'company':
            for fld in self._fields_required_consumer_type_company():
                if fld not in claim or not bool(claim.get(fld, '')):
                    errors[fld] = "Campo obligatorio"

        if claim.get("consumer_younger", False):
            for fld in self._fields_required_consumer_younger():
                if fld not in claim or not bool(claim.get(fld, '')):
                    errors[fld] = "Campo obligatorio"

        state_id = int(claim.get("consumer_state_id", 0))
        province_id = int(claim.get("consumer_province_id", 0))
        district_id = int(claim.get("consumer_district_id", 0))
        res_country_state = request.env["res.country.state"].sudo()
        consumer_state_name = ""
        consumer_province_name = ""
        consumer_district_name = ""
        if state_id:
            consumer_state_id = res_country_state.browse(state_id)
            consumer_state_name = consumer_state_id.name
        if province_id:
            consumer_province_id = res_country_state.browse(province_id)
            consumer_province_name = consumer_province_id.name
        if district_id:
            consumer_district_id = res_country_state.browse(district_id)
            consumer_district_name = consumer_district_id.name

        claim.update({"consumer_state_name": consumer_state_name,
                      "consumer_province_name": consumer_province_name,
                      "consumer_district_name": consumer_district_name})

        return errors, claim

    def process_data_claim(self, claim):
        claim["consumer_younger"] = bool(claim.get("consumer_younger", False))
        if "csrf_token" in claim:
            del claim["csrf_token"]
        if "consumer_state_name" in claim:
            del claim["consumer_state_name"]
        if "consumer_province_name" in claim:
            del claim["consumer_province_name"]
        if "consumer_district_name" in claim:
            del claim["consumer_district_name"]
        if not claim.get("consumer_younger", False):
            for fld in self._fields_required_consumer_younger():
                if fld in claim:
                    del claim[fld]
        if claim.get("consumer_type", False) != 'company':
            for fld in self._fields_required_consumer_type_company():
                if fld in claim:
                    del claim[fld]

        return request.env["libro.reclamaciones"].sudo().create(claim)

    @http.route('/libro-reclamaciones', type='http', auth='public', methods=['GET', 'POST'], website=True, csrf=False)
    def LibroReclamaciones(self, **args):
        errors = {}
        claim = {}
        company_obj = request.env.company
        company = {
            "name": company_obj.name,
            "street": company_obj.street,
            "vat": company_obj.vat,
            "prev_info_claim": company_obj.default_prev_info_claim
        }
        country_id = request.env.ref("base.pe").id
        state_ids = request.env['res.country.state'].sudo().search(
            [('country_id', '=', country_id), ('state_id', '=', False), ('province_id', '=', False)])

        if not bool(args):
            if not request.env.user._is_public():
                partner_id = request.env.user.partner_id
                claim.update({
                    'consumer_name': partner_id.name,
                    'consumer_email': partner_id.email
                })
            return request.render('bo_libro_reclamaciones.libro_reclamaciones', {'states': state_ids,
                                                                                 'company': company,
                                                                                 'errors': errors,
                                                                                 'claim': claim})
        else:
            errors, claim = self.validate_data_claim(args)
            _logger.info(errors)
            _logger.info(claim)
            if bool(errors):
                return request.render('bo_libro_reclamaciones.libro_reclamaciones', {'states': state_ids,
                                                                                     'company': company,
                                                                                     'errors': errors,
                                                                                     'claim': claim})
            else:
                claim_obj = self.process_data_claim(claim)
                return request.redirect("/reclamacion-enviada/{}".format(claim_obj.name))

    @http.route(['/get-distrito-libro-reclamaciones'], type='json', auth="public", website=True)
    def GetDisLibroReclamaciones(self, provincia, **kw):
        return http.request.env['res.country.state'].sudo().search([('province_id', '=', int(provincia))]).mapped(lambda r: {'id': r.id, 'name': r.name})

    @http.route(['/get-provincia-libro-reclamaciones'], type='json', auth="public", website=True)
    def GetProLibroReclamaciones(self, departamento, **kw):
        return http.request.env['res.country.state'].sudo().search([('state_id', '=', int(departamento)), ('province_id', '=', False)]).mapped(lambda r: {'id': r.id, 'name': r.name})
