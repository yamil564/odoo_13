from odoo import _, api, fields, models

import logging
_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    notes_journal = fields.Many2one(related='company_id.notes_journal', readonly=False)
