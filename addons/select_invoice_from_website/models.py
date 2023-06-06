from odoo import models,fields,api
import re
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    invoice_type_code = fields.Selection(selection=[("01","Factura Electrónica"),("03","Boleta Electrónica")],default="03")
    

class ResPartner(models.Model):
    _inherit = "res.partner"

    allow_receive_mails = fields.Boolean(string="Permite recibir correos de ofertas")

    @api.model
    def check_number_doc(self,doc,idt):
        type = self.env['l10n_latam.identification.type'].sudo().search([('id','=', int(idt))], limit=1)
        patron_dni = re.compile("\d{8}$")
        if type.exists():
            #6 - Tipo de documento RUC
            if type.l10n_pe_vat_code == "6":
                # _logger.info(self._check_valid_ruc(doc))
                return self._check_valid_ruc(doc)
            #6 - Tipo de documento DNI
            elif type.l10n_pe_vat_code == "1":
                if not patron_dni.match(doc):
                    return False
        return True


class IdentificationType(models.Model):
    _inherit = "l10n_latam.identification.type"

    available_in_website = fields.Boolean("Disponible en Sitio Web",default=True)