from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging
from odoo.addons.gestionit_pe_fe.models.parameters.catalogs import tnc, tnd, tdc, tdr
_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    invoice_journal_id = fields.Many2one("account.journal")
    # desc_global = fields.Float(string="Descuento global", default=0)

    invoice_type = fields.Selection(selection=[('out_refund', 'Devolución'), (
        'out_invoice', 'Venta')], string="Tipo de movimiento", default="")
    invoice_type_code_id = fields.Char(
        string="Tipo de comprobante electrónico")
    refund_invoice_id = fields.Many2one(
        "account.move", string="Comprobante a rectificar")
    credit_note_comment = fields.Char(string="Sustento de nota")
    credit_note_type = fields.Selection(string='Tipo de Nota de Crédito', readonly=True,
                                        selection="_selection_credit_note_type", states={'draft': [('readonly', False)]})

    def _selection_credit_note_type(self):
        return tnc

    def _prepare_invoice_line(self, order_line):
        res = super(PosOrder, self)._prepare_invoice_line(order_line)
        res.update({
            'lot_name': ",".join(order_line.pack_lot_ids.mapped('lot_name'))
        })
        return res

        # if order_line.price_unit*order_line.qty > 0:
        #     return {
        #         'product_id': order_line.product_id.id,
        #         'quantity': order_line.qty if self.amount_total >= 0 else -order_line.qty,
        #         'discount': order_line.discount,
        #         'price_unit': order_line.price_unit,
        #         'name': order_line.product_id.display_name,
        #         'tax_ids': [(6, 0, order_line.tax_ids_after_fiscal_position.ids)],
        #         'product_uom_id': order_line.product_uom_id.id,
        #         'lot_name': ",".join(order_line.pack_lot_ids.mapped('lot_name'))
        #     }
        # else:
        #     self.desc_global += abs(order_line.qty*order_line.price_unit)

    def _prepare_invoice_vals(self):
        vals = super(PosOrder, self)._prepare_invoice_vals()

        # if not self.invoice_journal_id:
        #     raise ValidationError(
        #         "La creación del comprobante requiere de la selección de una Serie de facturación.")

        # desc_percent = (abs(self.desc_global)*100) / (abs(self.desc_global)+self.amount_total)

        vals.update({
            "journal_id": self.invoice_journal_id.id,
            "reversed_entry_id": self.refund_invoice_id.id,
            "invoice_type_code": self.invoice_journal_id.invoice_type_code_id,
            "tipo_nota_credito": self.credit_note_type,
            "sustento_nota": self.credit_note_comment,
            "type": self.invoice_type,
            # Cambio para loyalty
            # 'invoice_line_ids': [(0, None, self._prepare_invoice_line(line)) for line in self.lines if line.price_unit*line.qty > 0],
            # "apply_global_discount": True if abs(desc_percent) > 0 else False,
            # "descuento_global": abs(desc_percent)
        })

        return vals

    def action_pos_order_invoice(self):
        moves = self.env['account.move']

        for order in self:
            # Force company for all SUPERUSER_ID action
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            move_vals = order._prepare_invoice_vals()
            new_move = order._create_invoice(move_vals)
            new_move._onchange_recompute_dynamic_lines()

            order.write({'account_move': new_move.id, 'state': 'invoiced'})
            new_move.sudo().with_context(force_company=order.company_id.id).post()
            moves += new_move

        if not moves:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': moves and moves.ids[0] or False,
        }

    def _order_fields(self, ui_order):
        vals = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get("invoice_journal_id", False):
            if ui_order.get("invoice_type_code_id") in ["01","03"]:
                invoice_type = "out_invoice"
            elif ui_order.get("invoice_type_code_id") == "07":
                invoice_type = "out_refund"
            # invoice_journal = self.env["account.journal"].sudo().browse(invoice_journal_id)
            # if invoice_journal.
            vals.update({'invoice_journal_id': ui_order.get("invoice_journal_id"),
                         'invoice_type_code_id': ui_order.get("invoice_type_code_id"),
                         'invoice_type': ui_order.get("invoice_type",invoice_type),
                         'credit_note_comment': ui_order.get("credit_note_comment"),
                         'credit_note_type': ui_order.get("credit_note_type")})
        if len(ui_order.get("refund_invoice", [])) == 2:
            vals.update(
                {"refund_invoice_id": ui_order.get("refund_invoice", [])[0]})

        return vals

    # @profile
    # @api.model
    # def _order_fields(self, ui_order):
    #     _logger.info(ui_order)
    #     res = super(PosOrder, self)._order_fields(ui_order)
    #     res['number'] = ui_order.get('number', False)
    #     res['invoice_journal'] = ui_order.get('invoice_journal', False)
    #     res['sequence_number'] = ui_order.get('sequence_number', '')
    #     res['invoice_type_code_id'] = ui_order.get('invoice_type_code_id', '')
    #     res['invoice_type'] = ui_order.get('invoice_type', '')

    #     if res.get("invoice_type",False) == "out_refund":
    #         res['credit_note_comment'] = ui_order.get("credit_note_comment")
    #         res['credit_note_type'] = ui_order.get("credit_note_type")
    #         if "refund_invoice" in ui_order:
    #             if len(ui_order["refund_invoice"]) == 2:
    #                 res['refund_invoice'] = ui_order.get('refund_invoice', [])[0]
    #     return res

    def get_current_invoice(self):
        res = {"digest_value": "*"}
        for order in self:
            invoice = order.account_move
            if invoice:
                res.update({"pos_order_id": order.id,
                            "digest_value": invoice.digest_value if invoice.digest_value else "*",
                            "name": invoice.name if invoice.digest_value else "*",
                            "invoice_portal_url": invoice.get_portal_url(report_type="pdf", download=True)})

            return res

    def get_invoice_name(self):
        self.ensure_one()
        invoice_type_names = {"01": "Factura Electrónica",
                              "03": "Boleta Electrónica", "07": "Nota de Crédito"}
        invoice = self.account_move
        if invoice:
            invoice_type_name = invoice_type_names.get(
                invoice.invoice_type_code) or ""
            name = invoice.name
            return "{} {}".format(invoice_type_name, name)
        return ""

    def _prepare_done_order_for_pos(self):
        res = super(PosOrder, self)._prepare_done_order_for_pos()
        if self.partner_id:
            res.update({
                "partner_id": [self.partner_id.id, self.partner_id.name],
            })
        if self.account_move.state == "posted":
            res.update({
                "invoice_journal_id": self.invoice_journal_id.id,
                "invoice_type_code_id": self.account_move.invoice_type_code,
                "number": self.account_move.name,
                "sequence_number": self.account_move.name.split("-")[1],
                "digest_value": self.account_move.digest_value,
                "account_move": [self.account_move.id, self.account_move.name],
                "refund_invoice": [self.account_move.reversed_entry_id.id, self.account_move.reversed_entry_id.name],
                "credit_note_type_name": self.account_move.tipo_nota_credito
            })
        return res

    def _prepare_fields_for_pos_list(self):
        res = super(PosOrder, self)._prepare_fields_for_pos_list()
        res.append("account_move")
        return res

    def get_order(self):
        result = {"has_invoice": False}
        self.ensure_one()
        result["date"] = self.date_order
        result["order_name"] = self.name
        if self.account_move:
            result["has_invoice"] = True
            result["invoice_id"] = [
                self.account_move.id, self.account_move.name]
            # Tipos de comprobantes 01- Factura ; 03- Boleta ; 07- Nota de crédito ; 08- Nota de débito
            result["invoice_type_code"] = self.account_move.invoice_type_code
            result["date"] = self.account_move.invoice_date
            result["payments"] = self.payment_ids.mapped(
                lambda r: {'id': r.payment_method_id.id, 'amount': r.amount})
        result["lines"] = self.lines.mapped(lambda r: {"product_id": r.product_id.id,
                                                       "price_unit": r.price_unit,
                                                       "qty": r.qty})

        return result


class l10nLatamIdentificationType(models.Model):
    _inherit = "l10n_latam.identification.type"

    available_in_pos = fields.Boolean("Disponible en POS", default=False)
