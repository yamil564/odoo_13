
from odoo import api, models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_due = fields.Char("Delivery Due", compute='_show_delivery_due', copy=False, store=False)
    compute_field = fields.Boolean(string="check field", compute='_check_group_user')

    delivery_state = fields.Selection([
        ('done', 'Done'), ('waiting', 'Waiting'),
        ('partial_ready', 'Partial Ready'),
        ('partial_delivery', 'Partial Delivery'),
        ('fully_ready', 'Fully Ready')], string='Delivery Status',
        compute='_calculate_delivery_state', store=True,
        copy=False, default='waiting', index=True, readonly=False,
        help="Delivery Status.")

    @api.depends('picking_ids.move_ids_without_package', 'order_line')
    def _calculate_delivery_state(self):
        for o in self:
            o.delivery_state = 'waiting'
            pickings_done = o.picking_ids.filtered(lambda p: (p.state in ['done']))
            pickings_not_done = o.picking_ids.filtered(
                lambda p: (
                        p.state not in ['done', 'cancel']
                        and p.state in ['draft', 'waiting', 'confirmed', 'assigned']
                )
            )

            stock_move_forecast = pickings_not_done.move_ids_without_package.filtered(
                lambda sm: (
                        sm.sale_line_id
                        and not sm.sale_line_id.is_delivery
                        and sm.state in ['assigned']
                )
            )

            stock_move_forecast_partial = pickings_not_done.move_ids_without_package.filtered(
                lambda sm: (
                        sm.sale_line_id
                        and not sm.sale_line_id.is_delivery
                        and sm.state in ['partially_available']
                )
            )

            stock_move_forecast_not_partial = pickings_not_done.move_ids_without_package.filtered(
                lambda sm: (
                        sm.sale_line_id
                        and not sm.sale_line_id.is_delivery
                        and sm.state not in ['partially_available', 'assigned', 'done']
                )
            )

            stock_move_not_done = pickings_done.move_ids_without_package.filtered(
                lambda sm: (
                        sm.sale_line_id
                        and not sm.sale_line_id.is_delivery
                        and sm.quantity_done < sm.sale_line_id.product_uom_qty
                        and sm.state in ['done']
                )
            )

            stock_move_done = pickings_done.move_ids_without_package.filtered(
                lambda sm: (
                        sm.sale_line_id
                        and not sm.sale_line_id.is_delivery
                        and sm.quantity_done == sm.sale_line_id.product_uom_qty
                        and sm.state in ['done']
                )
            )
            lines_not_delivery = o.order_line.filtered(
                lambda l: (
                    not l.is_delivery
                )
            )
            if o.state in ['sale', 'done']:
                o.delivery_state = 'waiting'
                if len(lines_not_delivery) == len(stock_move_done):
                    o.delivery_state = 'done'
                else:
                    if not pickings_done and pickings_not_done and stock_move_forecast_partial:
                        o.delivery_state = 'partial_ready'
                    elif not pickings_done and pickings_not_done and not stock_move_forecast:
                        o.delivery_state = 'waiting'
                    elif not pickings_done and pickings_not_done \
                            and stock_move_forecast and len(stock_move_forecast) < len(lines_not_delivery):
                        o.delivery_state = 'partial_ready'
                    elif stock_move_not_done and pickings_not_done and not stock_move_forecast_partial and not stock_move_forecast:
                        o.delivery_state = 'partial_delivery'
                    elif stock_move_not_done and pickings_not_done and (
                            stock_move_forecast_partial or stock_move_forecast):
                        if stock_move_forecast_partial or stock_move_forecast_not_partial:
                            o.delivery_state = 'partial_ready'
                        elif not stock_move_forecast_partial and stock_move_forecast and not stock_move_forecast_not_partial:
                            o.delivery_state = 'fully_ready'
                    elif pickings_done and pickings_not_done:
                        if stock_move_forecast:
                            o.delivery_state = 'fully_ready'
                        elif not stock_move_forecast and stock_move_forecast_partial:
                            o.delivery_state = 'partial_ready'
                        else:
                            o.delivery_state = 'partial_delivery'
                    elif not stock_move_not_done and pickings_not_done:
                        for sp in pickings_not_done:
                            if sp.state == 'assigned':
                                o.delivery_state = 'fully_ready'
                            else:
                                o.delivery_state = 'waiting'
                    else:
                        o.delivery_state = 'done'
            else:
                o.delivery_state = ''

    def _show_delivery_due(self):
        for o in self:
            o.delivery_due = ''
            commitment_date = o.commitment_date or o.expected_date

            if o.delivery_state in ['waiting', 'fully_ready', 'partial_ready', 'partial_delivery'] and commitment_date:
                today = fields.Datetime.now()
                diff = today - commitment_date
                if diff.days > 0:
                    if diff.days == 1:
                        o.delivery_due = 'Due yesterday'
                    else:
                        o.delivery_due = ('%s%s%s') % ('Due ', str(diff.days), ' days ago')
                elif diff.days < 0:
                    if diff.days == -1:
                        o.delivery_due = 'Due tomorrow'
                    else:
                        o.delivery_due = ('%s%s%s') % ('Due next ', str(-diff.days), ' days.')
                else:
                    o.delivery_due = 'Due today'

    def _check_group_user(self):
        for order in self:
            if self.env.user.has_group("sale_order_delivery_status.edit_delivery_status_manually"):
                order.compute_field = True
            else:
                order.compute_field = False