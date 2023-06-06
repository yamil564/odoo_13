# -*- coding: utf-8 -*-
{
    'name': "Reporte de Comprobantes en Excel",
    'summary': """
        Exportación de Comprobantes en Excel""",
    'description': """
        Long description of module's purpose
    """,
    'author': "Reporte de Comprobantes",
    'website': "http://www.facturacion.vip",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'account','account_period', 'report_xlsx'],
    'data': [
        'views/views.xml',
        'views/templates.xml',
        'report/report.xml'
    ],
    'demo': [],
}
