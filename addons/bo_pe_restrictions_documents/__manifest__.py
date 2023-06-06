{
	'name': 'Restricciones Generales de Registro en Documentos',
	'version': "13.1.0",
	'author': 'Franco Najarro',
	'website':'',
	'category':'',
	'depends':['account','purchase','base','sale','gestionit_pe_fe',
		'extra_account_move_line','bo_pe_contabilidad_documents'],
	'description':'''
		'Restricciones Generales de Registro en Documentos'
		''',
	'data':[
		'views/account_move_view.xml',
	],
	'installable': True,
    'auto_install': False,
}