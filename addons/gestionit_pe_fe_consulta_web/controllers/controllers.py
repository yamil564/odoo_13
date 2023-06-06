# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)


class Buscador(http.Controller):
    @http.route('/consulta', auth='public')
    def index(self, **kwargs):
        return request.render('gestionit_pe_fe_consulta_web.form')

    @http.route('/busqueda', type='http', auth='public', method=["POST"], csrf=False)
    def consulta(self, **post):
        correlativo = post.get("correlativo", "")
        try:
            correlativo = str(int(correlativo))
        except Exception as e:
            return "El número correlativo es erróneo"

        numero = (post.get("serie") or "").upper()+"-" + correlativo.zfill(8)
        fecha = post.get("fecha")
        ruc = post.get("ruc")

        try:
            total = post.get("total")
            total = float(total)
        except Exception as e:
            pass

        documento = request.env["account.move"].sudo().search([['name', "=", numero], 
                                                                ['partner_id.vat', "=", ruc], 
                                                                ['invoice_date', '=', fecha], 
                                                                ['amount_total', '=', total]],limit=1)

        return request.render('gestionit_pe_fe_consulta_web.documentos', {'documento': documento})

