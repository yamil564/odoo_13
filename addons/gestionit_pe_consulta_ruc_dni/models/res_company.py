# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
import logging
import requests
import json
_logger = logging.getLogger(__name__)

patron_dni = re.compile("\d{8}$")
patron_ruc = re.compile("[12]\d{10}$")

class ResCompany(models.Model):
    _inherit = ['res.company']

    api_migo_endpoint = fields.Char(string="API Migo - Endpoint")
    api_migo_token = fields.Char(string="API Migo - Token")

    """
    'request_number_identificacion_partner' es una función usada tambien por el punto de venta para consultar a un api externo
    los datos de un número de DNI o RUC, por defecto se usa el servicio de migo.pe, sin embargo, esta función
    puede ser sobrecargada para consumir otro servicio.
    Debe considerar que los datos que debe devolver request_number_identificacion_partner deben ser valores con los campos de res.partner
    """    

    @api.model
    def request_number_identificacion_partner(self,tipo_doc,num_doc):
        num_doc = num_doc.strip()
        if tipo_doc not in ["1","6"]:
            raise UserError("Los tipos de documentos permitidos son '1':DNI y '6':RUC")

        if tipo_doc == "1":
            if not patron_dni.match(num_doc):
                raise UserError("El número de DNI no es válido")

            vals = self.request_migo_dni(num_doc)
            if not vals:
                return {}
            return {"name":vals["name"]}
        elif tipo_doc == "6":
            if not patron_ruc.match(num_doc):
                raise UserError("El número de RUC no es válido")

            response = self.request_migo_ruc(num_doc)
            vals = {}
            if not response:
                return {}

            ditrict_obj = self.env['res.country.state']
            prov_ids = ditrict_obj.search([('name', '=', response['provincia']),
                                            ('province_id', '=', False),
                                            ('state_id', '!=', False)])
            dist_id = ditrict_obj.search([('name', '=', response['distrito']),
                                            ('province_id', '!=', False),
                                            ('state_id', '!=', False),
                                            ('province_id', 'in', [x.id for x in prov_ids])], limit=1)
            if dist_id:
                vals.update({"district_id":dist_id.id,
                    "province_id":dist_id.province_id.id,
                    "state_id":dist_id.state_id.id,
                    "country_id":dist_id.country_id.id
                })

            vals.update({
                "estado_contribuyente":response['estado_del_contribuyente'],
                "name":response['nombre_o_razon_social'],
                "registration_name": response['nombre_o_razon_social'],
                "ubigeo":response["ubigeo"],
                "street":response['direccion'],
                "is_company":True,
                "company_type":"company"
            })

            return vals

    @api.model
    def request_migo_dni(self, dni):
        user = self.env.user
        url = user.company_id.api_migo_endpoint + "dni"
        token = user.company_id.api_migo_token
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            data = {
                "token": token,
                "dni": dni
            }
            res = requests.request(
                "POST", url, headers=headers, data=json.dumps(data),timeout=3)
            res = res.json()
            if res.get("success", False):
                return {"name":res.get("nombre", False)}
            return {}
        except Exception as e:
            return {}
        

    @api.model
    def request_migo_ruc(self, ruc):
        errors = []
        user = self.env.user

        if not user.company_id.api_migo_endpoint:
            errors.append("Debe configurar el end-point del API")
        if not user.company_id.api_migo_token:
            errors.append("Debe configurar el token del API")
        if len(errors) > 0:
            raise UserError("\n".join(errors))
        else:
            url = user.company_id.api_migo_endpoint + "ruc"
            token = user.company_id.api_migo_token
            try:
                headers = {
                    'Content-Type': 'application/json'
                }
                data = {
                    "token": token,
                    "ruc": ruc
                }
                res = requests.request(
                    "POST", url, headers=headers, data=json.dumps(data),timeout=3)
                res = res.json()

                if res.get("success", False):
                    return res
                return {}
            except Exception as e:
                _logger.info(e)
                return {}

        return {}