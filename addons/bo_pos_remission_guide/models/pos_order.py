from odoo import _, api, fields, models
from odoo.exceptions import Warning, UserError, ValidationError

import logging
logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def get_ubigeo_guia(self, departament, province, district):
        departament_id = self.env['res.country.state'].browse(int(departament))
        province_id = self.env['res.country.state'].browse(int(province))
        district_id = self.env['res.country.state'].browse(int(district))
        provinces = self.env['res.country.state'].search([('state_id','=',departament_id.id),('province_id','=',False)])
        ubigeo = False
        province_id_v = province_id.id

        if province_id in provinces:
            districts = self.env['res.country.state'].search([('province_id','=',province_id.id)])
            province_id_v = province_id.id
            if district_id in districts:
                ubigeo = district_id.code or ''
                district_id_v = district_id.id or False
            else:
                ubigeo = districts[0].code if districts else ''
                district_id_v = districts[0].id if districts else False
        else:
            districts = self.env['res.country.state'].search([('province_id','=',provinces[0].id)])
            ubigeo = districts[0].code or ''
            district_id_v = districts[0].id if districts else False
            province_id_v = provinces[0].id if provinces else False

        return {
            'provinces':[(line.id, line.name) for line in provinces] or False,
            'districts':[(line.id, line.name) for line in districts] or False,
            'ubigeo':ubigeo,
            'province_id':province_id_v,
            'district_id':district_id_v
        }

    def get_fields_popup_guia(self):
        transport_companys = self.env['res.partner'].search([('es_empresa_transporte_publico', '=', 'True')])
        drivers = self.env['res.partner'].search([('parent_id', 'in', transport_companys.ids), ('parent_id', '!=', False)])
        departaments = self.env['res.country.state'].search([('state_id','=',False), ('province_id','=',False),('country_id', '=', self.env.company.partner_id.country_id.id)])
        provinces = self.env['res.country.state'].search([('state_id','!=',False), ('province_id','=',False),('country_id', '=', self.env.company.partner_id.country_id.id)])
        districts = self.env['res.country.state'].search([('state_id','!=',False), ('province_id','!=',False),('country_id', '=', self.env.company.partner_id.country_id.id)])
        cars = self.env['gestionit.vehiculo'].search([])
        street = self.partner_id.street
        state_id = self.partner_id.state_id.name
        province_id = self.partner_id.province_id.name
        district_id = self.partner_id.district_id.name
        ubigeo = self.partner_id.ubigeo
        total_weight = 0
        for line in self.lines:
            total_weight += line.product_id.weight
        return {
            'order':self.id,
            'transport_companys': [(line.id, line.name) for line in transport_companys],
            'street':street,
            'state_id':state_id,
            'province_id':province_id,
            'district_id':district_id,
            'ubigeo':ubigeo,
            'total_weight':total_weight,
            'company_street':self.env.company.partner_id.street,
            'drivers':[(line.id, line.name, line.parent_id) for line in drivers] or False,
            'departaments':[(line.id, line.name) for line in departaments],
            'provinces':[(line.id, line.name) for line in provinces],
            'districts':[(line.id, line.name) for line in districts],
            'department_id':self.partner_id.state_id.id if self.partner_id.state_id else '',
            'province_id':self.partner_id.province_id.id if self.partner_id.province_id else '',
            'district_id':self.partner_id.district_id.id if self.partner_id.district_id else '',
            'cars':[(line.id, line.marca + '-' + line.modelo + '-' + line.numero_placa) for line in cars],
        }
        
    def print_guia(self,starting_address, remission_guide_arrival_address, remission_guide_weight, remission_guide_department, remission_guide_province, remission_guide_district, remission_guide_ubigeo, remission_guide_transport_companys, remission_guide_driver, remission_guide_car):
        if self.account_move:
            if not self.account_move.guia_remision_ids:
                guia_vals = self.account_move.action_context_default_guia_remision()
                lines = []
                llegada = self.env['res.partner'].browse(guia_vals["default_destinatario_partner_id"])
                ubigeo = self.env['res.country.state'].browse(int(remission_guide_district))
                transport_id = self.env['res.partner'].browse(int(remission_guide_transport_companys))
                driver_id = False
                car_id = False
                if remission_guide_driver:
                    driver = self.env['res.partner'].browse(int(remission_guide_driver))
                    if driver:
                        driver_id = driver.id
                
                if remission_guide_car:
                    car = self.env['gestionit.vehiculo'].browse(int(remission_guide_car))
                    if car:
                        car_id = car.id

                for invoice in guia_vals["default_comprobante_pago_ids"]:
                    invoice = self.env['account.move'].browse(invoice[2][0])
                    for line in invoice.invoice_line_ids:
                        if line.product_id.type == 'product':
                            lines.append((0,0,{
                                'product_id':line.product_id.id,
                                'description':line.name,
                                'uom_id':line.product_uom_id.id,
                                'qty':line.quantity,
                            }))
                vals = {
                    "documento_asociado":guia_vals["default_documento_asociado"],
                    "fecha_emision":guia_vals["default_fecha_emision"],
                    "fecha_inicio_traslado":guia_vals["default_fecha_inicio_traslado"],
                    "motivo_traslado":guia_vals["default_motivo_traslado"],
                    "comprobante_pago_ids":guia_vals["default_comprobante_pago_ids"],
                    "destinatario_partner_id":guia_vals["default_destinatario_partner_id"],
                    "company_partner_id":guia_vals["default_company_partner_id"],
                    "company_id":guia_vals["default_company_id"],
                    "guia_remision_line_ids":lines,
                    "direccion_partida_id":self.env.company.partner_id.id,
                    "lugar_partida_direccion":starting_address,
                    "lugar_partida_ubigeo_code":self.env.company.partner_id.district_id.id or self.env.company.partner_id.province_id.id or self.env.company.partner_id.state_id.id,
                    "direccion_llegada_id":llegada.id,
                    "lugar_llegada_direccion":remission_guide_arrival_address,
                    "lugar_llegada_ubigeo_code":ubigeo.id,
                    "modalidad_transporte":"01",
                    "transporte_partner_id":transport_id.id,
                    "peso_bruto_total":float(remission_guide_weight),
                    "conductor_publico_id": driver_id or False,
                    "vehiculo_publico_id": car_id or False
                }
                guia_id = self.env['gestionit.guia_remision'].create(vals)
                guia_id.post()
            else:
                guia_id = self.account_move.guia_remision_ids[0]
                if guia_id.state =='borrador':
                    guia_id.post()
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url_report = '{base}/report/pdf/gestionit_pe_fe.report_guia_remision_template/{id}'.format(base = base_url, id = guia_id.id)
            return url_report

        else:
            raise UserError(("Para generar una Guía de Remisión debe crear una Boleta o factura."))