{
	'name': 'Campos adicionales de Documento en Asientos/Apuntes',
	'version': "1.0.0",
	'author': "Franco Najarro",
	'website':'',
	'category':'',
	'depends':['account','gestionit_pe_fe'],
	'description':'''
		Campos adicionales de Documento en Asientos/Apuntes.
			> Campos adicionales de Documento en Asientos/Apuntes
			> Campos adicionales de Documento en Asientos/Apuntes
		''',
	'data':[
		'security/ir.model.access.csv',
		'views/account_move_line_view_form.xml',
		'views/account_move_view.xml',
		'views/sunat_catalogs_10_view.xml',

	],
	'installable': True,
    'auto_install': False,
}