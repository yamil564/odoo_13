# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from odoo.addons import decimal_precision as dp

class AccountStockValuationReport(models.Model):
    _name = 'account.stock.valuation.report'
    _auto = False
    _description = 'Stock move valuation report'
    _order = "product_id, location_id, date"
    _rec_name = "picking_id"

    stock_valuation_layer_id = fields.Many2one('stock.valuation.layer',string="Valoración Inventario")
    move_id = fields.Many2one('stock.move', string="Movimiento")
    type = fields.Selection(selection=[('in','Entrada'),('out','Salida')], string="Ind. ES")
    account_move_id = fields.Many2one('account.move',string="Reg. Contable")
    invoice_number = fields.Char(string="Nro. Documento")
    origin = fields.Char(string="Referencia")
    picking_id = fields.Many2one('stock.picking', string="Cod. Inventario")
    purchase_line_id = fields.Many2one('purchase.order.line', string="Detalle de Compra")
    purchase_id = fields.Many2one('purchase.order', related="purchase_line_id.order_id", string="Compra", readonly=True)
    sale_line_id = fields.Many2one('sale.order.line', string="Detalle de Venta")
    sale_id = fields.Many2one('sale.order', related="sale_line_id.order_id", string="Venta", readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', readonly=True)
    categ_id = fields.Many2one('product.category', string='Categoria', related='product_id.categ_id', readonly=True)
    uom_id = fields.Many2one('uom.uom', string="UoM")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    quantity = fields.Float(string="Cantidad Ingreso", digits=dp.get_precision('Product Unit of Measure'))
    location_id = fields.Many2one('stock.location', string="Ubicacion")
    usage = fields.Selection(related='location_id.usage', string="Tipo de Ubicacion", readonly=True)
    qty_in = fields.Float(string="Cantidad Entrada", digits=dp.get_precision('Product Unit of Measure'))
    cost_in = fields.Float(string="Cost. Unit. Entrada", digits=dp.get_precision('Product Price'))
    total_cost_in = fields.Float(string="Total Costo Entrada", digits=dp.get_precision('Product Price'))
    qty_out = fields.Float(string="Cantidad Salida", digits=dp.get_precision('Product Unit of Measure'))
    cost_out = fields.Float(string="Cost. Unit. Salida", digits=dp.get_precision('Product Price'))
    total_cost_out = fields.Float(string="Total Costo Salida", digits=dp.get_precision('Product Price'))
    
    ###########################################################################################
    qty = fields.Float(string="Saldo Cantidad", digits=dp.get_precision('Product Unit of Measure'))
    unit_cost = fields.Float(string="Cost. Promedio", digits=dp.get_precision('Product Price'))
    value = fields.Float(string="Saldo Costo Total", digits=dp.get_precision('Product Price'))
    #stock_value = fields.Float(string="Valor (Valoración del inventario)")
    ###########################################################################################
    
    date = fields.Datetime(string="Fec. Movimiento")
    date_expected = fields.Datetime(string="Fec. Prevista")
    picking_type_id = fields.Many2one('stock.picking.type',string="Tipo de operacion")
    warehouse_id = fields.Many2one('stock.warehouse', string="Almacén")
    inventory_id = fields.Many2one('stock.inventory', string="Cod. Inventario de Ajuste")


    def init(self):
      tools.drop_view_if_exists(self.env.cr, self._table)
      self.env.cr.execute("""
        CREATE or REPLACE VIEW {} as (
          select 
            table_quantity.id,
            table_quantity.id as stock_valuation_layer_id,
            table_quantity.stock_move_id as move_id, 
            table_quantity.type_operation as TYPE, 
            table_quantity.account_move_id as account_move_id, 
            table_quantity.invoice_number as invoice_number, 
            table_quantity.origin as origin, 
            table_quantity.picking_id as picking_id, 
            table_quantity.purchase_line_id as purchase_line_id, 
            table_quantity.purchase_id as purchase_id, 
            table_quantity.sale_line_id as sale_line_id, 
            table_quantity.sale_id as sale_id, 
            table_quantity.product_id as product_id, 
            table_quantity.product_template_id as product_tmpl_id, 
            table_quantity.categ_id as categ_id, 
            table_quantity.uom_id as uom_id, 
            table_quantity.company_id as company_id, 
            table_quantity.quantity as quantity, 
            table_quantity.location_id as location_id, 
            table_quantity.usage as usage, 
            table_quantity.qty_in as qty_in, 
            table_quantity.cost_in as cost_in, 
            table_quantity.total_cost_in as total_cost_in, 
            table_quantity.qty_out as qty_out, 
            table_quantity.cost_out as cost_out, 
            table_quantity.total_cost_out as total_cost_out, 
            table_quantity.cantidad_actual as qty, 

            case when table_quantity.quantity < 0.00 then table_quantity.unit_cost
            when coalesce(table_quantity.cantidad_actual,0.00) = 0.00 then table_quantity.unit_cost 
            when coalesce(table_quantity.cantidad_actual,0.00) <> 0.00 
            then coalesce(table_value.valor_actual,0.00)/coalesce(table_quantity.cantidad_actual,0.00) end unit_cost,

            table_value.valor_actual as value, 
            table_quantity.create_date as date, 
            table_quantity.date_expected as date_expected, 
            table_quantity.picking_type_id as picking_type_id, 
            table_quantity.warehouse_id as warehouse_id, 
            table_quantity.inventory_id as inventory_id

            from 

            (select 
            svl.id, 
            svl.stock_move_id, 
            case when svl.value >=0.00 then 'in'
            else 'out' end type_operation,
            svl.account_move_id, 
            CASE 
                  WHEN sm.sale_line_id IS NOT NULL THEN
                  (
                  SELECT
                    array_to_string( ARRAY_AGG ( account_move.name ORDER BY account_move.name ), ', ' ) 
                  FROM
                    sale_order_line
                    INNER JOIN sale_order_line_invoice_rel ON sale_order_line_invoice_rel.order_line_id = sale_order_line.
                    ID INNER JOIN account_move_line ON sale_order_line_invoice_rel.invoice_line_id = account_move_line.
                    ID INNER JOIN account_move ON account_move_line.move_id = account_move.ID 
                  WHERE
                    sale_order_line.id = sm.sale_line_id 
                    AND account_move_line.product_id = sm.product_id  
                  ) 
                  WHEN sm.purchase_line_id IS NOT NULL THEN
                  (
                  SELECT
                    array_to_string( ARRAY_AGG ( account_move.name ORDER BY account_move.name ), ', ' ) 
                  FROM
                    purchase_order_line
                    INNER JOIN account_move_line ON account_move_line.purchase_line_id = purchase_order_line.
                    ID INNER JOIN account_move ON account_move_line.move_id = account_move.id 
                  WHERE
                    purchase_order_line.id = sm.purchase_line_id 
                    AND account_move_line.product_id = sm.product_id 
                  ) 
                  WHEN sm.inventory_id IS NOT NULL THEN
                  'AJUSTE' ELSE (
                  SELECT
                    array_to_string( ARRAY_AGG ( DISTINCT ( account_move.name ) ORDER BY account_move.name ), ', ' ) 
                  FROM
                    account_move
                    INNER JOIN account_move_line ON account_move_line.move_id = account_move.id 
                    INNER JOIN stock_picking ON stock_picking.origin = account_move.name 
                  WHERE
                    stock_picking.ID = sm.picking_id 
                    AND account_move_line.product_id = sm.product_id 
                  ) 
                END AS invoice_number,
            sm.origin, 
            sm.picking_id, 
            sm.purchase_line_id, 
            pol.order_id as purchase_id, 
            sm.sale_line_id, 
            sol.order_id sale_id, 
            svl.product_id, 
            pdtp.id as product_template_id, 
            pdtp.categ_id as categ_id, 
            sm.product_uom as uom_id,
            svl.company_id as company_id,
            svl.quantity,
            sm.location_id as location_id, 
            sl.usage, 

            case when svl.quantity >0.00 then svl.quantity
            else 0.00
            end qty_in,
            case when svl.quantity >0.00 then svl.unit_cost
            else 0.00
            end cost_in,

            case when svl.value > 0.00 then svl.value
            when svl.value < 0.00 then 0.00
            end total_cost_in,

            case when svl.quantity <0.00 then abs(svl.quantity)
            else 0.00
            end qty_out,
            case when svl.quantity <0.00 then abs(svl.unit_cost)
            else 0.00
            end cost_out,

            case when svl.value < 0.00 then abs(svl.value)
            when svl.value > 0.00 then 0.00
            end total_cost_out,

            svl.create_date, 
            (select coalesce(sum(quantity),0.00) from stock_valuation_layer as svl2 where 
              svl2.create_date <= svl.create_date and svl.product_id =svl2.product_id and svl2.id<svl.id order by svl.product_id,svl.create_date)
              + coalesce(svl.quantity,0.00) as cantidad_actual,
            svl.unit_cost, 
            svl.value, 
            sm.date, 
            sm.date_expected, 
            sm.picking_type_id, 
            sm.warehouse_id, 
            sm.inventory_id

            from stock_valuation_layer as svl 
            left join stock_move sm on sm.id = svl.stock_move_id 
            left join stock_location sl on sl.id = sm.location_id 
            left join account_move am on am.id = svl.account_move_id 
            left join sale_order_line sol on sol.id = sm.sale_line_id
            left join sale_order so on so.id = sol.order_id 
            left join purchase_order_line pol on pol.id=sm.purchase_line_id 
            left join purchase_order po on po.id = pol.order_id
            left join product_product pdpd on pdpd.id = svl.product_id 
            left join product_template pdtp on pdtp.id = pdpd.product_tmpl_id
            order by svl.product_id, svl.create_date, svl.id) as table_quantity

            left join 

            (select id,
              (select coalesce(sum(value),0.00) from stock_valuation_layer as svl2 where 
                svl2.create_date <= svl.create_date and svl.product_id =svl2.product_id and svl2.id<svl.id order by svl.product_id,svl.create_date)
                + coalesce(svl.value,0.00) as valor_actual
            from stock_valuation_layer as svl order by product_id, create_date,id) table_value on

            table_value.id=table_quantity.id 
               
        )""".format(self._table))



    def action_get_account_moves(self):
        self.ensure_one()
        action_ref = self.env.ref('account.action_move_journal_line')
        if not action_ref:
            return False
        action_data = action_ref.read()[0]
        action_data['domain'] = [('id', 'in', self.move_id.account_move_ids.ids)]
        return action_data



    def get_query_account_stock_valuation_report(self):
      query = """
        select 
        table_quantity.id,
        table_quantity.stock_move_id, 
        table_quantity.type_operation, 
        table_quantity.account_move_id, 
        table_quantity.invoice_number, 
        table_quantity.origin, 
        table_quantity.picking_id, 
        table_quantity.purchase_line_id, 
        table_quantity.purchase_id, 
        table_quantity.sale_line_id, 
        table_quantity.sale_id, 
        table_quantity.product_id, 
        table_quantity.product_template_id, 
        table_quantity.categ_id, 
        table_quantity.uom_id, 
        table_quantity.company_id, 
        table_quantity.quantity, 
        table_quantity.location_id, 
        table_quantity.usage, 
        table_quantity.qty_in, 
        table_quantity.cost_in, 
        table_quantity.total_cost_in, 
        table_quantity.qty_out, 
        table_quantity.cost_out, 
        table_quantity.total_cost_out, 
        table_quantity.cantidad_actual, 

        case when table_quantity.quantity < 0.00 then table_quantity.unit_cost
        when coalesce(table_quantity.cantidad_actual,0.00) = 0.00 then table_quantity.unit_cost 
        when coalesce(table_quantity.cantidad_actual,0.00) <> 0.00 
        then coalesce(table_value.valor_actual,0.00)/coalesce(table_quantity.cantidad_actual,0.00) end costo_promedio,
        table_value.valor_actual, 

        table_quantity.create_date, 
         
        table_quantity.cantidad_actual, 
        table_quantity.unit_cost, 
        table_quantity.value,
        table_quantity.date, 
        table_quantity.date_expected, 
        table_quantity.picking_type_id, 
        table_quantity.warehouse_id, 
        table_quantity.inventory_id

        from 

        (select 
        svl.id, 
        svl.stock_move_id, 
        case when svl.value >=0.00 then 'in'
        else 'out' end type_operation,
        svl.account_move_id, 
        CASE 
              WHEN sm.sale_line_id IS NOT NULL THEN
              (
              SELECT
                array_to_string( ARRAY_AGG ( account_move.name ORDER BY account_move.name ), ', ' ) 
              FROM
                sale_order_line
                INNER JOIN sale_order_line_invoice_rel ON sale_order_line_invoice_rel.order_line_id = sale_order_line.
                ID INNER JOIN account_move_line ON sale_order_line_invoice_rel.invoice_line_id = account_move_line.
                ID INNER JOIN account_move ON account_move_line.move_id = account_move.ID 
              WHERE
                sale_order_line.id = sm.sale_line_id 
                AND account_move_line.product_id = sm.product_id  
              ) 
              WHEN sm.purchase_line_id IS NOT NULL THEN
              (
              SELECT
                array_to_string( ARRAY_AGG ( account_move.name ORDER BY account_move.name ), ', ' ) 
              FROM
                purchase_order_line
                INNER JOIN account_move_line ON account_move_line.purchase_line_id = purchase_order_line.
                ID INNER JOIN account_move ON account_move_line.move_id = account_move.id 
              WHERE
                purchase_order_line.id = sm.purchase_line_id 
                AND account_move_line.product_id = sm.product_id 
              ) 
              WHEN sm.inventory_id IS NOT NULL THEN
              'AJUSTE' ELSE (
              SELECT
                array_to_string( ARRAY_AGG ( DISTINCT ( account_move.name ) ORDER BY account_move.name ), ', ' ) 
              FROM
                account_move
                INNER JOIN account_move_line ON account_move_line.move_id = account_move.id 
                INNER JOIN stock_picking ON stock_picking.origin = account_move.name 
              WHERE
                stock_picking.ID = sm.picking_id 
                AND account_move_line.product_id = sm.product_id 
              ) 
            END AS invoice_number,
        sm.origin, 
        sm.picking_id, 
        sm.purchase_line_id, 
        pol.order_id as purchase_id, 
        sm.sale_line_id, 
        sol.order_id sale_id, 
        svl.product_id, 
        pdtp.id as product_template_id, 
        pdtp.categ_id as categ_id, 
        sm.product_uom as uom_id,
        svl.company_id as company_id,
        svl.quantity,
        sm.location_id as location_id, 
        sl.usage, 

        case when svl.quantity >0.00 then svl.quantity
        else 0.00
        end qty_in,
        case when svl.quantity >0.00 then svl.unit_cost
        else 0.00
        end cost_in,

        case when svl.value > 0.00 then svl.value
        when svl.value < 0.00 then 0.00
        end total_cost_in,

        case when svl.quantity <0.00 then abs(svl.quantity)
        else 0.00
        end qty_out,
        case when svl.quantity <0.00 then abs(svl.unit_cost)
        else 0.00
        end cost_out,

        case when svl.value < 0.00 then abs(svl.value)
        when svl.value > 0.00 then 0.00
        end total_cost_out,

        svl.create_date, 
        	(select coalesce(sum(quantity),0.00) from stock_valuation_layer as svl2 where 
        		svl2.create_date <= svl.create_date and svl.product_id =svl2.product_id and svl2.id<svl.id order by svl.product_id,svl.create_date)
        		+ coalesce(svl.quantity,0.00) as cantidad_actual,
        svl.unit_cost, 
        svl.value, 
        sm.date, 
        sm.date_expected, 
        sm.picking_type_id, 
        sm.warehouse_id, 
        sm.inventory_id

        from stock_valuation_layer as svl 
        left join stock_move sm on sm.id = svl.stock_move_id 
        left join stock_location sl on sl.id = sm.location_id 
        left join account_move am on am.id = svl.account_move_id 
        left join sale_order_line sol on sol.id = sm.sale_line_id
        left join sale_order so on so.id = sol.order_id 
        left join purchase_order_line pol on pol.id=sm.purchase_line_id 
        left join purchase_order po on po.id = pol.order_id
        left join product_product pdpd on pdpd.id = svl.product_id 
        left join product_template pdtp on pdtp.id = pdpd.product_tmpl_id
        order by svl.product_id, svl.create_date, svl.id) as table_quantity

        left join 

        (select id,
        	(select coalesce(sum(value),0.00) from stock_valuation_layer as svl2 where 
        		svl2.create_date <= svl.create_date and svl.product_id =svl2.product_id and svl2.id<svl.id order by svl.product_id,svl.create_date)
        		+ coalesce(svl.value,0.00) as valor_actual
        from stock_valuation_layer as svl order by product_id , create_date,id) table_value on

        table_value.id=table_quantity.id """

      return query
