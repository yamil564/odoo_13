from odoo import models,api,fields
import logging
logger = logging.getLogger(__name__)

class Import(models.TransientModel):
    _inherit = "base_import.import"

    def do(self, fields, columns, options, dryrun):
        self = self.with_context({'dryrun':dryrun})
        res = super(Import, self).do(fields, columns, options, dryrun)
        return res
