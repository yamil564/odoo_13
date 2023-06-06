from odoo import api,models,fields
from odoo.exceptions import UserError, ValidationError
import re

class Website(models.Model):
    _inherit = "website"
    has_facebook_pixel = fields.Boolean(string="Facebook Pixel",default=False)
    facebook_pixel_code = fields.Char("Código de Facebook Pixel")

class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"
    facebook_pixel_code = fields.Char(related="website_id.facebook_pixel_code",readonly=False)
    has_facebook_pixel = fields.Boolean(related="website_id.has_facebook_pixel",readonly=False)

    @api.constrains('facebook_pixel_code')
    def _check_facebook_pixel_code(self):
        for record in self:
            pattern = re.compile("\d{16}")
            if not pattern.match(record.facebook_pixel_code):
                raise UserError("El formato del código de Facebook Pixel es incorrecto.")
            
    