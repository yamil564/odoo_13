{
	'name': 'SUNAT PLE-Compras',
	'version': "13.0.3",
	'author': 'Franco Najarro',
	'website':'',
	'category':'',
	'depends':['account','ple_base','bo_pe_contabilidad_documents'],
	'description':'''
		Modulo de reportes PLE de Najarro.
			> Compras
		''',
	'data':[
		#'security/group_users.xml',
		'security/ir.model.access.csv',
		'views/ple_purchase_view.xml',
		'views/ple_purchase_line_view.xml',
		'views/wizard_printer_ple_purchase_view.xml',
	],
	'installable': True,
    'auto_install': False,
}