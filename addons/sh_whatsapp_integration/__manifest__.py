# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name" : "All in one WhatsApp Integration-Sales, Purchase, Account and CRM",
    "author" : "Softhealer Technologies",
    "website": "http://www.softhealer.com",
    "support": "support@softhealer.com",    
    "category": "Extra Tools",
    "summary": "Whatsapp Integration App,  Invoice To Customer Whatsapp Module, stock whatsup Whatsapp, Sales Whatsapp App, Purchase Whatsapp, CRM Whatsapp, invoice whatsapp, inventory whatsapp, account whatsup Odoo",
    "description": """Using this module you can send Quotations, Sale Order, Invoices, Bills, RFQs, Purchase Orders, and direct to Clients/Vendor's WhatsApp. You can easily send PDF of sale, purchase, invoice & inventory documents using URL.
 All In One Whatsapp Integration - Sales, Purchase, Account, CRM Odoo. """,        
    "version":"13.0.8",
    "depends" : ['crm','sale_management','purchase','stock'],
    "application" : True,
    "data" : [
            "data/sale_email_data.xml",
            'security/whatsapp_security.xml',
            "wizard/send_whatsapp_message_view.xml",
            "views/res_partner_views.xml",
            "wizard/send_whasapp_number_view.xml",
            
            "views/crm_lead_inherit_views.xml",
            "views/sale_order_inherit_view.xml",
            "views/purchase_order_inherit_view.xml",
            "views/customer_invoice_inherit_view.xml",
            "views/customer_delivery_inherit_view.xml",
            "views/res_config_settings.xml",
            "views/res_users_inherit_view.xml",
            "views/account_payment_inherit_view.xml",
            ],            
    "images": ["static/description/background.png",],  
    "live_test_url": "https://www.youtube.com/watch?v=qsbWdscnly0&feature=youtu.be",            
    "auto_install":False,
    "installable" : True,
    "price": 45,
    "currency": "EUR"   
}
