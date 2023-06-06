# -*- coding: utf-8 -*-
from odoo import fields,models,api

class einvoice_catalog_07(models.Model):
    _name = "tipo.afectacion"
    _description = 'Codigos de Tipo de Afectacion del IGV'

    code = fields.Char(string='Codigo', size=4, index=True, required=True)
    name = fields.Char(string='Descripcion', size=128, index=True, required=True)
    no_onerosa = fields.Boolean(string='No onerosa')
    type = fields.Selection([('gravado','Gravado'),('exonerado','Exonerado'),('inafecto','Inafecto')],string='Tipo')
    
    # @api.multi
    # @api.depends('code', 'name')
    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         for table in rec:
    #             l_name = table.code and table.code + ' - ' or ''
    #             l_name +=  table.name
    #             result.append((table.id, l_name ))
    #         return result