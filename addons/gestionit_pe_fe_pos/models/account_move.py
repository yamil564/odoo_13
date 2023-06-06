from odoo import models, fields, _
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoiced_lot_values(self):
        res = super(AccountMove, self)._get_invoiced_lot_values()

        sql = """
            select aml.product_id as product_id,
                aml.name as product_name,
                pol.qty as quantity ,
                uu.name as uom_name,
                ppol.lot_name as lot_name
                from account_move_line aml
                left join account_move am on am.id = aml.move_id 
                left join pos_order po on po.account_move = am.id
                left join pos_order_line pol on pol.order_id = po.id and aml.product_id = pol.product_id 
                left join pos_pack_operation_lot ppol on ppol.pos_order_line_id = pol.id
                left join uom_uom uu on aml.product_uom_id = uu.id
                where am.id = {} and ppol.lot_name is not null
                group by aml.product_id,aml.name,pol.qty,uu.name ,ppol.lot_name
        """
        # _logger.info(sql.format(self.id))
        self.env.cr.execute(sql.format(self.id))
        result = self.env.cr.dictfetchall()
        res += result

        # _logger.info(res)
        return res
