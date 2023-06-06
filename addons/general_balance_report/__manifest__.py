{
	'name': 'ESTADO DE SITUACIÓN FINANCIERA',
	'version': "1.0.0",
	'author': 'Franco Najarro',
	'website':'',
	'category':'',
	'depends':['base','account','unique_library_accounting_queries','account_period_pe','report_formats'],
	'description':'''
		Modulo de Reporte de Estado de Situación Financiera.
		''',
	'data':[
		'security/ir.model.access.csv',
		'views/template_general_balance_report_view.xml',
		'views/template_elements_report_view.xml',
		'data/template.general.balance.report.csv',
		'data/template.activos.corrientes.line.csv',
		'data/template.activos.no.corrientes.line.csv',
		'data/template.pasivos.corrientes.line.csv',
		'data/template.pasivos.no.corrientes.line.csv',
		'data/template.patrimonio.line.csv',
		'views/dorniers_general_balance_report_view.xml',
		'views/dorniers_general_balance_report_line_view.xml',
	],
	'installable': True,
    'auto_install': False,
}