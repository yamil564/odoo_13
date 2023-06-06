{
    'name': 'Kardex de producto',
    'version': '1.0.0',
    'category': '',
    'license': 'AGPL-3',
    'summary': "Modulo de informe de kardex de producto",
    'author': "Franco Najarro",
    'website': '',
    'depends': ['stock','purchase','sale'],
    'data': [
        'security/ir.model.access.csv',
        'report/account_stock_valuation_report_view.xml',
        'security/groups_rule.xml'
        ],
    'installable': True,
}
