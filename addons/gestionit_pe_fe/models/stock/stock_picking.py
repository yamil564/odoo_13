# -*- coding: utf-8 -*-
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
from odoo import fields, models, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    numero_guia = fields.Char("Número de Guía")
    tiene_guia_remision = fields.Boolean(
        "Tienes guía de Remisión", default=False)

    @api.onchange("tiene_guia_remision")
    def _set_default_tiene_guia_remision(self):
        for record in self:
            if not record.tiene_guia_remision:
                record.numero_guia = False

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if name:
            recs = self.search(['|', ('name', operator, name),
                                ('numero_guia', operator, name)] + (args or []), limit=limit)
            return recs.name_get()
        return super(StockPicking, self).name_search(name, args=args, operator=operator, limit=limit)

    def name_get(self):
        return [(rec.id, rec.name + (' - [' + rec.numero_guia+']')if rec.numero_guia else rec.name) for rec in self]
