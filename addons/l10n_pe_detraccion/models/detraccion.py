from odoo import api, fields, models, _

class TipoDetraccion(models.Model):
	_name = "tipo.detraccion"
	_description = "Tipo de Detraccion"

	name = fields.Char(string="Nombre", required=True)
	anexo = fields.Char(string="Anexo", required=True)
	code = fields.Char(string=u"Código", required=True, size=3)
	code_fe = fields.Char(string="Código FE")
	line_ids = fields.One2many('tipo.detraccion.line', 'detraccion_id', string="Productos y/o Servicios")
	description = fields.Text(string="Comentario")

	_sql_constraints = [
		('anexo_code_uniq', 'unique(anexo,code)', 'El anexo-codigo tiene que ser Unico!'),
	]


	def name_get(self):
		result = []
		for detra in self:
			result.append((detra.id, "%s-%s-%s" % (detra.anexo, detra.code, detra.name)))
		return result

	@api.model
	def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
		args = args or []
		recs = []
		if name:
			recs = self._search([('code', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
		if not recs:
			recs = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
		return self.browse(recs).name_get()

class DetraccionDetalle(models.Model):
	_name = "tipo.detraccion.line"
	_description = "Productos y/o servicio de detraccion"
	_rec_name = "detraccion_id"
	_order = "date desc"

	detraccion_id = fields.Many2one('tipo.detraccion', string="Detraccion",
		required=True, ondelete='cascade', index=True, copy=False)
	product_id = fields.Many2many('product.product', string="Producto y/o Servicio")
	amount = fields.Float(string="Monto", required=True)
	porcentaje = fields.Float(string="Porcentaje", required=True)
	date = fields.Date(string="Fecha", required=True)

	@api.model
	def get_detraccion(self, product, date):
		detraccion = self.search([
			('product_id','=',product),('date','<=',date)
			], limit=1, order="date")
		return detraccion