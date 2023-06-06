from odoo import models, api, _
from odoo.exceptions import UserError


class WizardAccountAnalyticDistribution(models.TransientModel):
    _name = "wizard.account.analytic.distribution"
    _description = "Recalcular Distribución Analítica"


    def recalculate_analytic_distribution(self):
        if self._context.get('active_ids', []):
            if self._context.get('active_model') == 'account.move':
                domain = [('id', 'in', self._context.get('active_ids', [])),
                ('state', '=','posted'),
                ('type','not in',['out_invoice','out_refund'])]
            
            moves = self.env['account.move'].search(domain)
            if not moves:
                raise UserError(_('No se han encontrado asientos contables validados para el proceso de recalculo.'))
            
            moves.update_analytic_distribution()
            
            return {'type': 'ir.actions.act_window_close'}