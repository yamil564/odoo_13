# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError
from odoo.addons.gestionit_pe_fe.models.parameters.catalogs import tdc
import logging
_logger=logging.getLogger(__name__)

class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	prefix_code=fields.Char(string="Serie del Comprobante")
	invoice_number=fields.Char(string="Correlativo del Comprobante")

	type_document_id = fields.Selection(string="Tipo de Documento",selection="_selection_invoice_type")
	
	date_emission = fields.Date(string="Fecha de Emisión")


	def _selection_invoice_type(self):
		return tdc