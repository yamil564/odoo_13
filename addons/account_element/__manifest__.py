{
    'name': 'Tipo de Elemento de Cuenta',
    'version': '1.0.0',
    'category': '',
    'license': 'AGPL-3',
    'summary': "Modulo que permite determinar un Tipo de Elemento de Cuenta",
    'author': "Franco Najarro",
    'website': '',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/data_element_config_view.xml',
        'views/element_config_view.xml',
        'views/account_view.xml',
        ],
    'installable': True,
}
