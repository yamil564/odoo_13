{
	'name': 'SUNAT_PLE_Libros_Base',
	'version': "1.0.2",
	'author': 'Franco Najarro',
	'website':'',
	'category':'',
	'depends':['account','report_formats','bo_pe_contabilidad_documents','base'],
	'description':'''
		Modulo de reportes.
			> Base
		''',
	'data':[
		'security/group_users.xml',
		'security/ir.model.access.csv',
		'views/ple_base_view.xml',
		'views/wizard_printer_ple_base_view.xml',
		'views/res_country_view.xml',

	],
	'installable': True,
    'auto_install': False,
}