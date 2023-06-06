# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
import logging
import requests
import json
_logger = logging.getLogger(__name__)


class WizardSaleOrderContingencia(models.TransientModel):
	_name='wizard.sale.order.contingencia'
	_description = "Crear Documentos de Contingencia desde Ventas"



	sale_order_id = fields.Many2one('sale.order',string="Orden de Venta",readonly=True)

	type_document = fields.Selection(selection=[('01',"Factura"),('03',"Boleta")])

	prefix_code_contingencia_id = fields.Many2one('account.journal',
		string="Serie de Contingencia",
		required=True)

	invoice_number_contingencia = fields.Char(string="Número de Documento Contingencia",
		required=True)

	sale_order_enable_ids = fields.Many2many('account.journal',string="Series Permitidas")
		#,related="sale_order_id.sale_order_enable_ids")

	
	def create_document_contingencia(self):
		if self.sale_order_id and self.type_document:
			if not self.prefix_code_contingencia_id or not self.invoice_number_contingencia:
				raise UserError(
					"El número de Serie y Número de Documento de Contingencia son Obligatorios, por favor llenelos !")
			self.sale_order_id.write({'prefix_code_contingencia_id':self.prefix_code_contingencia_id or False})
			self.sale_order_id.write({'invoice_number_contingencia':self.invoice_number_contingencia or ''})


			if self.type_document=='01':
				if len(self.sale_order_id.invoice_ids) == 0:
					self.sale_order_id.write({'tipo_documento':"01"})
					move = self.sale_order_id._create_invoices(final=True)
					move._onchange_recompute_dynamic_lines()

			elif self.type_document=='03':
				_logger.info('\n\nHONGETEEEEEEE\n\n')
				if len(self.sale_order_id.invoice_ids) == 0:
					self.sale_order_id.write({'tipo_documento':"03"})
					move = self.sale_order_id._create_invoices(final=True)
					move._onchange_recompute_dynamic_lines()
					_logger.info('\n\nHONGUITO 2021 !!!\n\n')

			return self.sale_order_id.action_view_invoice()

	#############################################