from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import logging
_logger = logging.getLogger(__name__)

class WebsiteSaleCountryExtend(WebsiteSale):

    @http.route(['/get-distrito'], type='json', auth="public", website=True)
    def GetDistrito(self, provincia, **kw):
        distritos = http.request.env['res.country.state'].sudo().search(
            [('province_id', '=', int(provincia))])
        dis = []
        for distrito in distritos:
            news = {
                "id": distrito.id,
                "name": distrito.name,
            }
            dis.append(news)

        return dis

    @http.route(['/get-provincia'], type='json', auth="public", website=True)
    def GetProvincia(self, departamento, **kw):
        provincias = http.request.env['res.country.state'].sudo().search(
            [('state_id', '=', int(departamento)), ('province_id', '=', False)])
        pro = []

        for provincia in provincias:
            news = {
                "id": provincia.id,
                "name": provincia.name,
            }
            pro.append(news)
        return pro

    @http.route(['/get-departamento'], type='json', auth="public", website=True)
    def GetDepartamento(self, pais, **kw):
        pais = http.request.env['res.country'].sudo().search([('code', '=', 'PE')]).id
        departamentos = http.request.env['res.country.state'].sudo().search(
            [('country_id', '=', pais),
             ('state_id', '=', False),
             ('province_id', '=', False)])
        dep = []
        for departamento in departamentos:
            news = {
                "id": departamento.id,
                "name": departamento.name,
            }
            dep.append(news)

        return dep
