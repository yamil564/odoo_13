{
    "name": "GIT - Actualización Automática de Tipo de Dólares desde SUNAT",
    "author": "Gestión IT",
    "description": "",
    'depends': [
        "base",
        "web",
        "web_notify",
        "account",
        "sale_management", ],
    "category": "Uncategorized",
    "data": [
        'data/res_currency.xml',
        'security/security.xml',
        'views/res_currency_view.xml',
        'views/account_invoice_form.xml',
        'models/ir_cron.xml',
        'assets.xml'
    ],
    "qweb":[
        "static/src/xml/menu_exchange.xml"
    ],
    "external_dependencies": {"python": []}
}
