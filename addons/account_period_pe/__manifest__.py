# -*- coding: utf-8 -*-
{
    'name': "Periodo Contable",

    'summary': """
        Periodo contable Multi-Empresa""",

    'description': """
        Periodo contable Multi-Empresa
    """,

    'author': "Franco Najarro",
    'website': "",

    'category': 'Accounting',
    'version': '1.1',

    # any module necessary for this one to work correctly
    'depends': ['account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_menuitem.xml',
        'views/account_views.xml',
        'views/account_end_fy.xml',
        'views/account_move.xml',
        'views/account_move_line.xml'
    ],

}