from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError
import logging
_logger=logging.getLogger(__name__)

class SunatCatalog10(models.Model):
    _name = "sunat.catalog.10"
    _description = "Tipo de Comprobante de Pago o Documento"

    active = fields.Boolean("Activo",default=True)
    name = fields.Char("Descripción")
    code = fields.Char("Código")