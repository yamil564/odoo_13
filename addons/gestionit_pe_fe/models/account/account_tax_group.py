# -*- coding: utf-8 -*-
from odoo import fields, models, api


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    codigo = fields.Char(string='Código', size=4, index=True, required=True)
    codigo_inter = fields.Char(string='Código internacional', size=3)
    descripcion = fields.Char(string='Descripción', size=128, index=True, required=True)
    no_onerosa = fields.Boolean(string='No onerosa')
    # tipo = fields.Selection([('gravado', 'Gravado'), ('exonerado', 'Exonerado'), ('inafecto', 'Inafecto')], string='Tipo')
    tipo_afectacion = fields.Char(string="Afectación")
