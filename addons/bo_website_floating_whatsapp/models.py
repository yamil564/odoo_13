from odoo import models,fields,api
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = "website"

    website_floating_whatsapp = fields.Char("Celular Whatsapp")
    website_floating_whatsapp_location = fields.Selection(string="Ubicación",selection=[("right","Derecha"),("left","Izquierda")],default="left")
    website_floating_whatsapp_message_shop = fields.Text("Mensaje WSP Shop")
    website_floating_whatsapp_message_product = fields.Text("Mensaje WSP Producto")
    website_floating_whatsapp_message_order = fields.Text("Mensaje WSP Orden")

    def get_whatsapp_url(self):
        url = "https://wa.me/{}?text={}"
        # _logger.info(request.httprequest.__dict__)
        path = request.httprequest.__dict__.get("path","")
        # _logger.info(path)
        order = self.sale_get_order()
        if not order:
            order = self.sale_get_order(force_create=True)

        if "/shop/product" in path and ("{producto}" in self.website_floating_whatsapp_message_product):
            path = path.split("?")[0]
            product_id = path.split("-")[-1]
            try:
                product = self.env["product.template"].browse(int(product_id))
                return url.format(self.website_floating_whatsapp,self.website_floating_whatsapp_message_product.format(producto=product.display_name))
            except Exception as e:
                pass
        elif ("/shop" in path or "/payment" in path or "/checkout" in path) and len(order.order_line) > 0:
            return url.format(self.website_floating_whatsapp,self.website_floating_whatsapp_message_order.format(orden=order.name))
        elif "/shop" in path or "/" == path:
            return url.format(self.website_floating_whatsapp,self.website_floating_whatsapp_message_shop)
        if "/slides" in path and ("{producto}" in self.website_floating_whatsapp_message_product):
            path = path.split("?")[0]
            product_id = path.split("-")[-1]
            try:
                product = self.env["slide.channel"].browse(int(product_id))
                return url.format(self.website_floating_whatsapp,self.website_floating_whatsapp_message_product.format(producto=product.display_name))
            except Exception as e:
                pass
        return False

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_floating_whatsapp = fields.Char(related="website_id.website_floating_whatsapp",
                                            readonly=False,
                                            default="")
    website_floating_whatsapp_message_shop = fields.Text(related="website_id.website_floating_whatsapp_message_shop",
                                                        readonly=False,
                                                        default="Hola, estoy interesado en sus productos.")
    website_floating_whatsapp_message_product = fields.Text(related="website_id.website_floating_whatsapp_message_product",
                                                            readonly=False,
                                                            default="Hola, estoy interesado en este producto {producto}.")
    website_floating_whatsapp_message_order = fields.Text(related="website_id.website_floating_whatsapp_message_order",
                                                            readonly=False,
                                                            default="Hola, mi número de compra es {orden}, me puedes ayudar con mi compra porfavor.")
    website_floating_whatsapp_location = fields.Selection(string="Ubicación",
                                                        related="website_id.website_floating_whatsapp_location",
                                                        selection=[("right","Derecha"),("left","Izquierda")],
                                                        readonly=False,
                                                        default="left")
