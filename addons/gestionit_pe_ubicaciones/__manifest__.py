{
    "name": "GIT - Parámetros de ubigeo - Perú",
    'version': '1.0.0',
    'author': 'Gestión IT',
    'description': 'Tabla paramétrica de Ubicaciones de Perú: Departamentos, Provincias y distritos.',
    'depends': ['base'],
    'data': [
        'views/res_partner_view.xml',
        'views/res_country_view.xml',
        'views/res_country_data_provincias.xml',
        'views/res_country_data_distritos.xml',
    ],
    'images': [
        'static/description/ubigeos_banner.png',
    ],
    'installable': True,
    'auto_install': False,
    "sequence": 1,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
