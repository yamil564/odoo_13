from odoo import api,models,fields
from odoo.exceptions import UserError, ValidationError
import re

class Website(models.Model):
    _inherit = "website"
    has_google_conversion_tracking = fields.Boolean(string="Google Seguimiento de conversiones",default=False)
    google_conversion_tracking_code = fields.Char("Código de seguimiento de conversiones")

class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"
    google_conversion_tracking_code = fields.Char(related="website_id.google_conversion_tracking_code",readonly=False)
    has_google_conversion_tracking = fields.Boolean(related="website_id.has_google_conversion_tracking",readonly=False)

    @api.constrains('google_conversion_tracking_code')
    def _check_google_conversion_tracking_code(self):
        for record in self:
            pattern = re.compile("[a-zA-Z]{2}[-]\d{11}")
            if not pattern.match(record.google_conversion_tracking_code):
                raise UserError("El formato del código de conversión de seguimiento es incorrecto.")
            
    