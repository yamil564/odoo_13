from odoo import models,api,fields
from odoo.addons.gestionit_pe_fe.models.parameters.catalogs import tdc
import logging
logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _selection_invoice_type(self):
        tdc_ext = tdc
        flag = False
        for l in tdc_ext:
            if l[0] == "100":
                flag = True
        if not flag:
            tdc_ext.append(("100", "Notas de Venta"))
        return tdc_ext
