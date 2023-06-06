{
	'name': 'SUNAT PLE-Diario-Mayor-Simplificado',
	'version': "1.0.0",
	'author': 'Franco Najarro',
	'website':'',
	'category':'',
	'depends':['account','ple_base','bo_pe_contabilidad_documents'],
	'description':'''
		Modulo de reportes PLE de Libro Diario-Mayor-Simplificado.
			> Libro Diario-Mayor-Simplificado
		''',
	'data':[
		#'security/group_users.xml',
		'security/ir.model.access.csv',
		'views/ple_diary_view.xml',
		'views/ple_diary_line_view.xml',
		'views/wizard_printer_ple_diary_view.xml',
	],
	'installable': True,
    'auto_install': False,
}