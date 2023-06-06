import odoo
import requests
from odoo import api, models, fields
from datetime import date, datetime, timedelta
import json
from pytz import timezone
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

CURRENCY_TYPES = {
    "commercial": "Comercial",
    "sale": "Venta",
    "purchase": "Compra"
}


class ResCurrency(models.Model):
    _inherit = "res.currency"
    _rec_name = "display_name"

    # def _compute_name(self):
    #     for record in self:
    #         record.display_name = record.name + (" [{}] ".format(CURRENCY_TYPES.get(record.type)) if CURRENCY_TYPES.get(record.type) else "")

    # display_name = fields.Char("Nombre",compute=_compute_name,store=True)

    dayli_update_sbs_usd = fields.Boolean("Actualización diaria automática",default=True)

    def name_get(self):
        result = []
        for record in self:
            if record.name and record.type:
                result.append((record.id, "{} [{}] T/C: {:.3f}".format(
                    record.name, CURRENCY_TYPES.get(record.type), 1/record.rate)))
            else:
                result.append((record.id, record.name))
        return result

    type = fields.Selection(selection=[('commercial', 'Comercial'), (
        'sale', 'Venta'), ('purchase', 'Compra')], default="commercial")

    _sql_constraints = [
        ('unique_name', 'FALSE', ''),
        ('rounding_gt_zero', 'CHECK (rounding>0)',
         'The rounding factor must be greater than 0!')
    ]

    def action_get(self):
        view_id = self.sudo().env.ref("gestionit_pe_tipocambio.view_form_rate_simple").id
        tz = self.env.user.tz or "America/Lima"
        today = datetime.now(tz=timezone(tz))
        action = {
            "name": "Tipo de Cambio {} [{}]".format(self.name, CURRENCY_TYPES.get(self.type)),
            "type": "ir.actions.act_window",
            "res_model": "res.currency.rate",
            "views": [[view_id, "form"]],
            "view_mode": "form",
            "target": "new",
        }
        rate = self.env["res.currency.rate"].sudo().search([("company_id", "=", self.env.company.id), (
            "type", "=", self.type), ("currency_id", "=", self.id), ("name", "=", today.strftime("%Y-%m-%d"))], limit=1)

        if rate.exists():
            action.update({"res_id": rate.id})
        else:
            action.update({"context": {"default_currency_id": self.id,
                                       "default_name": today.strftime("%Y-%m-%d"),
                                       "company_id": self.env.company.id}})
        return action


