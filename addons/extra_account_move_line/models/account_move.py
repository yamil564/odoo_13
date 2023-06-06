from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError
import logging
_logger=logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'


    def action_account_move_line_views(self):
        if self.line_ids:

            return {
                "name":"Apuntes Contables",
                "type": "ir.actions.act_window",
                "res_model": "account.move.line",
                "view_mode": "tree,form",
                "view_id": False,
                "domain":[('id','in',
                    self.line_ids.filtered(lambda t:t.display_type not in ['line_section']).mapped('id') or [])],
                "context":{"journal_id":self.journal_id.id}
            }

