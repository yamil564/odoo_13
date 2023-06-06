# -*- encoding: utf-8 -*-

{
    'name': 'Tipo de Cambio Especial para Pagos/Cobros y Transferencias',
    'summary': """
    	Tipo de Cambio Especial para Pagos/Cobros y Transferencias
    """,
    'version': '13.0.0.0',
    'category': 'Accounting',
    'description': """
       Tipo de Cambio Especial para Pagos/Cobros y Transferencias
    """,
    'author': 'Franco Najarro-BigOdoo',
    'website': '',
    'depends': ['account','gestionit_pe_fe','bo_pe_contabilidad_documents'],
    'data': [
        'views/account_payment_view.xml',
        'views/account_move_view.xml',
    ],
}