class Tipocambio(models.Model):
    _inherit = "res.currency.rate"
    type = fields.Selection(selection=[('commercial', 'Comercial'), (
        'sale', 'Venta'), ('purchase', 'Compra')], related="currency_id.type")

    factor = fields.Float("T/C", default=1)
    currency_name = fields.Char("Moneda", related="currency_id.name")

    @api.onchange("rate")
    def _onchange_rate(self):
        if self.rate > 0:
            self.factor = 1/self.rate

    @api.onchange("factor")
    def _onchange_rate(self):
        if self.factor > 0:
            self.rate = 1/self.factor
        else:
            self.factor = 1
            self.rate = 1

    def api_migo_get_token(self):
        company = self.env.company
        token = company.api_migo_token
        return token

    def api_migo_get_endpoint(self):
        company = self.env.company
        endpoint = company.api_migo_endpoint
        if not endpoint:
            endpoint = "https://api.migo.pe/api/v1/"
        endpoint = endpoint.strip()
        endpoint = endpoint if endpoint[-1] == "/" else "{}/".format(endpoint)
        return endpoint

    @api.model
    def api_migo_usd_pen_exchange_latest(self):
        token = self.api_migo_get_token()
        endpoint = self.api_migo_get_endpoint()
        data = {"token": token}

        try:
            headers = {
                'Content-Type': 'application/json'
            }
            result = requests.request(
                "POST", "{}exchange/latest".format(endpoint), headers=headers, data=json.dumps(data))
            if result.status_code == 200:
                return result.json()
            else:
                raise Exception(
                    "No se ha encontrado el último tipo de cambio disponible o el servicio no esta disponible.")
        except Exception as e:
            raise Exception(e)

    @api.model
    def api_migo_usd_pen_exchange_date(self, date):
        token = self.api_migo_get_token()
        endpoint = self.api_migo_get_endpoint()
        data = {"token": token, "fecha": date}
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            result = requests.request(
                "POST", "{}exchange/date".format(endpoint), headers=headers, data=json.dumps(data))
            _logger.info(result.text)
            if result.status_code == 200:
                return result.json()
            else:
                raise Exception(
                    "No se ha encontrado el tipo de cambio solicitado para la fecha {}.".format(today_format))
        except Exception as e:
            raise Exception(e)

    def action_update_rate_commercial_pen_usd(self):
        if not self.name:
            raise UserError("La fecha del T/C es obligatoria.")

        if not self.currency_id:
            raise UserError("La moneda es obligatoria.")

        if not(self.type == "commercial" and self.currency_id.name == "USD"):
            raise UserError(
                "Esta opción solo esta disponible para la moneda USD de tipo Venta.")

        if not self.company_id:
            raise UserError("La compañia del tipo de cambio es obligatoria.")

        try:
            res = self.api_migo_usd_pen_exchange_date(
                self.name.strftime("%Y-%m-%d"))
        except Exception as e:
            today = datetime.now(tz=timezone(
                "America/Lima")).strftime("%Y-%m-%d")
            if today == self.name.strftime("%Y-%m-%d"):
                try:
                    res = self.api_migo_usd_pen_exchange_latest()
                except Exception as e:
                    raise UserError(e)

        rate_sale = float(res.get("precio_venta", False))
        rate_compra = float(res.get("precio_compra", False))
        rate_commercial = (rate_sale + rate_compra)/2
        rate = 1/rate_commercial if rate_commercial != 0.0 else 0.0
        self.rate = rate
        self.factor = 1/rate
        self.env.user.notify_success(
            'El T/C PEN -> USD: {}'.format(self.factor), "T/C comercial actualizado")

    def action_update_rate_sale_pen_usd(self):
        if not self.name:
            raise UserError("La fecha del T/C es obligatoria.")

        if not self.currency_id:
            raise UserError("La moneda es obligatoria.")

        if not(self.type == "sale" and self.currency_id.name == "USD"):
            raise UserError(
                "Esta opción solo esta disponible para la moneda USD de tipo Venta.")

        if not self.company_id:
            raise UserError("La compañia del tipo de cambio es obligatoria.")

        try:
            res = self.api_migo_usd_pen_exchange_date(
                self.name.strftime("%Y-%m-%d"))
            _logger.info(res)
        except Exception as e:
            today = datetime.now(tz=timezone(
                "America/Lima")).strftime("%Y-%m-%d")
            if today == self.name.strftime("%Y-%m-%d"):
                try:
                    res = self.api_migo_usd_pen_exchange_latest()
                except Exception as e:
                    raise UserError(e)

        rate = float(res.get("precio_venta", False))
        rate = 1/rate if rate != 0.0 else 0.0
        self.rate = rate
        self.factor = 1/rate
        self.env.user.notify_success(
            'El T/C PEN -> USD: {}'.format(self.factor), "T/C de compra actualizado")

    def action_update_rate_sale_pen_usd_recursive(self, date):
        if not self.name:
            raise UserError("La fecha del T/C es obligatoria.")

        if not self.currency_id:
            raise UserError("La moneda es obligatoria.")

        if not(self.type == "sale" and self.currency_id.name == "USD"):
            raise UserError(
                "Esta opción solo esta disponible para la moneda USD de tipo Venta.")

        if not self.company_id:
            raise UserError("La compañia del tipo de cambio es obligatoria.")

        try:
            res = self.api_migo_usd_pen_exchange_date(
                date.strftime("%Y-%m-%d"))
            _logger.info(res)
        except Exception as e:
            return self.action_update_rate_sale_pen_usd_recursive(date-timedelta(days=1))

        rate = float(res.get("precio_venta", False))
        rate = 1/rate if rate != 0.0 else 0.0
        self.rate = rate
        self.factor = 1/rate
        self.env.user.notify_success(
            'El T/C PEN -> USD: {}'.format(self.factor), "T/C de compra actualizado")

    def action_update_rate_purchase_pen_usd(self):
        if not self.name:
            raise UserError("La fecha del T/C es obligatoria.")

        if not self.currency_id:
            raise UserError("La moneda es obligatoria.")

        if not(self.type == "purchase" and self.currency_id.name == "USD"):
            raise UserError(
                "Esta opción solo esta disponible para la moneda USD de tipo Venta.")

        if not self.company_id:
            raise UserError("La compañia del tipo de cambio es obligatoria.")

        try:
            res = self.api_migo_usd_pen_exchange_date(
                self.name.strftime("%Y-%m-%d"))
            _logger.info(res)
        except Exception as e:
            today = datetime.now(tz=timezone(
                "America/Lima")).strftime("%Y-%m-%d")
            if today == self.name.strftime("%Y-%m-%d"):
                try:

                    res = self.api_migo_usd_pen_exchange_latest()
                except Exception as e:
                    raise UserError(e)

        rate = float(res.get("precio_compra", False))
        rate = 1/rate if rate != 0.0 else 0.0
        self.rate = rate
        self.factor = 1/rate
        self.env.user.notify_success(
            'El T/C PEN -> USD: {}'.format(self.factor), "T/C de compra actualizado")

    @api.model
    def cron_update_ratio_sale_purchase_pen_usd(self):
        company_ids = self.env["res.company"].search([])
        today = datetime.now(tz=timezone("America/Lima"))
        today_format = today.strftime("%Y-%m-%d")
        today = date.fromisoformat(today_format)

        try:
            res = self.api_migo_usd_pen_exchange_date(today_format)
        except Exception as e:
            try:
                res = self.api_migo_usd_pen_exchange_latest()
            except Exception as e:
                raise UserError(e)

        vals = []

        for comp in company_ids:
            currency_usd_sale = self.env["res.currency"].search(
                [('type', '=', 'sale'), ('name', '=', 'USD')], limit=1)
            currency_usd_purchase = self.env["res.currency"].search(
                [('type', '=', 'purchase'), ('name', '=', 'USD')], limit=1)
            currency_usd_commercial = self.env["res.currency"].search(
                [('type', '=', 'commercial'), ('name', '=', 'USD')], limit=1)
            factor_sale = float(res.get("precio_venta"))
            factor_purchase = float(res.get("precio_compra"))
            factor_commercial = (factor_sale + factor_purchase)/2
            if currency_usd_sale.exists():
                rate_sale = 1/factor_sale
                currency_rate_usd_sale = currency_usd_sale.rate_ids.filtered(lambda r: r.name == today and r.company_id == comp)

                if len(currency_rate_usd_sale) == 0:
                    vals.append({"name": today,
                            "type": "sale",
                            "company_id": comp.id,
                            "rate": rate_sale,
                            "currency_id": currency_usd_sale.id,
                            "factor": factor_sale})
                    #self.env["res.currency.rate"].sudo().create({"name": today,
                    #                                      "type": "sale",
                    #                                      "company_id": comp.id,
                    #                                      "rate": rate_sale,
                    #                                      "currency_id": currency_usd_sale.id,
                    #                                      "factor": factor_sale})
            if currency_usd_purchase.exists():
                rate_purchase = 1/factor_purchase
                currency_rate_usd_purchase = currency_usd_purchase.rate_ids.filtered(lambda r: r.name == today and r.company_id == comp)
                if len(currency_rate_usd_purchase) == 0:
                    vals.append({"name": today,
                                "type": "purchase",
                                "company_id": comp.id,
                                "rate": rate_purchase,
                                "currency_id": currency_usd_purchase.id,
                                "factor": factor_purchase})
                    #self.env["res.currency.rate"].create({"name": today,
                    #                                      "type": "sale",
                    #                                      "company_id": comp.id,
                    #                                      "rate": rate_purchase,
                    #                                      "currency_id": currency_usd_purchase.id,
                    #                                      "factor": factor_purchase})
            if currency_usd_commercial.exists():
                rate_commercial = 1/factor_commercial
                currency_rate_usd_commercial = currency_usd_commercial.rate_ids.filtered(lambda r: r.name == today and r.company_id == comp)
                if len(currency_rate_usd_commercial) == 0:
                    vals.append({"name": today,
                                "type": "commercial",
                                "company_id": comp.id,
                                "rate": rate_commercial,
                                "currency_id": currency_usd_commercial.id,
                                "factor": factor_commercial})
                    #self.env["res.currency.rate"].create({"name": today,
                    #                                      "type": "commercial",
                    #                                      "company_id": comp.id,
                    #                                      "rate": rate_commercial,
                    #                                      "currency_id": currency_usd_commercial.id,
                    #                                      "factor": factor_commercial})

        self.env["res.currency.rate"].sudo().create(vals)

    def save(self):
        self.env.user.notify_success(
            'El T/C PEN -> USD: {}'.format(self.factor), "T/C {} actualizado".format(self.type))


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("currency_id", "invoice_date")
    def _compute_exchante_rate_day(self):
        for move in self:
            # _logger.info(move)
            if move.company_id:
                currency_move = move.currency_id
                invoice_date = datetime.now(tz=timezone(
                    "America/Lima")) if not move.invoice_date else move.invoice_date

                # _logger.info(invoice_date)
                if currency_move:
                    currency_company = self.env.company.currency_id
                    rate = currency_company._convert(
                        1, currency_move, move.company_id, invoice_date, round=False)
                    # _logger.info(rate)
                    move.exchange_rate_day = round(
                        1/(rate if rate > 0 else 1), 4)
                else:
                    move.exchange_rate_day = 1
            else:
                move.exchange_rate_day = 1

    exchange_rate_day = fields.Float(
        "T/C", compute=_compute_exchante_rate_day, digits=(1, 4), store=True)

    # @api.onchange("currency_id","invoice_date")
    # def onchange_exchange_rate_day(self):
    #     for move in self:
    #         if move.currency_id and move.invoice_date:
    #             move.exchange_rate_day = self.env["res.currency"]._get_conversion_rate(move.company_id.currency_id,move.currency_id,move.company_id,move.invoice_date)

    # def post(self):
    # tz = self.env.user.tz or "America/Lima"
    # for move in self:
    #     if not move.invoice_date:
    #         move.invoice_date = datetime.now(tz = timezone(tz))

    #     if move.company_currency_id != move.currency_id:
    #         if not move.tipo_cambio or move.tipo_cambio == 0 :
    #             currency_rate = self.env["res.currency.rate"].sudo().search([("name","=",move.invoice_date.strftime("%Y-%m-%d")),("currency_id","=",move.currency_id.id)])
    #             if currency_rate.exists():
    #                 if move.journal_id.type == "sale":
    #                     move.tipo_cambio = currency_rate[0].cambio_compra

    #                 if move.journal_id.type == "purchase":
    #                     move.tipo_cambio =  currency_rate[0].cambio_venta
    #             else:
    #                 raise UserError("Debe actualizar el tipo de cambio de compra/venta para la fecha {}.".format(move.invoice_date.strftime("%Y-%m-%d")))
    #     else:
    #         move.tipo_cambio =  1
    # return super(AccountMove, self).post()

    # @api.onchange("invoice_date","currency_id")
    # def get_ratio(self):
    #     if self.invoice_date:
    #         if self.company_currency_id != self.currency_id:
    #             # if not self.tipo_cambio or self.tipo_cambio == 0:
    #             currency_rate = self.env["res.currency.rate"].sudo().search([("name","=",self.invoice_date.strftime("%Y-%m-%d")),("currency_id","=",self.currency_id.id)])
    #             if currency_rate.exists():
    #                 if self.journal_id.type == "sale":
    #                     self.tipo_cambio = currency_rate[0].cambio_compra

    #                 if self.journal_id.type == "purchase":
    #                     self.tipo_cambio =  currency_rate[0].cambio_venta
    #             else:
    #                 raise UserError("Debe actualizar el tipo de cambio de compra/venta para la fecha {}.".format(self.invoice_date.strftime("%Y-%m-%d")))
    #         else:
    #             self.tipo_cambio =  1
