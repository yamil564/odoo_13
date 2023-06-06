from odoo import models,fields,api
from odoo.http import request
import logging
# _logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = "website"
    has_botpress = fields.Boolean("Botpress",default=False)
    botpress_bot_id = fields.Char("Botpress Bot Id")
    botpress_host = fields.Char("Botpress Host")
    botpress_url_stylesheet = fields.Char("Botpress Stylesheet")

    def get_botpress_host(self):
        if self.botpress_host:
            return self.botpress_host
        return False
    
    def get_botpress_bot_id(self):
        if self.botpress_bot_id:
            return self.botpress_bot_id
        return False
        
class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    has_botpress = fields.Boolean(related="website_id.has_botpress",readonly=False)
    botpress_bot_id = fields.Char(related="website_id.botpress_bot_id",readonly=False)
    botpress_host = fields.Char(related="website_id.botpress_host",readonly=False)
    botpress_url_stylesheet = fields.Char(related="website_id.botpress_url_stylesheet",readonly=False)

