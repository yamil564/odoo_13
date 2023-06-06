from .Accounting import AdditionalAccountID, CustomerAssignedAccountID
from .Party import Party
from .util import Xmleable, default_document


class AccountingSupplierParty(Xmleable):
    def __init__(self, party, customer_assigned_account=None,
                 additional_account=None):
        self.party = party
        self.customer_assigned_accountID = customer_assigned_account
        self.additional_accountID = additional_account

    def fix_values(self):
        if type(self.customer_assigned_accountID) == str:
            self.customer_assigned_accountID = CustomerAssignedAccountID(self.customer_assigned_accountID)
        if type(self.additional_accountID) == str:
            self.additional_accountID = AdditionalAccountID(self.additional_accountID)

    def validate(self, errs, obs):
        assert type(self.party) == Party
        if self.customer_assigned_accountID:
            assert type(self.customer_assigned_accountID) == CustomerAssignedAccountID
        if self.additional_accountID:
            assert type(self.additional_accountID) == AdditionalAccountID

    def generate_doc(self):
        self.doc = default_document.createElement("cac:AccountingSupplierParty")
        if self.customer_assigned_accountID:
            self.doc.appendChild(self.customer_assigned_accountID.get_document())
        if self.additional_accountID:
            self.doc.appendChild(self.additional_accountID.get_document())
        self.doc.appendChild(self.party.get_document())


class DespatchSupplierParty(Xmleable):
    def __init__(self, customer_assigned_account=None, party=None):
        self.customer_assigned_accountID = customer_assigned_account
        self.party = party

    def fix_values(self):
        if type(self.customer_assigned_accountID) == str:
            self.customer_assigned_accountID = CustomerAssignedAccountID(self.customer_assigned_accountID)

    def validate(self, erros, observs):
        assert type(self.customer_assigned_accountID) is CustomerAssignedAccountID
        assert type(self.party) is Party

    def generate_doc(self):
        self.doc = default_document.createElement("cac:DespatchSupplierParty")
        if self.customer_assigned_accountID:
            self.doc.appendChild(self.customer_assigned_accountID.get_document())
        self.doc.appendChild(self.party.get_document())


class SellerSupplierParty(Xmleable):
    def __init__(self, customer_assigned_account=None, party=None):
        self.customer_assigned_accountID = customer_assigned_account
        self.party = party

    def fix_values(self):
        if type(self.customer_assigned_accountID) == str:
            self.customer_assigned_accountID = CustomerAssignedAccountID(self.customer_assigned_accountID)

    def validate(self, erros, observs):
        assert type(self.customer_assigned_accountID) is CustomerAssignedAccountID
        assert type(self.party) is Party

    def generate_doc(self):
        self.doc = default_document.createElement("cac:SellerSupplierParty")
        if self.customer_assigned_accountID:
            self.doc.appendChild(self.customer_assigned_accountID.get_document())
        self.doc.appendChild(self.party.get_document())
