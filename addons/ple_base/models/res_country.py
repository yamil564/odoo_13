from odoo import models, fields, api, _
class ResCountry(models.Model):
	_inherit = 'res.country'

	codigo_sunat = fields.Char(string="Código Sunat" , size = 4)

	_sql_constraints = [
        ('Código Sunat', 'UNIQUE (codigo_sunat)',  'El código ingresado para este pais ya existe !!')

    ]