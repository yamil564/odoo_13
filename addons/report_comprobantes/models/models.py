import re
from datetime import datetime
from odoo import models, fields, api, _
import pandas as pd
import numpy as np
import io
from odoo.exceptions import UserError, ValidationError
from io import BytesIO
import json
import os
import logging
_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Can not import xlsxwriter`.')
patron_comprobante = re.compile("[F,B]\w{3}[-]\d{1,8}")


class WizardComprobantesReport(models.TransientModel):
    _name = 'wizard.comprobantes.report'
    tipo_de_seleccion_tiempo = fields.Selection(string="Tipo de Selección",
                                                default="intervalo_fechas",
                                                selection=[('intervalo_fechas', 'Intervalo de Fechas'), ("por_mes", "Por mes")])

    anio_fiscal = fields.Many2one("account.fiscalyear", string="Año Fiscal")
    periodo = fields.Many2one("account.period", string="Periodo")

    fecha_inicio = fields.Date("Fecha de Inicio")
    fecha_fin = fields.Date("Fecha Fin")

    # supplier_id = fields.Many2one("res.partner", "Proveedor")

    @api.onchange("periodo")
    def _onchange_periodo(self):
        for record in self:
            record.fecha_inicio = record.periodo.date_start
            record.fecha_fin = record.periodo.date_stop

    @api.model
    def default_get(self, fields):
        res = super(WizardComprobantesReport, self).default_get(fields)
        anio_fiscal_ids = self.env["account.fiscalyear"].search([])
        if len(anio_fiscal_ids) > 0:
            res.update({"anio_fiscal": anio_fiscal_ids[0].id})

        return res

    def btn_generate_xlsx(self):
        # _logger.info("Button")
        report_obj = self.env.ref(
            "report_comprobantes.comprobantes_report_xlsx")
        # _logger.info(dir(report_obj))
        return report_obj.report_action(self, data={"fecha_inicio": self.fecha_inicio, "fecha_fin": self.fecha_fin})


class ComprobantesXlsx(models.AbstractModel):
    _name = 'report.report_comprobantes.comprobantes_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def create_xlsx_report(self, docids, data):
        # _logger.info("DATA CREATE")
        # _logger.info(data)
        objs = self._get_objs_for_report(docids, data)
        file_data = BytesIO()
        #workbook = xlsxwriter.Workbook(file_data, self.get_workbook_options())
        workbook = pd.ExcelWriter(file_data, engine='xlsxwriter')
        self.generate_xlsx_report(workbook, data, objs)
        # workbook.close()
        workbook.save()
        file_data.seek(0)
        return file_data.read(), 'xlsx'

    def generate_xlsx_report(self, workbook, data, records):
        fecha_inicio = data.get("fecha_inicio", False)
        fecha_fin = data.get("fecha_fin", False)
        # 01 - Facturas
        # 03 - Boletas
        # 07 - Notas de Crédito
        # 08 - Notas de Débito
        domain = [['journal_id.type', '=', 'sale'],
                  ['state', 'in', ['posted']],
                  ['journal_id.invoice_type_code_id', 'in', ['00', '01', '03', '07', '08']], ]
        if fecha_fin:
            domain.append(["invoice_date", "<=", fecha_fin])
        if fecha_inicio:
            domain.append(["invoice_date", ">=", fecha_inicio])

        _logger.info(domain)
        comprobante_ids = self.env["account.move"].search(domain)
        _logger.info(comprobante_ids)

        def get_serie_correlativo(numero):
            numero_comp = numero.strip()
            try:
                # if patron_comprobante.match(numero_comp):
                serie, correlativo = numero_comp.split("-")
                correlativo = int(correlativo)
            except Exception as e:
                raise UserError(
                    "La serie o Correlativo del comprobante {} no es correcto".format(numero))

            return (serie, correlativo)

        def row_comp(comp):
            numero = comp.name
            serie, correlativo = get_serie_correlativo(numero)
            tipo_comp = comp.journal_id.invoice_type_code_id if comp.journal_id else ""
            observacion = ""
            if comp.reversed_entry_id:
                numero_rec = comp.reversed_entry_id.name
                serie_rec, correlativo_rec = get_serie_correlativo(numero_rec)
                tipo_comp_rec = comp.reversed_entry_id.journal_id.invoice_type_code_id
                fecha_emision_rec = comp.reversed_entry_id.invoice_date
            elif comp.debit_origin_id:
                numero_rec = comp.debit_origin_id.name
                serie_rec, correlativo_rec = get_serie_correlativo(numero_rec)
                tipo_comp_rec = comp.debit_origin_id.journal_id.invoice_type_code_id
                fecha_emision_rec = comp.debit_origin_id.invoice_date
            else:
                numero_rec, serie_rec, correlativo_rec, tipo_comp_rec, fecha_emision_rec = "", "", "", "", ""

            signo = -1 if tipo_comp == '07' else 1
            anular = 0 if comp.estado_comprobante_electronico == '2_ANULADO' else 1

            row = {
                "Estado": comp.state,
                "Fecha de emisión": comp.invoice_date,
                "Fecha de Vencimiento": comp.invoice_date_due,
                'Tipo de comprobante': tipo_comp,
                "Número Comp.": numero,
                "Serie Comp.": serie,
                "Correlativo Comp.": correlativo,
                "Fecha de emisión Comp. Rec.": fecha_emision_rec,
                'Tipo de comprobante a Rec.': tipo_comp_rec,
                "Comprobante a Rectificar": numero_rec,
                "Serie Comp. Rec.": serie_rec,
                "Correlativo Comp. Rec.": correlativo_rec,
                'Documento de origen': comp.invoice_origin if comp.invoice_origin else "",
                'Código de Empresa': comp.partner_id.ref if comp.partner_id else "",
                'Empresa': comp.partner_id.name if comp.partner_id else "",
                'Tipo de documento de identidad': comp.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code if comp.partner_id else "",
                'Número de documento': comp.partner_id.vat if comp.partner_id else "",
                'Dirección': comp.partner_id.street if comp.partner_id else "",
                'Descuento Global': round(comp.descuento_global, 2),
                "Moneda":comp.currency_id.name,
                "T/C":round(1/comp.company_id.currency_id._convert(1,comp.currency_id,comp.company_id,comp.invoice_date,False),6),
                'Monto Gravado': round(comp.total_venta_gravado, 2)*signo*anular,
                'IGV 18% Venta': round(comp.amount_igv, 2)*signo*anular,
                'Monto Inafecto': round(comp.total_venta_inafecto, 2)*signo*anular,
                'Monto Exonerado': round(comp.total_venta_exonerada, 2)*signo*anular,
                'Monto Gratuito': round(comp.total_venta_gratuito, 2)*signo*anular,
                'Total Descuentos': round(comp.total_descuentos, 2)*signo*anular,
                'Monto total': round(comp.amount_total, 2)*signo*anular,
                'Estado comprobante electrónico': comp.estado_comprobante_electronico,
                'Anulación de comprobante': comp.anulacion_comprobante,
                'Vendedor': comp.sudo().user_id.name if comp.sudo().user_id else "",
                'Observacion': observacion
            }

            # for x in comp.tax_line_ids.sorted(lambda r: r.sequence):
            #     row.update({x.name: round(x.amount_total, 2)})
            return row

        comps = [
            row_comp(comp)
            for comp in comprobante_ids
        ]
        _logger.info(comps)
        df_states = pd.DataFrame(comps, columns=["Estado",
                                                 "Fecha de emisión",
                                                 "Fecha de Vencimiento",
                                                 "Tipo de comprobante",
                                                 "Número Comp.",
                                                 "Serie Comp.",
                                                 "Correlativo Comp.",
                                                 "Fecha de emisión Comp. Rec.",
                                                 'Tipo de comprobante a Rec.',
                                                 'Comprobante a Rectificar',
                                                 "Serie Comp. Rec.",
                                                 "Correlativo Comp. Rec.",
                                                 "Documento de origen",
                                                 "Empresa",
                                                 "Código de Empresa",
                                                 "Tipo de documento de identidad",
                                                 "Número de documento",
                                                 'Dirección',
                                                 "Moneda",
                                                 "T/C",
                                                 'Descuento Global',
                                                 'Monto Gravado',
                                                 'Monto Inafecto',
                                                 'Monto Exonerado',
                                                 'Monto Gratuito',
                                                 'Total Descuentos',
                                                 'IGV 18% Venta',
                                                 'Monto total',
                                                 'Estado comprobante electrónico',
                                                 'Anulación de comprobante',
                                                 'Vendedor',
                                                 "Observacion"])

        ####################################################
        """
        df_states = df_states.sort_values(by=["Serie Comp.","Número Comp.","Correlativo Comp."])
        cnt = 1
        tam = len(df_states)
        serie_actual = df_states.loc[0]["Serie Comp."]#F001
        correlativo_actual = df_states.loc[0]["Correlativo Comp."]#303
        """
        def completar_correlativos(df, tipo_comp):
            df = df.sort_values(by=["Correlativo Comp."])
            cnt = 1
            tam = len(df)
            serie_actual = df.iloc[0]["Serie Comp."]  # B001
            correlativo_actual = df.iloc[0]["Correlativo Comp."]  # 5
            while cnt < tam:
                correlativo_actual = correlativo_actual+1
                number = serie_actual+"-"+str(correlativo_actual).zfill(8)
                if correlativo_actual != df.iloc[cnt]["Correlativo Comp."]:
                    row_d = {"Estado": "",
                             "Fecha de emisión": "",
                             "Fecha de Vencimiento": "",
                             "Tipo de comprobante": tipo_comp,
                             "Número Comp.": number,
                             "Serie Comp.": serie_actual,
                             "Correlativo Comp.": correlativo_actual,
                             "Fecha de emisión Comp. Rec.": "",
                             'Tipo de comprobante a Rec.': "",
                             'Comprobante a Rectificar': "",
                             "Serie Comp. Rec.": "",
                             "Correlativo Comp. Rec.": "",
                             "Documento de origen": "",
                             "Empresa": "",
                             "Código de Empresa": "",
                             "Tipo de documento de identidad": "",
                             "Número de documento": "",
                             'Dirección': "",
                             "Moneda":"",
                             "T/C":"",
                             'Descuento Global': "",
                             'Monto Gravado': "",
                             'Monto Inafecto': "",
                             'Monto Exonerado': "",
                             'Monto Gratuito': "",
                             'Total Descuentos': "",
                             'IGV 18% Venta': "",
                             'Monto total': "",
                             'Estado comprobante electrónico': "",
                             'Anulación de comprobante': "",
                             'Vendedor': ""}
                    inv = self.env["account.move"].search(
                        [["name", "=", number]])
                    if len(inv) == 0:
                        row_d.update({"Observacion": "No Existe"})
                        df = df.append(row_d, ignore_index=True)
                    else:
                        row_d.update({"Observacion": "Este registro se encuentra en esta fecha {}".format(
                            inv[0].invoice_date)})
                        df = df.append(row_d, ignore_index=True)

                    df = pd.DataFrame(df.values, columns=["Estado",
                                                          "Fecha de emisión",
                                                          "Fecha de Vencimiento",
                                                          "Tipo de comprobante",
                                                          "Número Comp.",
                                                          "Serie Comp.",
                                                          "Correlativo Comp.",
                                                          "Fecha de emisión Comp. Rec.",
                                                          'Tipo de comprobante a Rec.',
                                                          'Comprobante a Rectificar',
                                                          "Serie Comp. Rec.",
                                                          "Correlativo Comp. Rec.",
                                                          "Documento de origen",
                                                          "Empresa",
                                                          "Código de Empresa",
                                                          "Tipo de documento de identidad",
                                                          "Número de documento",
                                                          'Dirección',
                                                          "Moneda",
                                                          "T/C",
                                                          'Descuento Global',
                                                          'Monto Gravado',
                                                          'Monto Inafecto',
                                                          'Monto Exonerado',
                                                          'Monto Gratuito',
                                                          'Total Descuentos',
                                                          'IGV 18% Venta',
                                                          'Monto total',
                                                          'Estado comprobante electrónico',
                                                          'Anulación de comprobante',
                                                          'Vendedor',
                                                          'Observacion'])
                    df = df.sort_values(by=["Correlativo Comp."])
                tam = len(df)
                cnt = cnt+1
            return df

        group_df = df_states.groupby(["Serie Comp.", "Tipo de comprobante"])
        series = list(group_df.groups.keys())
        df = pd.DataFrame()
        dfs = []
        for s in series:
            df_gr = group_df.get_group(s)
            df_cc = completar_correlativos(df_gr, s[1])
            dfs.append(df_cc)
        df = pd.concat(dfs)

        df = pd.DataFrame(df.values, columns=["Estado",
                                              "Fecha de emisión",
                                              "Fecha de Vencimiento",
                                              "Tipo de comprobante",
                                              "Número Comp.",
                                              "Serie Comp.",
                                              "Correlativo Comp.",
                                              "Fecha de emisión Comp. Rec.",
                                              'Tipo de comprobante a Rec.',
                                              'Comprobante a Rectificar',
                                              "Serie Comp. Rec.",
                                              "Correlativo Comp. Rec.",
                                              "Documento de origen",
                                              "Empresa",
                                              "Código de Empresa",
                                              "Tipo de documento de identidad",
                                              "Número de documento",
                                              'Dirección',
                                              "Moneda",
                                              "T/C",
                                              'Descuento Global',
                                              'Monto Gravado',
                                              'Monto Inafecto',
                                              'Monto Exonerado',
                                              'Monto Gratuito',
                                              'Total Descuentos',
                                              'IGV 18% Venta',
                                              'Monto total',
                                              'Estado comprobante electrónico',
                                              'Anulación de comprobante',
                                              'Vendedor',
                                              'Observacion'])
        df_states = df.sort_values(
            by=["Tipo de comprobante", "Serie Comp.", "Correlativo Comp."])
        """
        while cnt<tam:
            
            correlativo_actual = correlativo_actual+1
            number = serie_actual+"-"+str(correlativo_actual).zfill(8) 
            os.system("echo '{}\n{}\n{}'".format(cnt,tam,number))
            try:
                os.system("echo '{}'".format("-----------------")) 
                os.system("echo '{}\n{}\n{}'".format(correlativo_actual,df_states.loc[cnt]["Correlativo Comp."],df_states.loc[cnt]["Número Comp."]))
                os.system("echo '{}'".format("-----------------")) 
                if serie_actual == df_states.loc[cnt]["Serie Comp."] :
                    
                    if  correlativo_actual != df_states.loc[cnt]["Correlativo Comp."]:
                        
                        inv = self.env["account.move"].search([["move_name", "=", number]])
                        if len(inv) == 0:
                            row_d = {"Estado":"",
                                        "Fecha de emisión":"",
                                        "Tipo de comprobante":"",
                                        "Número Comp.":number,
                                        "Serie Comp.":serie_actual,
                                        "Correlativo Comp.":correlativo_actual,
                                        "Fecha de emisión Comp. Rec.":"",
                                        'Tipo de comprobante a Rec.':"",
                                        'Comprobante a Rectificar':"",
                                        "Serie Comp. Rec.":"",
                                        "Correlativo Comp. Rec.":"",
                                        "Documento de origen":"",
                                        "Empresa":"",
                                        "Tipo de documento de identidad":"",
                                        "Número de documento":"",
                                        'Dirección':"",
                                        'Descuento Global':"",
                                        'Monto Gravado':"",
                                        'Monto Inafecto':"",
                                        'Monto Exonerado':"",
                                        'Monto Gratuito':"",
                                        'Total Descuentos':"",
                                        'IGV 18% Venta':"",
                                        'Monto total':"",
                                        'Estado comprobante electrónico':"",
                                        'Anulación de comprobante':"",
                                        'Vendedor':"",
                                        'Observacion':"No existe"}
                            #df_states = pd.DataFrame(np.insert(df_states.values, cnt, values=row_d, axis=0))
                            df_states = df_states.append(row_d,ignore_index=True)    
                        else:
                            row_d = {"Estado":"",
                                    "Fecha de emisión":"",
                                    "Tipo de comprobante":"",
                                    "Número Comp.":number,
                                    "Serie Comp.":serie_actual,
                                    "Correlativo Comp.":correlativo_actual,
                                    "Fecha de emisión Comp. Rec.":"",
                                    'Tipo de comprobante a Rec.':"",
                                    'Comprobante a Rectificar':"",
                                    "Serie Comp. Rec.":"",
                                    "Correlativo Comp. Rec.":"",
                                    "Documento de origen":"",
                                    "Empresa":"",
                                    "Tipo de documento de identidad":"",
                                    "Número de documento":"",
                                    'Dirección':"",
                                    'Descuento Global':"",
                                    'Monto Gravado':"",
                                    'Monto Inafecto':"",
                                    'Monto Exonerado':"",
                                    'Monto Gratuito':"",
                                    'Total Descuentos':"",
                                    'IGV 18% Venta':"",
                                    'Monto total':"",
                                    'Estado comprobante electrónico':"",
                                    'Anulación de comprobante':"",
                                    'Vendedor':"",
                                    'Observacion':"Este registro se encuentra en esta fecha {}".format(inv[0].invoice_date)}
                            #df_states = pd.DataFrame(np.insert(df_states.values, cnt, values=row_d, axis=0))
                            df_states = df_states.append(row_d,ignore_index=True)
                        
                        df_states = df_states.sort_values(by=["Serie Comp.","Número Comp.","Correlativo Comp."])
                        df_states = pd.DataFrame(df_states.values,columns=["Estado",
                                                        "Fecha de emisión",
                                                        "Tipo de comprobante",
                                                        "Número Comp.",
                                                        "Serie Comp.",
                                                        "Correlativo Comp.",
                                                        "Fecha de emisión Comp. Rec.",
                                                        'Tipo de comprobante a Rec.',
                                                        'Comprobante a Rectificar',
                                                        "Serie Comp. Rec.",
                                                        "Correlativo Comp. Rec.",
                                                        "Documento de origen",
                                                        "Empresa",
                                                        "Tipo de documento de identidad",
                                                        "Número de documento",
                                                        'Dirección',
                                                        'Descuento Global',
                                                        'Monto Gravado',
                                                        'Monto Inafecto',
                                                        'Monto Exonerado',
                                                        'Monto Gratuito',
                                                        'Total Descuentos',
                                                        'IGV 18% Venta',
                                                        'Monto total',
                                                        'Estado comprobante electrónico',
                                                        'Anulación de comprobante',
                                                        'Vendedor',
                                                        'Observacion'])
                    
                else:
                    serie_actual = df_states.loc[cnt]["Serie Comp."]
                    correlativo_actual = df_states.loc[cnt]["Correlativo Comp."]

            except Exception as e:
                print(e)
                pass

            cnt = cnt + 1
            tam = len(df_states)
        """

        # df_states.drop(df_states.tail(1).index,inplace=True) # drop last n rows
        ####################################################
        records = []
        for row in df_states.to_dict(orient="records"):
            serie = row.get("Serie Comp.", "")
            numero = str(row.get("Correlativo Comp.", "")).zfill(7)
            if row["Observacion"] or row["Estado comprobante electrónico"] != "1_ACEPTADO" and patron_comprobante.match(serie+"-"+numero):

                records.append({
                    "fecha": "",
                    "fechavcto": "",
                    "tipo": row.get("Tipo de comprobante", ""),
                    "serie": serie,
                    "numero": numero,
                    "ruc": "",
                    "nombre": "",
                    "valvtae": "",
                    "valvtai": "",
                    "igv": "",
                    "total": "",
                    "fecharef": "",
                    "tiporef": "",
                    "serieref": "",
                    "numeroref": "",
                    "codigo": "",
                    "obs": row["Observacion"]
                })
            else:
                fecha = row["Fecha de emisión"].strftime("%d-%m-%y") if row["Fecha de emisión"] else ""
                fechavcto = row["Fecha de Vencimiento"].strftime("%d-%m-%y") if row["Fecha de Vencimiento"] else ""
                tipo = row.get("Tipo de comprobante", "") or ""
                serie = row.get("Serie Comp.", "") or ""
                numero = str(row.get("Correlativo Comp.", "")).zfill(7) or ""
                ruc = row.get("Número de documento", "") or ""
                nombre = row.get("Empresa", "") or ""
                valvtae = "0"
                valvtai = "0"
                valvtaa = str(round(row.get("Monto Gravado", 0), 2)
                              * (-1 if tipo == '07' else 1))
                igv = str(round(row.get("IGV 18% Venta", 0), 2)
                          * (-1 if tipo == '07' else 1))
                total = str(round(row.get("Monto total", 0), 2)
                            * (-1 if tipo == '07' else 1))
                fecharef = row.get("Fecha de emisión Comp. Rec.", "").strftime("%d-%m-%Y") if row.get("Fecha de emisión Comp. Rec.") else ""
                tiporef = row.get("Tipo de comprobante a Rec.", "") or ""
                serieref = row.get("Serie Comp. Rec.", "") or ""
                numeroref = str(row.get("Correlativo Comp. Rec.", "")).zfill(
                    7) if row.get("Correlativo Comp. Rec.", "") else ""
                codigo = str(row.get("Código de Empresa", "")) or ""
                records.append({
                    "fecha": fecha,
                    "fechavcto": fechavcto,
                    "tipo": tipo,
                    "serie": serie,
                    "numero": numero,
                    "ruc": ruc,
                    "nombre": nombre,
                    "valvtae": valvtae,
                    "valvtai": valvtai,
                    "valvtaa": valvtaa,
                    "igv": igv,
                    "total": total,
                    "fecharef": fecharef,
                    "tiporef": tiporef,
                    "serieref": serieref,
                    "numeroref": numeroref,
                    "codigo": codigo,
                    "obs": ""
                })

        df_states_0 = pd.DataFrame(records, columns=["fecha",
                                                     "fechavcto",
                                                     "tipo",
                                                     "serie",
                                                     "numero",
                                                     "ruc",
                                                     "nombre",
                                                     "valvtae",
                                                     "valvtai",
                                                     "valvtaa",
                                                     "igv",
                                                     "total",
                                                     "fecharef",
                                                     "tiporef",
                                                     "serieref",
                                                     "numeroref",
                                                     "codigo"])

        df_states_1 = pd.DataFrame(records, columns=["fecha",
                                                     "fechavcto",
                                                     "tipo",
                                                     "serie",
                                                     "numero",
                                                     "ruc",
                                                     "nombre",
                                                     "valvtae",
                                                     "valvtai",
                                                     "valvtaa",
                                                     "igv",
                                                     "total",
                                                     "fecharef",
                                                     "tiporef",
                                                     "serieref",
                                                     "numeroref",
                                                     "codigo",
                                                     "obs"])

        # df_states_0.to_excel(workbook, sheet_name='Formato')
        # df_states_1.to_excel(workbook, sheet_name='Formato con Obs.')
        df_states.to_excel(workbook, sheet_name='Comprobantes')
