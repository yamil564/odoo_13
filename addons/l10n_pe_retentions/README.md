>> Codigo para actualizar los consecutivos de las facturas

UPDATE account_move_line aml 
SET invoice_number = LPAD( aml2.invoice_number, 8, '0' ) 
FROM
	account_move_line aml2
	INNER JOIN catalogs_sunat cs ON cs.ID = aml2.table10_id 
WHERE
	cs.code IN ( '01', '07', '08', '03' ) 
	AND cs.table_code = 'table.10' 
	AND aml.ID = aml2.ID;

UPDATE account_invoice ai1 
SET invoice_number = LPAD( ai1.invoice_number, 8, '0' ) 
FROM
	account_invoice ai
	JOIN catalogs_sunat cs ON cs.ID = ai.table10_id 
WHERE
	cs.code IN ( '01', '07', '08', '03' ) 
	AND cs.table_code = 'table.10' 
	AND ai.ID = ai1.ID 
	AND LENGTH ( ai.invoice_number :: TEXT ) < 8;