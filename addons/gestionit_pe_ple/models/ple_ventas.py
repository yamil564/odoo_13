from odoo import fields, models, api
from datetime import datetime, timedelta
from io import BytesIO
import calendar
import base64

import logging
_logger = logging.getLogger(__name__)


# REGISTRO DE VENTAS
class PrintReportTextVentas(models.TransientModel):
    _name = "print.ventas.reporte.contabilidad"

    def _list_anios(self):
        d = datetime.now()

        list = []

        i = 0
        while i < 3:
            anios = timedelta(days=365 * i)
            reference_date = d - anios
            list.append((str(reference_date.year), str(reference_date.year)))
            i += 1

        return list

    def get_month(self):
        d = datetime.now()
        return "{:02d}".format(d.month)

    def get_year(self):
        d = datetime.now()
        return "{:04d}".format(d.year)

    invoice_summary_file = fields.Binary("Reporte de Ventas")
    file_name = fields.Char("File Name")
    invoice_report_printed = fields.Boolean("Reporte de Ventas")
    years = fields.Selection(
        string="Año", selection=_list_anios, default=get_year)
    months = fields.Selection(
        string="Mes",
        selection=[
            ("01", "Enero"),
            ("02", "Febrero"),
            ("03", "Marzo"),
            ("04", "Abril"),
            ("05", "Mayo"),
            ("06", "Junio"),
            ("07", "Julio"),
            ("08", "Agosto"),
            ("09", "Septiembre"),
            ("10", "Octubre"),
            ("11", "Noviembre"),
            ("12", "Diciembre"),
        ],
        default=get_month,
    )

    # @api.multi
    def generaReporte(self):
        monthRange = calendar.monthrange(int(self.years), int(self.months))

        invoice_objs = self.env["account.move"].search(
            [
                ("invoice_date", ">=", self.years + "-" + self.months + "-01"),
                (
                    "invoice_date",
                    "<=",
                    self.years + "-" + self.months + "-" + str(monthRange[1]),
                ),
                ("type", "=", "out_invoice"),
                ("state", "not in", ["draft", "cancel"]),
            ]
        )

        for wizard in self:
            fp = BytesIO()
            cuo = 1
            for line in invoice_objs:
                di = datetime.strptime(str(line.invoice_date), "%Y-%m-%d")
                di = str(di.date()).split("-")
                fdi = "/".join(reversed(di))

                if line.invoice_date_due is False:
                    dd = line.invoice_date
                else:
                    dd = line.invoice_date_due
                # Por mientras
                dd = ""

                if line.partner_id.parent_id:
                    doccode = line.partner_id.parent_id.l10n_latam_identification_type_id.l10n_pe_vat_code
                    vatcode = line.partner_id.parent_id.vat
                    docname = line.partner_id.parent_id.name
                else:
                    doccode = line.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code
                    vatcode = line.partner_id.vat
                    docname = line.partner_id.name
                ac = "M" + str(cuo).zfill(3)

                ventas = (
                    self.years
                    + self.months
                    + "00"
                    + "|"
                    + str(cuo)
                    + "|"
                    + str(ac)
                    + "|"
                    + str(fdi)
                    + "|"
                    + str(dd)
                    + "|"
                    + str(line.journal_id.invoice_type_code_id)
                    + "|"
                    + str(line.name.split("-")[0])
                    + "|"
                    + str(line.name.split("-")[1])
                    + "|"
                    + ""
                    + "|"
                    + str(doccode)
                    + "|"
                    + str(vatcode)
                    + "|"
                    + str(docname)
                    + "|"
                    + ""
                    + "|"
                    + str(line.amount_untaxed)
                    + "|"
                    + ""
                    + "|"
                    + str(line.amount_tax)
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + str(line.amount_total)
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + ""
                    + "|"
                    + "1"
                    + "|"
                    + "1"
                    + "|"
                    + ""
                    + "\n"
                )

                fp.write(ventas.encode("utf-8"))
                cuo = cuo + 1

            file_text_name = (
                "LE"
                + self.create_uid.company_id.vat
                + self.years
                + self.months
                + "0014010000"
                + "1111.txt"
            )
            excel_file = base64.encodestring(fp.getvalue())
            wizard.invoice_summary_file = excel_file
            # wizard.file_name = "Ventas.txt"
            wizard.file_name = file_text_name
            wizard.invoice_report_printed = True
            fp.close()

            return {
                "view_mode": "form",
                "res_id": wizard.id,
                "res_model": "print.ventas.reporte.contabilidad",
                "view_type": "form",
                "type": "ir.actions.act_window",
                "context": wizard.env.context,
                "target": "new",
            }
