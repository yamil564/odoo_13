from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.float_utils import float_repr
from odoo.tools import float_is_zero
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_state = fields.Selection([
        ('no_invoice', 'No Invoice'), ('not_paid', 'Not Paid'),
        ('partial_paid', 'Partial Paid'), ('fully_paid', 'Fully Paid'),
        ('overdue', 'Overdue')], string='Payment Status', default='no_invoice', copy=False, readonly=True,
        help="Payment Status.")

    compute_payment_state = fields.Char(string='Payment Status', compute='_show_payment_state', store=False,
                                        copy=False, default='no_invoice', index=True, readonly=True,
                                        help="Payment Status.")

    ribbon_payment_state = fields.Char(string='Payment Status', store=False, default='no_invoice',
                                       compute='_show_payment_state')

    show_payment_button = fields.Boolean(string='Show Payment Button', compute='_show_payment_button', store=False,
                                         copy=False)

    payments_widget = fields.Text(string='Payment Details',
                                  groups="account.group_account_invoice,account.group_account_readonly",
                                  compute='_compute_payments_widget_reconciled_info')

    order_amount_residual = fields.Monetary(string='Amount Due', compute='_compute_order_amount',
                                            help="Order Amount Due.")

    def _show_payment_state(self):
        for order in self:
            is_fully_delivery = order._is_fully_delivery()
            order.compute_payment_state = 'no_invoice'
            if order.state in ['done', 'sale']:
                invoices = order.mapped("invoice_ids").filtered(
                    lambda i: i.state in ["posted"]
                              and i.type in ['out_invoice', 'out_receipt']
                              and i.invoice_payment_state not in ['paid']
                )

                if not is_fully_delivery:
                    pl_order_amount_due = float(float_repr(order.order_amount_residual,
                                                           precision_digits=order.currency_id.decimal_places))

                    amount_total = order.amount_total
                    if pl_order_amount_due >= amount_total:
                        if order.invoice_ids:
                            order.compute_payment_state = 'not_paid'
                    elif 0 < pl_order_amount_due < amount_total and invoices:
                        order.compute_payment_state = 'partial_paid'
                    elif pl_order_amount_due == 0:
                        order.compute_payment_state = 'fully_paid'
                else:
                    total_paid, total_invoice_amount = order._get_total_paid_total_invoice_amount()
                    invoiceable_lines = order._get_invoiceable_orderline()
                    if invoiceable_lines:
                        total_invoice_amount += sum(
                            (line.qty_delivered - line.qty_invoiced) * line.price_reduce_taxinc for line in
                            invoiceable_lines)

                    if total_invoice_amount > total_paid and not total_paid:
                        if order.invoice_ids:
                            order.compute_payment_state = 'not_paid'
                    elif 0 < total_paid < total_invoice_amount and invoices:
                        order.compute_payment_state = 'partial_paid'
                    elif total_paid >= total_invoice_amount > 0:
                        order.compute_payment_state = 'fully_paid'

            # Check payment overdue
            if order.compute_payment_state in ['partial_paid', 'not_paid']:
                today = fields.Date.context_today(self)
                invoices = order.mapped("invoice_ids").filtered(
                    lambda i: i.state in ["posted"] and i.type in ['out_invoice', 'out_receipt'] and i.invoice_payment_state not in ['paid']
                )

                if any(True for l in invoices if l.invoice_date_due and l.invoice_date_due < today):
                    order.compute_payment_state = 'overdue'

            order.ribbon_payment_state = order.compute_payment_state

            if order.compute_payment_state != order.payment_state:
                order.payment_state = order.compute_payment_state

            if order.compute_payment_state == 'no_invoice':
                order.compute_payment_state = _('No Invoice')
            elif order.compute_payment_state == 'not_paid':
                order.compute_payment_state = _('Not Paid')
            elif order.compute_payment_state == 'partial_paid':
                order.compute_payment_state = _('Partial Paid')
            elif order.compute_payment_state == 'fully_paid':
                order.compute_payment_state = _('Fully Paid')
            elif order.compute_payment_state == 'overdue':
                diff = 0
                today = fields.Date.context_today(self)
                for l in order.invoice_ids:
                    if (today - l.invoice_date_due).days > diff:
                        diff = (today - l.invoice_date_due).days
                if diff == 1:
                    order.compute_payment_state = _('Overdue (yesterday)')
                elif diff > 1:
                    order.compute_payment_state = _('Overdue (%s days ago)') % str(diff)

    def _show_payment_button(self):
        self.show_payment_button = False
        invoice_not_paid = self.invoice_ids.filtered(lambda i: i.invoice_payment_state in ['not_paid']
                                                               and i.type == 'out_invoice')

        amount_total_signed = 0
        invoices = self.mapped("invoice_ids").filtered(
            lambda i: i.state in ["posted"] and i.type in ['out_invoice', 'out_receipt', 'out_refund']
        )
        for inv in invoices:
            amount_total_signed += inv.amount_total_signed

        if amount_total_signed and invoice_not_paid:
            self.show_payment_button = True

    def _compute_order_amount(self):
        for order in self:
            total_paid, pl_order_amount_due = order._get_total_paid_total_invoice_amount()
            invoiceable_lines = order._get_invoiceable_orderline()
            is_fully_delivery = order._is_fully_delivery()

            if not is_fully_delivery and invoiceable_lines:
                pl_order_amount_due += sum((line.product_uom_qty - line.qty_invoiced) * line.price_reduce_taxinc for line in invoiceable_lines)
            elif is_fully_delivery and invoiceable_lines:
                pl_order_amount_due += sum(
                    (line.qty_delivered - line.qty_invoiced) * line.price_reduce_taxinc for line in invoiceable_lines)

            pl_order_amount_due = pl_order_amount_due - total_paid

            txs = self.env['payment.transaction'].sudo().search([('sale_order_ids', '=', order.id)])
            for tx in txs:
                if tx and tx.state == 'done' and tx.payment_id and tx.payment_id.state == 'posted':
                    pl_order_amount_due -= tx.amount

            order.order_amount_residual = pl_order_amount_due if pl_order_amount_due > 0 else 0.0

    def _compute_payments_widget_reconciled_info(self):
        self.ensure_one()
        reconciled_vals = []
        payments_widget_vals = {'title': _('Less Payment'), 'outstanding': False, 'content': []}

        account_payment = self.env['account.payment'].search([('invoice_ids', 'in', self.invoice_ids.ids)])
        if account_payment:
            for p in account_payment:
                reconciled_vals.append({
                    'name': p.name,
                    'journal_name': p.journal_id.name,
                    'amount': p.amount,
                    'currency': p.currency_id.symbol,
                    'digits': [69, p.currency_id.decimal_places],
                    'position': p.currency_id.position,
                    'date': p.payment_date,
                    # 'payment_id': p.id,
                    # 'partial_id': partial.id,
                    'account_payment_id': p.id,
                    'payment_method_name': p.payment_method_id.name if p.journal_id.type == 'bank' else None,
                    # 'move_id': counterpart_line.move_id.id,
                    'ref': p.communication,
                })
            payments_widget_vals['content'] = reconciled_vals

        else:
            txs = self.env['payment.transaction'].sudo().search([('sale_order_ids', '=', self.id)])
            for tx in txs:
                if tx and tx.state == 'done' and tx.payment_id and tx.payment_id.state == 'posted':
                    p = tx.payment_id
                    reconciled_vals.append({
                        'name': p.name,
                        'journal_name': p.journal_id.name,
                        'amount': p.amount,
                        'currency': p.currency_id.symbol,
                        'digits': [69, p.currency_id.decimal_places],
                        'position': p.currency_id.position,
                        'date': p.payment_date,
                        # 'payment_id': p.id,
                        # 'partial_id': partial.id,
                        'account_payment_id': p.id,
                        'payment_method_name': p.payment_method_id.name if p.journal_id.type == 'bank' else None,
                        # 'move_id': counterpart_line.move_id.id,
                        'ref': p.communication,
                    })
                    payments_widget_vals['content'] = reconciled_vals

        if payments_widget_vals['content']:
            self.payments_widget = json.dumps(payments_widget_vals, default=date_utils.json_default)
        else:
            self.payments_widget = json.dumps(False)

    def _get_invoiceable_orderline(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for line in self.order_line:
            if line.order_id.state not in ['sale', 'done']:
                return []

            if line.display_type == 'line_section':
                # Only invoice the section if one of its lines is invoiceable
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(line.product_uom_qty - line.qty_invoiced,
                                                                  precision_digits=precision):
                continue
            if line.product_uom_qty - line.qty_invoiced > 0 or (
                    line.product_uom_qty - line.qty_invoiced < 0 and final) or line.display_type == 'line_note':
                if line.is_downpayment:
                    # Keep down payment lines separately, to put them together
                    # at the end of the invoice, in a specific dedicated section.
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = None
                invoiceable_line_ids.append(line.id)

        return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)

    def action_register_payment(self):

        invoice_not_paid = self.invoice_ids.filtered(lambda i: i.invoice_payment_state in ['not_paid', 'partial']
                                                               and i.type in ['out_invoice', 'out_receipt'])

        if not invoice_not_paid:
            raise UserError(_("You can't register a payment "
                              "because there is nothing left to pay on the selected journal items."))

        group_payment = len(invoice_not_paid) > 1

        return {
            'name': _('Register Payment'),
            'res_model': len(invoice_not_paid) == 1 and 'account.payment' or 'account.payment.register',
            'view_mode': 'form',
            'view_id': len(invoice_not_paid) != 1 and self.env.ref(
                'account.view_account_payment_form_multi').id or self.env.ref(
                'account.view_account_payment_invoice_form').id,
            'context': {
                'active_model': 'account.move',
                'active_ids': invoice_not_paid.ids,
                'default_group_payment': group_payment,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _get_total_paid_total_invoice_amount(self):
        self.ensure_one()
        total_paid = 0
        total_invoice_amount = 0
        if self.mapped("invoice_ids"):
            invoices = self.mapped("invoice_ids").filtered(
                lambda i: i.state in ["posted"]
                          and i.type in ['out_invoice', 'out_receipt']
            )

            if invoices:
                for invoice in invoices:
                    total_paid += invoice.amount_total - invoice.amount_residual
                    total_invoice_amount += invoice.amount_total

        txs = self.env['payment.transaction'].sudo().search([('sale_order_ids', '=', self.id)])
        for tx in txs:
            if tx and tx.state == 'done' and tx.payment_id and tx.payment_id.state == 'posted':
                total_paid += tx.amount

        return total_paid, total_invoice_amount
    def _is_fully_delivery(self):
        self.ensure_one()
        is_fully_delivery = False
        pickings_done = self.picking_ids.filtered(lambda p: (p.state in ['done']))

        pickings_not_done = self.picking_ids.filtered(
            lambda p: (
                    p.state not in ['done', 'cancel']
                    and p.state in ['draft', 'waiting', 'confirmed', 'assigned']
            )
        )

        if pickings_done and not pickings_not_done:
            is_fully_delivery = True
        elif pickings_not_done:
            is_fully_delivery = False

        return is_fully_delivery