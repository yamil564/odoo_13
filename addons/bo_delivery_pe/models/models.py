from odoo import models, api, fields,_
import logging
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from pytz import timezone
_logger = logging.getLogger(__name__)


# def float_to_time(time):
#     return '{0:02.0f}:{1:02.0f}'.format(*divmod(float(time) * 60, 60))

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    # delivery_type = fields.Selection(selection_add=[('pe_go_pack','Go PACK'),('pe_express','Express')])
    country_ids = fields.Many2many("res.country",default=lambda self:[self.env.ref("base.pe").id],readonly=False)
    province_ids = fields.Many2many("res.country.state","res_country_state_province",string="Provincias")
    district_ids = fields.Many2many("res.country.state","res_country_state_district",string="Distritos")

    ubigeo_desde = fields.Char("Ubigeo desde")
    ubigeo_hasta = fields.Char("Ubigeo hasta")

    # delivery_district_ids = fields.One2many("delivery.carrier.district","delivery_carrier_id")

    # config_dispatch_date = fields.Boolean("Habilitar despacho",default=False)

    # dispatch_monday = fields.Boolean("Lunes",default=True)
    # dispatch_tuesday = fields.Boolean("Martes",default=True)
    # dispatch_wednesday = fields.Boolean("Miercoles",default=True)
    # dispatch_thursday = fields.Boolean("Jueves",default=True)
    # dispatch_friday = fields.Boolean("Viernes",default=True)
    # dispatch_saturday = fields.Boolean("Sábado",default=True)
    # dispatch_sunday = fields.Boolean("Domingo",default=True)

    # dispatch_deadline_time = fields.Float("Hora de corte",help="esta es la hora de corte de recepción de pedidos del día. Valores permitidos de 0 a 24",default=18)
    # number_date_options = fields.Integer(default=3,string="Número de fechas de despacho")
    # days_dispatch = fields.Integer(default=1,string="Días de despacho desde la compra")

    # def get_dispatch_date_options(self):
    #     if not self.config_dispatch_date:
    #         return []
    #     tz = self.env.user.tz or "America/Lima"
    #     number_date_options = 0
    #     if not(self.dispatch_monday or self.dispatch_tuesday or self.dispatch_wednesday or self.dispatch_thursday or self.dispatch_friday or self.dispatch_saturday or self.dispatch_sunday):
    #         raise UserError("No hay fechas disponibles, debe comuníquese con el administrador de la tienda.")

    #     list_options = []
    #     count_now = 0
    #     now = datetime.now(tz=timezone(tz))
    #     time = float_to_time(self.dispatch_deadline_time)
    #     dispatch_deadline_time = (datetime.combine(now.date(),datetime.strptime(time,"%H:%M").time())+timedelta(hours=5)).astimezone(tz=timezone(tz))
    #     _logger.info(dispatch_deadline_time)
    #     _logger.info(now)
    #     if now < dispatch_deadline_time:
    #         date = (now + timedelta(days=self.days_dispatch)).date().strftime("%d-%m-%Y")
    #         list_options.append(date)
    #         number_date_options += 1
    #     else:
    #         count_now = 1

    #     while number_date_options < self.number_date_options:
    #         date = (now + timedelta(days=(count_now+number_date_options+self.days_dispatch))).date().strftime("%d-%m-%Y")
    #         list_options.append(date)
    #         number_date_options += 1

    #     return list_options

    def _match_address(self, partner):
        self.ensure_one()
        res = super(DeliveryCarrier,self)._match_address(partner)

        if self.province_ids and partner.province_id not in self.province_ids:
            res = False

        if self.district_ids and partner.district_id not in self.district_ids:
            res = False

        if self.ubigeo_desde and (partner.ubigeo or '').upper() < self.ubigeo_desde.upper():
            res = False
        
        if self.ubigeo_hasta and (partner.ubigeo or '').upper() > self.ubigeo_hasta.upper():
            res = False
        return res
    
    # def pe_go_pack_rate_shipment(self,order):
    #     carrier = self._match_address(order.partner_shipping_id)
    #     if not carrier:
    #         return {'success': False,
    #                 'price': 0.0,
    #                 'error_message': _('Error: this delivery method is not available for this address.'),
    #                 'warning_message': False}
    #     delivery_district_ids = self.delivery_district_ids.filtered(lambda r:r.district_id == order.partner_shipping_id.district_id)
    #     if delivery_district_ids.exists():
    #         price = delivery_district_ids[0].amount
    #     else:
    #         return {'success': False,
    #                 'price': 0.0,
    #                 'error_message': _('Error: this delivery method is not available for this address.'),
    #                 'warning_message': False}

    #     company = self.company_id or order.company_id or self.env.company
    #     if company.currency_id and company.currency_id != order.currency_id:
    #         price = company.currency_id._convert(price, order.currency_id, company, fields.Date.today())
        
    #     _logger.info(price)
    #     return {'success': True,
    #             'price': price,
    #             'carrier_price':price,
    #             'error_message': False,
    #             'warning_message': False}

    # def pe_express_rate_shipment(self,order):
    #     carrier = self._match_address(order.partner_shipping_id)
    #     if not carrier:
    #         return {'success': False,
    #                 'price': 0.0,
    #                 'error_message': _('Error: this delivery method is not available for this address.'),
    #                 'warning_message': False}
    #     delivery_district_ids = self.delivery_district_ids.filtered(lambda r:r.district_id == order.partner_shipping_id.district_id)
    #     if delivery_district_ids.exists():
    #         price = delivery_district_ids[0].amount
    #     else:
    #         return {'success': False,
    #                 'price': 0.0,
    #                 'error_message': _('Error: this delivery method is not available for this address.'),
    #                 'warning_message': False}

    #     company = self.company_id or order.company_id or self.env.company
    #     if company.currency_id and company.currency_id != order.currency_id:
    #         price = company.currency_id._convert(price, order.currency_id, company, fields.Date.today())
        
    #     return {'success': True,
    #             'price': price,
    #             'carrier_price':price,
    #             'error_message': False,
    #             'warning_message': False}
