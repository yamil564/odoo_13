from odoo import _, api, fields, models

import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    notes_journal = fields.Many2one('account.journal', 'Diario para Notas')
