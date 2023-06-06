{
    'name': 'Sale / Invoice Ticket',
    'version': '1.0',
    'description': 'Sale / Invoice ticket de BigOdoo',
    'summary': 'Sale / Invoise ticket de BigOdoo',
    'author': 'BigOdoo',
    'website': 'https://bigodoo.com',
    'license': 'LGPL-3',
    'category': 'Sale / Invoice',
    'depends': [
        'account', 'sale', 'gestionit_pe_fe'
    ],
    'data': [
        'views/assets.xml',
        'views/ticket_view.xml',
    ],
    # 'demo': [
    #     ''
    # ],
    'qweb': ["static/src/xml/invoice_ticket.xml"],
    'installable': True,
    'application': True,
}
