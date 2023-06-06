{
	'name': 'Extracto Bancario Automático',
	'version': "13.0.0",
	'author': 'Franco Najarro-BigOdoo',
	'website':'',
	'category':'',
	'depends': ['account','report_formats'],
	'description':'''
		Modulo de Extracto Bancario Automático al generar Asientos contables donde participan cuentas de liquidez.
			> Conciliación bancaria
		''',
	'data':[
		'views/account_journal_view.xml',
		'views/account_bank_statement_view.xml',
	],
	'installable': True,
	'auto_install': False,
}