import logging
import werkzeug
from odoo import models,fields,api
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = "website"

    allow_receive_mails_active = fields.Boolean("Activar confirmación de envío de correos en checkout de compra",
                                            default=True)
    allow_receive_mails_label = fields.Html("Label de confirmación para recibir correos",
                                            default="<span>Enviarme novedades y ofertas por correo electrónico</span>") 

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    allow_receive_mails_active = fields.Boolean("Activar confirmación de envío de correos en checkout de compra",
                                            related="website_id.allow_receive_mails_active",
                                            readonly=False)
    allow_receive_mails_label = fields.Html("Label de confirmación para recibir correos",
                                            related="website_id.allow_receive_mails_label",
                                            readonly=False)
