


def get_query_kardex(self):
	query = """select table_quantity.id, table_quantity.product_id, table_quantity.create_date, 
		table_quantity.quantity, table_quantity.cantidad_actual, table_quantity.unit_cost, 
		table_quantity.value,
		case when table_quantity.quantity < 0.00 then table_quantity.unit_cost
		when coalesce(table_quantity.cantidad_actual,0.00) = 0.00 then table_quantity.unit_cost 
		when coalesce(table_quantity.cantidad_actual,0.00) <> 0.00 
		then coalesce(table_value.valor_actual,0.00)/coalesce(table_quantity.cantidad_actual,0.00) end costo_promedio

		from 

		(select id, product_id, create_date, quantity,
			(select coalesce(sum(quantity),0.00) from stock_valuation_layer as svl2 where 
				svl2.create_date <= svl.create_date and svl.product_id =svl2.product_id and 
				svl2.id<svl.id order by svl.product_id,svl.create_date)
				+ coalesce(svl.quantity,0.00) as cantidad_actual,
				unit_cost, value
		from stock_valuation_layer as svl order by product_id , create_date,id) as table_quantity

		left join 

		(select id,
			(select coalesce(sum(value),0.00) from stock_valuation_layer as svl2 where 
				svl2.create_date <= svl.create_date and svl.product_id =svl2.product_id and 
				svl2.id<svl.id order by svl.product_id,svl.create_date)
				+ coalesce(svl.value,0.00) as valor_actual
		from stock_valuation_layer as svl order by product_id , create_date,id) table_value on

		table_value.id=table_quantity.id """

###############################################################################

select table_quantity.id,
table_quantity.stock_move_id, 
table_quantity.invoice_number, 
table_quantity.product_id, 
table_quantity.create_date, 
table_quantity.quantity, 
table_quantity.cantidad_actual, 
table_quantity.unit_cost, 
table_quantity.value,
case when table_quantity.quantity < 0.00 then table_quantity.unit_cost
when coalesce(table_quantity.cantidad_actual,0.00) = 0.00 then table_quantity.unit_cost 
when coalesce(table_quantity.cantidad_actual,0.00) <> 0.00 
then coalesce(table_value.valor_actual,0.00)/coalesce(table_quantity.cantidad_actual,0.00) end costo_promedio

from 

(select svl.id, 
svl.stock_move_id, 
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
pol.order_id, 
sm.sale_line_id, 
sol.order_id, 
svl.product_id, 
pdtp.id as product_template_id, 
pdtp.categ_id as categ_id, 
sm.product_uom as uom_id,
svl.company_id as company_id,
svl.quantity,
sm.location_id as location_id, 
sl.usage, 

svl.create_date, 
	(select coalesce(sum(quantity),0.00) from stock_valuation_layer as svl2 where 
		svl2.create_date <= svl.create_date and svl.product_id =svl2.product_id and svl2.id<svl.id order by svl.product_id,svl.create_date)
		+ coalesce(svl.quantity,0.00) as cantidad_actual,
		unit_cost, value
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

table_value.id=table_quantity.id 

#############################################################################
#############################################################################


select table_quantity.id,
table_quantity.stock_move_id, 
table_quantity.invoice_number, 
table_quantity.product_id, 
table_quantity.create_date, 
table_quantity.quantity, 
table_quantity.cantidad_actual, 
table_quantity.unit_cost, 
table_quantity.value,
case when table_quantity.quantity < 0.00 then table_quantity.unit_cost
when coalesce(table_quantity.cantidad_actual,0.00) = 0.00 then table_quantity.unit_cost 
when coalesce(table_quantity.cantidad_actual,0.00) <> 0.00 
then coalesce(table_value.valor_actual,0.00)/coalesce(table_quantity.cantidad_actual,0.00) end costo_promedio

from 

(select svl.id, 
svl.stock_move_id, 
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
pol.order_id, 
sm.sale_line_id, 
sol.order_id, 
svl.product_id, 
pdtp.id as product_template_id, 
pdtp.categ_id as categ_id, 
sm.product_uom as uom_id,
svl.company_id as company_id,
svl.quantity,
sm.location_id as location_id, 
sl.usage, 

svl.create_date, 
	(select coalesce(sum(quantity),0.00) from stock_valuation_layer as svl2 where 
		svl2.create_date <= svl.create_date and svl.product_id =svl2.product_id and svl2.id<svl.id order by svl.product_id,svl.create_date)
		+ coalesce(svl.quantity,0.00) as cantidad_actual,
		unit_cost, value
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

table_value.id=table_quantity.id 