{
	'name': 'SUNAT PLE-Diario-Simplificado-Plan Contable',
	'version': "13.0.0",
	'author': 'Franco Najarro',
	'website':'',
	'category':'',
	'depends':['account','ple_base'],
	'description':'''
		Modulo de reportes PLE del Plan Contable utilizado.
			> Plan Contable del Libro Diario y Simplificado Utilizado
		''',
	'data':[
		#'security/group_users.xml',
		'security/ir.model.access.csv',
		'views/ple_diary_accounting_plan_view.xml',
		'views/ple_diary_accounting_plan_line_view.xml',
		'views/wizard_printer_ple_diary_accounting_plan_view.xml',
	],
	'installable': True,
    'auto_install': False,
}