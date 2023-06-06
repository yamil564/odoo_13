# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    porcentaje_retencion = fields.Char(
        string="Porcentaje de Retención %",
        default="3.00",
        config_parameter='porcentaje_retencion'
    )
    monto_minimo_retencion = fields.Char(
        string="Monto Mínimo Retención",
        default="700.00",
        config_parameter='monto_minimo_retencion'
    )


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        porcentaje_retencion = self.env['ir.config_parameter'].sudo().get_param('porcentaje_retencion')
        monto_minimo_retencion = self.env['ir.config_parameter'].sudo().get_param('monto_minimo_retencion')
        res.update(
            porcentaje_retencion=porcentaje_retencion,
            monto_minimo_retencion=monto_minimo_retencion
        )
        return res


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param("porcentaje_retencion", self.porcentaje_retencion)
        self.env['ir.config_parameter'].set_param("monto_minimo_retencion", self.monto_minimo_retencion)