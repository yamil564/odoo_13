from odoo import http
from odoo.http import request
import requests
import json
from odoo.addons.website_sale.controllers.main import WebsiteSale
import logging
import re
from werkzeug.exceptions import Forbidden, NotFound
_logger = logging.getLogger(__name__)

class WebsiteSaleExtend(WebsiteSale):

    def _get_mandatory_billing_fields(self):
        res = super(WebsiteSaleExtend,self)._get_mandatory_billing_fields()
        res.append("vat")
        res.append("l10n_latam_identification_type_id")
        res.append("state_id")
        res.append("province_id")
        res.append("district_id")

        # res.remove("street")
        res.remove("city")
        res.remove("country_id")
        return res

    def _get_mandatory_shipping_fields(self):
        res = super(WebsiteSaleExtend,self)._get_mandatory_shipping_fields()
        res.remove("street")
        res.remove("city")
        res.remove("country_id")

        return res

    def checkout_form_validate(self, mode, all_form_values, data):
        error, error_message  = super(WebsiteSaleExtend,self).checkout_form_validate(mode, all_form_values, data)
        # _logger.info(data.get("vat"))
        # _logger.info(data.get("l10n_latam_identification_type_id"))
        vat = data.get("vat",False)
        l10n_latam_identification_type_id = data.get("l10n_latam_identification_type_id")
        if vat or l10n_latam_identification_type_id:
            if not request.env["res.partner"].check_number_doc(vat,l10n_latam_identification_type_id):
                error["vat"] = "error"
                error["l10n_latam_identification_type_id"] = "error"
                error_message.append("Número de documento o Tipo de documento inválido")
        # _logger.info(data)
        if not data.get("allow_receive_mails",False):
            error["allow_receive_mails"] = "error"

        if not data.get("accept_privacy_policies",False):
            error["accept_privacy_policies"] = "error"

        # _logger.info(error)
        # _logger.info(error_message)
        return error, error_message

    @http.route("/change_invoice_type_code",type="json",method="POST",csrf=True,auth="public", website=True)
    def change_invoice_type_code(self,**kargs):
        order = request.website.sale_get_order()
        order.sudo().write({"invoice_type_code":kargs.get("invoice_type_code")})
        return True

    def checkout_redirection(self,order):
        res = super(WebsiteSaleExtend,self).checkout_redirection(order)
        return res

    @http.route(['/change_vat'], type='json', auth="public", website=True)
    def change_vat(self, **kw):
        """
            Este Método regresa la información concerniente al numero de identificación
            :param kwargs:
            :return:
        """

        partner_id = request.env['res.partner'].sudo().search([('vat','=', str(kw.get("vat")))], limit=1)
        type = request.env['l10n_latam.identification.type'].sudo().search([('id','=', int(kw['type']))], limit=1)
        patron_ruc = re.compile("[12]\d{10}$")
        patron_dni = re.compile("\d{8}$")
        razon = False
        partner = False
        validate = False
        district = False
        province = False
        department = False
        address = False
        country = request.env['res.country'].search([('code', '=', 'PE')], limit=1).id

        type = request.env['l10n_latam.identification.type'].search([('id', '=', int(kw['type']))])

        if type.l10n_pe_vat_code == '1':

            if len(kw['vat'].strip()) == 8:
                partner = self.request_migo_dni(kw['vat'].strip(), "dni")
                validate = True

        elif type.l10n_pe_vat_code == '6':

            if patron_ruc.match(kw['vat']):
                vat_arr = [int(c) for c in kw['vat']]
                arr = [5,4,3,2,7,6,5,4,3,2]
                s = sum([vat_arr[r]*arr[r] for r in range(0,10)])
                num_ver = (11-s%11)%10
                if vat_arr[10] == num_ver:
                    validate = True
                    call = self.request_migo_dni(kw['vat'].strip(), "ruc")
                    partner = call['name']

                    loc = request.env['res.country.state'].search([('code', '=', call['ubigeo'])])
                    address = call['address']

                    if loc.province_id:
                        if loc.state_id:
                            district = loc.id
                            province = loc.province_id.id
                            department = loc.state_id.id
                        else:
                            department = loc.id
                            province = loc.province_id.id
                    else:
                        department = loc.id

                    if len(call['ubigeo']) == 6:
                        district = request.env['res.country.state'].search([('code', '=', call['ubigeo'])])
                        province = district.province_id.id
                        department = district.state_id.id
                        district = district.id
                    elif len(call['ubigeo']) == 4:
                        province = request.env['res.country.state'].search([('code', '=', call['ubigeo'])])
                        department = province.state_id.id
                        province = province.id
                    elif len(call['ubigeo']) == 2:
                        department = request.env['res.country.state'].search([('code', '=', call['ubigeo'])]).id
                    razon = partner
        vals = {
            'name':partner,
            'validate':validate,
            'razon':razon,
            'district':district,
            'province':province,
            'department':department,
            'country':country,
            'address':address,
        }
        return vals

    def request_migo_dni(self, dni, type):
        companys = request.env.context.get('allowed_company_ids', False)
        if companys:
            company = request.env["res.company"].sudo().browse(companys[0])
            url = company.api_migo_endpoint + type
            token = company.api_migo_token
            headers = {'Content-Type': 'application/json'}
            if type == "dni":
                # data = {"token": "yQfQ97SvS38y3ZF9GMYZjBChKa1ajM4OzuRspcm7Eq22H7OETuxj9c17Vv3F", "dni": dni}
                data = {"token": token, "dni": dni}
            else:
                # data = {"token": "yQfQ97SvS38y3ZF9GMYZjBChKa1ajM4OzuRspcm7Eq22H7OETuxj9c17Vv3F", "ruc": dni}
                data = {"token": token, "ruc": dni}
        else:
            return False

        try:
            res = requests.request("POST", url, headers=headers, data=json.dumps(data))
            res = res.json()
            if res.get("success", False):
                if type == "dni":
                    return res.get("nombre", False)
                else:
                    ubigeo = str(res.get("ubigeo",False))
                    address = str(res.get("direccion_simple",False))
                    return {'name':res.get("nombre_o_razon_social", False), 'ubigeo':ubigeo, 'address':address}
            return False
        except Exception as e:
            return False

    def _checkout_form_save(self, mode, checkout, all_values):
        # _logger.info(mode)
        # _logger.info(all_values)
        # _logger.info(checkout)
        Partner = request.env['res.partner']
        if mode[0] == 'new':
            vat = checkout.get("vat")
            if vat:
                commercial_partner_id = Partner.sudo().search([("vat","=",vat),("parent_id","=",False)])
                if commercial_partner_id.exists():                
                    checkout.update({"commercial_partner_id":commercial_partner_id[0].id,"parent_id":commercial_partner_id[0].id})
                    del checkout["vat"]
                    del checkout["l10n_latam_identification_type_id"]
                
            # _logger.info(checkout)
            partner = Partner.sudo().with_context(tracking_disable=True).create(checkout)
            partner.country_id = int(request.env.ref("base.pe").id)
            partner.state_id = int(all_values['state_id'])
            partner.province_id = int(all_values['province_id'])
            partner.district_id = int(all_values['district_id'])
            if partner.district_id:
                    partner.ubigeo = partner.district_id.code or ""
            partner_id = partner.id
        elif mode[0] == 'edit':
            partner_id = int(all_values.get('partner_id', 0))
            if partner_id:
                # double check
                order = request.website.sale_get_order()
                shippings = Partner.sudo().search([("id", "child_of", order.partner_id.commercial_partner_id.ids)])
                if partner_id not in shippings.mapped('id') and partner_id != order.partner_id.id:
                    return Forbidden()
                partner = Partner.browse(partner_id).sudo()

                partner.write(checkout)
                partner.country_id = int(request.env.ref("base.pe").id)
                partner.state_id = int(all_values['state_id'])
                partner.province_id = int(all_values['province_id'])
                partner.district_id = int(all_values['district_id'])
                partner.allow_receive_mails = bool(all_values['allow_receive_mails'])
                partner.accept_privacy_policies = bool(all_values['accept_privacy_policies'])
                # _logger.info(partner.district_id.code)
                if partner.district_id:
                    partner.ubigeo = partner.district_id.code or ""
        return partner_id
