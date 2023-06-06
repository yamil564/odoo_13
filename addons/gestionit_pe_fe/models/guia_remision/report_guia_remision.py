from odoo import models, api, fields

import logging
_logger = logging.getLogger(__name__)


class SampleReportPrint(models.AbstractModel):
    _name = 'report.gestionit_pe_fe.print_sample_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # """in this function can access the data returned from the button
        # click function"""
        # model_id = data['model_id']
        # value = []
        # query = """SELECT *
        #                 FROM sale_order as so
        #                 JOIN sale_order_line AS sl ON so.id = sl.order_id
        #                 WHERE sl.id = %s"""
        # value.append(model_id)
        # self._cr.execute(query, value)
        # record = self._cr.dictfetchall()
        # return {
        #     'docs': record,
        #     'date_today': fields.Datetime.now(),
        # }
        return {
            'doc_ids': docids,
            'doc_model': 'gestionit.guia_remision',
            'docs': self.env['gestionit.guia_remision'].browse(docids),
            'report_type': data.get('report_type') if data else '',
        }
