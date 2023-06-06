from .util import Xmleable, default_document
from .Party import Party
from .Accounting import AdditionalAccountID, CustomerAssignedAccountID


class AccountingCustomerParty(Xmleable):
    def __init__(self, party=None, customer_assigned_account=None, additional_account=None):
        self.party = party
        self.customer_assigned_accountID = customer_assigned_account
        self.additional_accountID = additional_account

    def validate(self, errs, obs):
        assert self.party is None or type(self.party) == Party
        assert self.customer_assigned_accountID is None or \
            type(self.customer_assigned_accountID) == CustomerAssignedAccountID
        assert self.additional_accountID is None or \
            type(self.additional_accountID) == AdditionalAccountID

    def generate_doc(self):
        self.doc = default_document.createElement(
            "cac:AccountingCustomerParty")
        if self.customer_assigned_accountID:
            self.doc.appendChild(
                self.customer_assigned_accountID.get_document())
        if self.additional_accountID:
            self.doc.appendChild(self.additional_accountID.get_document())
        if self.party:
            self.doc.appendChild(self.party.get_document())


class DeliveryCustomerParty(Xmleable):
    def __init__(self, party=None, customer_assigned_account=None):
        self.party = party
        self.customer_assigned_accountID = customer_assigned_account

    def validate(self, errs, obs):
        assert self.party is None or type(self.party) == Party
        assert self.customer_assigned_accountID is None or \
            type(self.customer_assigned_accountID) == CustomerAssignedAccountID

    def generate_doc(self):
        self.doc = default_document.createElement("cac:DeliveryCustomerParty")
        if self.customer_assigned_accountID:
            self.doc.appendChild(
                self.customer_assigned_accountID.get_document())
        if self.party:
            self.doc.appendChild(self.party.get_document())
