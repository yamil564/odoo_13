{
    'name': 'Editor de Diarios en Asientos Contables',
    'version': '1.0.0',
    'category': '',
    'license': 'AGPL-3',
    'summary': "Editor de Diarios en Asientos Contables",
    'author': "Franco Najarro",
    'website': '',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/editor_journals_account_move_view.xml',
        ],
    'installable': True,
    'autoinstall': False,
}
