import logging
import werkzeug
from odoo import models,fields,api
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = "website"

    signup_privacy_policies_active = fields.Boolean("Activar Política de seguridad en registro de cliente",
                                            default=True)
    signup_privacy_policies_label = fields.Html("Label de Política de seguridad en registro",
                                            default="<span>He leído y acepto las <a href='/termino_y_condiciones' target='_blank'>Términos y condiciones</a> del sitio. Acepto tambien las <a href='/politica_privacidad' target='_blank'>Políticas de privacidad</a> y tratamiento de datos personales</span>") 

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    signup_privacy_policies_active = fields.Boolean("Activar Política de seguridad en registro de cliente",
                                            related="website_id.signup_privacy_policies_active",
                                            readonly=False)
    signup_privacy_policies_label = fields.Html("Label de Política de seguridad en registro",
                                            related="website_id.signup_privacy_policies_label",
                                            readonly=False)

class ResUsers(models.Model):
    _inherit = "res.users"
    accept_privacy_policies = fields.Boolean("Acepto políticas de privacidad?",default=False)


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    accept_privacy_policies = fields.Boolean("Acepto políticas de privacidad?",default=False)
