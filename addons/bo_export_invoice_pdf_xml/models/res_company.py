from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning

class ResCompany(models.Model):
	_inherit = "res.company"

	nro_maximo_exportacion = fields.Integer(string="Número Máximo de Documentos a Exportar")