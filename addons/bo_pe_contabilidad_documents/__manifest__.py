{
	'name': 'Configuraciones de Contabilidad en Moneda Extranjera-Recibos por Honorarios',
	'version': "1.1.0",
	'author': 'Franco Najarro',
	'website':'',
	'category':'',
	'depends':['account','purchase','base','sale','gestionit_pe_fe','extra_account_move_line'],
	'description':'''
		Configuraciones de Contabilidad en Moneda Extranjera.
			> Configuraciones de Contabilidad en Moneda Extranjera
		''',
	'data':[
		'security/res_groups.xml',
		'views/res_config_settings_view.xml',
		'views/res_partner_view.xml',
		'views/account_move_line_view.xml',
		'views/account_move_view.xml',
		'views/account_payment_view.xml',
		'views/wizard_report_account_payable_view.xml',
		'views/wizard_report_account_receivable_view.xml',

	],
	'installable': True,
    'auto_install': False,
}