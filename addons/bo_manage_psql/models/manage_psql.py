from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class BOManagePsql(models.Model):
    _name = 'bo.manage.psql'
    _description = 'Manage PSQL'

    name = fields.Char(string='Nombre')
    type = fields.Selection([
        ('sp', 'Procedimiento almacenado'),
        ('script', 'Script')
    ], string='Tipo')
    script = fields.Text(string='Script')

    def execute_sql(self):
        for s in self:
            _logger.info("bo.manage.sql - execute")
            _logger.info(s.script)
            if s.script:
                self.env.cr.execute(s.script)