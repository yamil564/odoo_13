{
    "name": "Emisión de Documentos de Contingencia desde Ventas",
    "author": "Franco Najarro",
    "description": "Emisión de Documentos de Contingencia desde Ventas",
    "depends": [
        "base",
        "account",
        "sale",
        "gestionit_pe_fe"],
    "data": [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'views/account_journal_view.xml',
        'views/sale_order.xml',
        'views/wizard_sale_order_contingencia_view.xml',

    ]
}
