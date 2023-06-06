{
    'name': 'Exportador de Reportes de Facturas ZIP',
    'version': '1.0',
    'description': 'Módulo para la exportación de reportes de facturas en versión ZIP',
    'author': 'Luis Millan',
    'website': 'https://bigodoo.com',
    'category': 'account',
    'depends': [
        'base',
        'gestionit_pe_fe'
    ],
    'data': [
        'data/parameters.xml',
        'wizards/account_zip_reports.xml',
        'security/ir.model.access.csv'
    ],
    'application': True,
}