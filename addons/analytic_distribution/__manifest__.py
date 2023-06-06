{
    'name': 'Distribucion de Cuenta',
    'version': '1.0.0',
    'category': '',
    'license': 'AGPL-3',
    'summary': "Modulo de distribucion de cuenta con contabilidad analitica",
    'author': "Franco Najarro-Big Odoo",
    'website': '',
    'depends': ['account','analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/analytic_account_view.xml',
        'views/account_view.xml',
        'views/account_move_view.xml',
        'views/wizard_account_analytic_distribution_view.xml',
        ],
    'installable': True,
}
