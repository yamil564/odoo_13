from odoo import _, api, fields, models

import logging
_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
	_inherit = "res.config.settings"

	nro_maximo_exportacion = fields.Integer(string="Número Máximo de Documentos a Exportar",
		related='company_id.nro_maximo_exportacion',readonly=False)