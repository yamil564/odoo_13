{
    "name": "GIT - Consulta de datos de clientes",
    "author": "Gestión IT",
    "description": "Consulta y obtención de datos desde RUC o DNI",
    "depends": [
        "base",
        "l10n_latam_base",
        "l10n_pe",
        "sale",
        "gestionit_pe_ubicaciones"],
    "data": [
        'security/res_groups.xml',
        'data/res_company.xml',
        'data/identification_type.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
        'views/sale_order.xml',
        'views/res_users.xml'
    ]
}
