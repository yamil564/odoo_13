from odoo import models,api,fields
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import re
import logging
logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_default_code(self):
        sequence = self.env['ir.sequence'].search([('code', '=', 'ref.prod'), ('company_id', 'in' , (self.env.company.id,))], limit=1)
        if sequence:
            return sequence.number_next_actual
        else:
            return 0

    default_code = fields.Char(required=False, default=_get_default_code)
    selector_default_code = fields.Selection([('manual','M'), ('automatic','A')], string='Selector Type Code', default='automatic')

    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if res.default_code not in ('', False):
            sequence = self.env['ir.sequence'].search([('code', '=', 'ref.prod'), ('company_id', 'in' , (self.env.company.id,))], limit=1)
            if self.env.context.get('dryrun', False):
                sequence.number_next_actual = int(res.default_code ) + 1
            return res

    def write(self, values):
        values['selector_default_code'] = 'automatic'
        res = super(ProductTemplate, self).write(values)
        return res

    @api.constrains('default_code')
    def _check_default_code_aux(self):
        for record in self:
            referece = self.env['product.template'].search([('default_code', 'not in', ('', False)), ('default_code', '=', self.default_code), ('id', '!=', self.id), ('company_id', 'in' , (self.env.company.id,False))])
            if (self.default_code or "0").isdigit():
                sequence = self.env['ir.sequence'].search([('code', '=', 'ref.prod'), ('company_id', 'in' , (self.env.company.id,))], limit=1)
                if int(self.default_code) > int(sequence.number_next_actual):
                    raise ValidationError('La Referencia Interna no puede ser mayor al siguiente número de su secuencia.')

            if referece.exists():
                raise ValidationError('No se puede repetir la Referencia Interna.')

class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_default_code(self):
        return self.env["ir.sequence"].next_by_code("ref.prod")

    default_code = fields.Char(required=False, default=_get_default_code)
