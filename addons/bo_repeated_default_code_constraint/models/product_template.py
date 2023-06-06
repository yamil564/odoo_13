from odoo import models,api,fields
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import re
import logging
logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.constrains('default_code')
    def _check_default_code(self):
        for record in self:
            referece = self.env['product.template'].search([('default_code', 'not in', ('', False)), ('default_code', '=', self.default_code), ('id', '!=', self.id), ('company_id', 'in' , (self.env.company.id,False))])

            if referece.exists():
                raise ValidationError('Ya existe un producto con la misma Referencia Interna.')