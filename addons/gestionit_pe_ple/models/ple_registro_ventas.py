import time
import json
import calendar
import io
from datetime import datetime, timedelta
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils

import logging
_logger = logging.getLogger(__name__)

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class ExcelWizard(models.TransientModel):
    _name = "rventas.xlsx.report.wizard"

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
    tipo = fields.Selection(string='Tipo', selection=[(
        'ventas', 'Registro de ventas'), ('mayor', 'Libro Mayor'), ('diario', 'Libro Diario')])

    def print_xlsx(self):
        data = {
            'month': self.months,
            'year': self.years,
            'tipo': self.tipo,
            'company_vat': self.create_uid.company_id.vat,
            'company_name': self.create_uid.company_id.name
        }

        return {
            'type': 'ir_actions_xlsx_download',
            'data': {
                'model': 'rventas.xlsx.report.wizard',
                'options': json.dumps(data, default=date_utils.json_default),
                'output_format': 'xlsx',
                'report_name': 'Excel Report',
            }
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        head = workbook.add_format({'bold': True, 'font_size': 8})
        table_head = workbook.add_format(
            {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 8})

        if data['tipo'] == 'ventas':
            # DOCUMENT HEADER
            sheet.merge_range(
                'A2:D2', 'FORMATO 14.1: REGISTRO DE VENTAS E INGRESOS', head)
            sheet.merge_range('A3:D3', 'PERÍODO:', head)
            sheet.merge_range('A4:D4', 'RUC:', head)
            sheet.merge_range(
                'A5:D5', 'APELLIDOS Y NOMBRES, DENOMINACIÓN O RAZÓN SOCIAL:', head)
            sheet.write('E3', data['month'] + '-' + data['year'])
            sheet.write('E4', data['company_vat'], head)
            sheet.write('E5', data['company_name'], head)

            # TABLE HEADER
            sheet.merge_range(
                'A6:A10', 'NÚMERO CORRELATIVO DEL REGISTRO O CÓDIGO ÚNICO DE LA OPERACIÓN', table_head)
            sheet.merge_range(
                'B6:B10', 'FECHA DE EMISIÓN DEL COMPROBANTE DE PAGO O DOCUMENTO', table_head)
            sheet.merge_range(
                'C6:C10', 'FECHA DE VENCIMIENTO Y/O PAGO', table_head)
            sheet.merge_range(
                'D6:F7', 'COMPROBANTE DE PAGO O DOCUMENTO', table_head)
            sheet.merge_range('D8:D10', 'TIPO', table_head)
            sheet.merge_range('E8:E10', 'N° SERIE', table_head)
            sheet.merge_range('F8:F10', 'NÚMERO', table_head)
            sheet.merge_range('G6:I7', 'INFORMACIÓN DEL CLIENTE', table_head)
            sheet.merge_range('G8:H8', 'DOCUMENTO DE IDENTIDAD', table_head)
            sheet.merge_range('G9:G10', 'TIPO (TABLA 2)', table_head)
            sheet.merge_range('H9:H10', 'NÚMERO', table_head)
            sheet.merge_range(
                'I8:I10', 'APELLIDOS Y NOMBRES, DENOMINACIÓN O RAZÓN SOCIAL', table_head)
            sheet.merge_range(
                'J6:J10', 'VALOR FACTURADO DE LA EXPORTACIÓN', table_head)
            sheet.merge_range(
                'K6:K10', 'BASE IMPONIBLE DE LA OPERACIÓN GRAVADA', table_head)
            sheet.merge_range(
                'L6:M7', 'IMPORTE TOTAL DE LA OPERACIÓN EXONERADA O INAFECTA', table_head)
            sheet.merge_range('L8:L10', 'EXONERADA', table_head)
            sheet.merge_range('M8:M10', 'INAFECTA', table_head)
            sheet.merge_range('N6:N10', 'ISC', table_head)
            sheet.merge_range('O6:O10', 'IGV Y/O IPM', table_head)
            sheet.merge_range(
                'P6:P10', 'OTROS TRIBUTOS Y CARGOS QUE NO FORMAN PARTE DE LA BASE IMPONIBLE', table_head)
            sheet.merge_range(
                'Q6:Q10', 'IMPORTE TOTAL DEL COMPROBANTE DE PAGO', table_head)
            sheet.merge_range('R6:R10', 'TIPO DE CAMBIO', table_head)
            sheet.merge_range(
                'S6:V7', 'REFERENCIA DEL COMPROBANTE DE PAGO O DOCUMENTO ORIGINAL QUE SE MODIFICA', table_head)
            sheet.merge_range('S8:S10', 'FECHA', table_head)
            sheet.merge_range('T8:T10', 'TIPO (TABLA 10)', table_head)
            sheet.merge_range('U8:U10', 'SERIE', table_head)
            sheet.merge_range(
                'V8:V10', 'N° DEL COMPROBANTE DE PAGO O COMPROBANTE', table_head)

            # TABLE CONTENT
            monthRange = calendar.monthrange(
                int(data['year']), int(data['month']))
            items = self.env["account.move"].search([
                ("invoice_date", ">=",
                 data['year'] + "-" + data['month'] + "-01"),
                ("invoice_date", "<=",
                 data['year'] + "-" + data['month'] + "-" + str(monthRange[1]))
            ])

            row = 10
            correlativo = 0
            for item in items:
                sheet.write(row, 0, correlativo)
                sheet.write(row, 1, str(item.invoice_date))
                sheet.write(row, 2, str(item.invoice_date_due))
                sheet.write(row, 3, str(item.invoice_type_code))
                sheet.write(row, 4, item.name[0:4])
                sheet.write(row, 5, item.name[5:13])
                sheet.write(
                    row, 6, item.partner_id.l10n_latam_identification_type_id.id)
                sheet.write(row, 7, item.partner_id.vat)
                sheet.write(row, 8, item.partner_id.name)
                sheet.write(row, 9, 0)
                sheet.write(row, 10, item.total_venta_gravado)
                sheet.write(row, 11, item.total_venta_exonerada)
                sheet.write(row, 12, item.total_venta_inafecto)
                sheet.write(row, 13, 0)
                sheet.write(row, 14, item.amount_igv)
                sheet.write(row, 15, 0)
                sheet.write(row, 16, item.amount_total)
                sheet.write(row, 17, item.tipo_cambio)
                if item.invoice_type_code == '08':
                    sheet.write(row, 18, str(
                        item.reversed_entry_id.invoice_date))
                    sheet.write(row, 19, str(
                        item.reversed_entry_id.invoice_type_code))
                    sheet.write(row, 20, item.reversed_entry_id.name[0:4])
                    sheet.write(row, 21, item.reversed_entry_id.name[5:13])
                if item.invoice_type_code == '09':
                    sheet.write(row, 18, str(
                        item.debit_origin_id.invoice_date))
                    sheet.write(row, 19, str(
                        item.debit_origin_id.invoice_type_code))
                    sheet.write(row, 20, item.debit_origin_id.name[0:4])
                    sheet.write(row, 21, item.debit_origin_id.name[5:13])
                else:
                    sheet.write(row, 18, '-')
                    sheet.write(row, 19, '-')
                    sheet.write(row, 20, '-')
                    sheet.write(row, 21, '-')

                row += 1
                correlativo += 1

        if data['tipo'] == 'mayor':
            # DOCUMENT HEADER
            sheet.merge_range(
                'A1:C1', 'FORMATO 6.1: LIBRO MAYOR', head)
            sheet.merge_range('A2:C2', 'PERÍODO:', head)
            sheet.merge_range('A3:C3', 'RUC:', head)
            sheet.merge_range(
                'A4:C4', 'APELLIDOS Y NOMBRES, DENOMINACIÓN O RAZÓN SOCIAL:', head)
            sheet.write('D2', data['month'] + '-' + data['year'])
            sheet.write('D3', data['company_vat'], head)
            sheet.write('D4', data['company_name'], head)

            # TABLE HEADER
            sheet.merge_range('A5:A6', 'FECHA DE LA OPERACIÓN', table_head)
            sheet.merge_range(
                'B5:B6', 'NÚMERO CORRELATIVO DEL LIBRO DIARIO (2)', table_head)
            sheet.merge_range(
                'C5:C6', 'DESCRIPCIÓN O GLOSA DE LA OPERACIÓN', table_head)
            sheet.merge_range('D5:E5', 'SALDOS Y MOVIMIENTOS', table_head)
            sheet.write('D6', 'DEBE', table_head)
            sheet.write('E6', 'HABER', table_head)

            lines = self.env['account.move.line'].search([("display_type", "not in", [
                                                         "line_section", "line_note"]), ("move_id.state", "=", "posted")])
            accounts = lines.mapped('account_id')

            row = 6
            for account in accounts:
                account_total_debit = 0
                account_total_credit = 0
                filter = lines.filtered(lambda r: r.account_id in account)
                sheet.merge_range(
                    row, 0, row, 1, 'CODIGO DE LA CUENTA CONTABLE:')
                sheet.write(row, 2, str(account.code)+' - '+str(account.name))
                row += 1
                for item in filter:
                    sheet.write(row, 0, str(item.date))
                    sheet.write(row, 1, "")
                    sheet.write(row, 2, item.name)
                    sheet.write(row, 3, item.debit)
                    sheet.write(row, 4, item.credit)

                    account_total_debit += item.debit
                    account_total_credit += item.credit

                    row += 1

                sheet.write(row, 2, 'MOVIMIENTO DEL MES')
                sheet.write(row, 3, account_total_debit)
                sheet.write(row, 4, account_total_credit)
                row += 1

                sheet.write(row, 1, 'SALDO FINAL')
                sheet.write(row, 2, str(account.code)+' - '+str(account.name))
                sheet.write(row, 3, account_total_debit - account_total_credit)
                row += 2

        if data['tipo'] == 'diario':
            # DOCUMENT HEADER
            sheet.merge_range(
                'A1:D1', 'FORMATO 5.1: LIBRO DIARIO', head)
            sheet.merge_range('A2:D2', 'PERÍODO:', head)
            sheet.merge_range('A3:D3', 'RUC:', head)
            sheet.merge_range(
                'A4:D4', 'APELLIDOS Y NOMBRES, DENOMINACIÓN O RAZÓN SOCIAL:', head)
            sheet.write('E2', data['month'] + '-' + data['year'])
            sheet.write('E3', data['company_vat'], head)
            sheet.write('E4', data['company_name'], head)

            # TABLE HEADER
            sheet.merge_range(
                'A5:A8', 'NÚMERO CORRELATIVO DEL ASIENTO O CÓDIGO ÚNICO DE LA OPERACIÓN', table_head)
            sheet.merge_range(
                'B5:B8', 'FECHA DE LA OPERACIÓN', table_head)
            sheet.merge_range(
                'C5:C8', 'GLOSA O DESCRIPCIÓN DE LA OPERACIÓN', table_head)
            sheet.merge_range(
                'D5:F5', 'REFERENCIA DE LA OPERACIÓN', table_head)
            sheet.write(
                'D6:D8', 'CÓDIGO DEL LIBRO O REGISTRO (TABLA 8)', table_head)
            sheet.write('E6:E8', 'NÚMERO CORRELATIVO', table_head)
            sheet.write(
                'F6:F8', 'NÚMERO DEL DOCUMENTO SUSTENTATORIO', table_head)
            sheet.merge_range(
                'G5:H5', 'CUENTA CONTABLE ASOCIADA A LA OPERACIÓN', table_head)
            sheet.write(
                'G6:G8', 'CÓDIGO', table_head)
            sheet.write('H6:H8', 'DENOMINACIÓN', table_head)
            sheet.merge_range(
                'I5:J5', 'MOVIMIENTO', table_head)
            sheet.write(
                'I6:I8', 'DEBE', table_head)
            sheet.write('J6:J8', 'HABER', table_head)

            items = self.env['account.move.line'].search([])

        # items = self.env["account.move.line"].search(
        #     [
        #         ("invoice_date", ">=", self.years + "-" + self.months + "-01"),
        #         (
        #             "invoice_date",
        #             "<=",
        #             self.years + "-" + self.months + "-" + str(monthRange[1]),
        #         ),
        #         ("type", "=", "out_invoice"),
        #         ("state", "not in", ["draft", "cancel"]),
        #     ]
        # )

        # sheet.write('B6', 'From:', cell_format)
        # sheet.merge_range('C6:D6', data['start_date'], txt)
        # sheet.write('F6', 'To:', cell_format)
        # sheet.merge_range('G6:H6', data['end_date'], txt)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
