# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re
import logging
import requests
import json
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_contingencia = fields.Boolean(string="Es Contingencia")

    @api.constrains("code","is_contingencia")
    def constrains_code(self):
        for record in self:
            if not record.is_contingencia:
                if record.electronic_invoice and record.type == "sale":
                    if record.code and record.invoice_type_code_id in ["07","08"]:
                        if re.match("^B\w{3}$", record.code) and record.tipo_comprobante_a_rectificar == "03":
                            return 
                        if re.match("^F\w{3}$", record.code) and record.tipo_comprobante_a_rectificar == "01":
                            return 
                        raise ValidationError("Error: El campo 'Serie' o 'Comprobante a rectificar' son incorrectos.")
                    
                    if re.match("^B\w{3}$", record.code) and record.invoice_type_code_id == "03":
                        return
                    if re.match("^F\w{3}$", record.code) and record.invoice_type_code_id == "01":
                        return
                    
                    if re.match("^T\w{3}$", record.code) and record.invoice_type_code_id == "09":
                        return
                    
                    raise ValidationError("Error: El campo 'Serie' o el 'Tipo de comprobante' son incorrectos. ")