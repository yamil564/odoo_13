{
	'name': 'SUNAT PLE VENTAS',
	'version': "1.1.0",
	'author': 'Franco Najarro',
	'website':'',
	'category':'',
	'depends':['account','ple_base','bo_pe_contabilidad_documents'],
	'description':'''
		Modulo de reportes PLE ventas.
			> Ventas
		''',
	'data':[
		#'security/group_users.xml',
		'security/ir.model.access.csv',
		'views/ple_sale_view.xml',
		'views/ple_sale_line_view.xml',
		'views/wizard_printer_ple_sale_view.xml',
	],
	'installable': True,
    'auto_install': False,
}