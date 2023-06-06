import pytz
import calendar
import base64
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, timedelta

from odoo.addons import ple_base as tools

import logging
_logger=logging.getLogger(__name__)

class PlePurchaseLine(models.Model):
	_inherit = 'ple.purchase.line'


	fecha_detraccion=fields.Date(string="Fecha Detracción",compute='_compute_campo_fecha_detraccion' , store=True)
	numero_detraccion=fields.Char(string="Número Detracción",compute='_compute_campo_numero_detraccion' ,store=True)



	@api.depends('move_id','move_id.register_detraction_id')
	def _compute_campo_fecha_detraccion(self):
		for rec in self:
			if rec.move_id.register_detraction_id:
				rec.fecha_detraccion = rec.move_id.register_detraction_id.fecha_pago or False



	@api.depends('move_id','move_id.register_detraction_id')
	def _compute_campo_numero_detraccion(self):
		for rec in self:
			if rec.move_id.register_detraction_id:
				rec.numero_detraccion = rec.move_id.register_detraction_id.nro_constancia or ''

	############################################################################