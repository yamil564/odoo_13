{
    'name': 'Sale Order Payment Status',
    'summary': 'Show Payment Status on Sale Order Tree and Sale Order Form. Do a payment on Sale Order Form',
    'description': 'Show Payment Status on Sale Order Tree and Sale Order Form. Do a payment on Sale Order Form',
    'author': "Sonny Huynh",
    'category': 'Sales',
    'version': '0.1',
    'depends': ['sale'],

    'data': [
        'views/form_view.xml',
        'views/assets.xml',
    ],
    'qweb': [
        "static/src/xml/account_payment.xml",
        "static/src/xml/badge.xml",
    ],
    # only loaded in demonstration mode
    'demo': [],
    'images': [
        'static/description/banner.png',
    ],
    'license': 'OPL-1',
    'price': 65.00,
    'currency': 'EUR',
}