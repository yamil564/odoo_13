from odoo import models,api,fields


class SunatCatalog59(models.Model):
    _name = "sunat.catalog.59"
    _description = "Medios de Pago"

    active = fields.Boolean("Activo",default=True)
    name = fields.Char("Descripción")
    code = fields.Char("Código")

class SunatCatalog54(models.Model):
    _name = "sunat.catalog.54"
    _description = "Códigos de bienes y servicios sujetos a detracciones"

    active = fields.Boolean("Activo",default=True)
    name = fields.Char("Descripción")
    code = fields.Char("Código")
    rate = fields.Float("Tasa %")


class SunatCatalog53(models.Model):
    _name = "sunat.catalog.53"
    _description = "Códigos de cargos, descuentos y otras deducciones"

    active = fields.Boolean("Activo",default=True)
    name = fields.Char("Descripción")
    code = fields.Char("Código")


class SunatCatalog51(models.Model):
    _name = "sunat.catalog.51"
    _description = " Código de tipo de operación"

    active = fields.Boolean("Activo",default=True)
    name = fields.Char("Descripción")
    code = fields.Char("Código")
    available_factura = fields.Boolean("Factura")
    available_boleta = fields.Boolean("Boleta")


