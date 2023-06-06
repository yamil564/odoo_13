from .util import Xmleable, createElementContent


# Date types
class DateType(Xmleable):
    def __init__(self, date=None, element_name=None):
        self.date = date
        self.element_name = element_name

    def generate_doc(self):
        self.doc = createElementContent(self.element_name, self.date)


class IssueDate(DateType):
    def __init__(self, date):
        super(IssueDate, self).__init__(date, "cbc:IssueDate")


class ReferenceDate(DateType):
    def __init__(self, date):
        super(ReferenceDate, self).__init__(date, "cbc:ReferenceDate")


class DueDate(DateType):
    def __init__(self, due_date):
        super(DueDate, self).__init__(due_date, "cbc:DueDate")


class SimpleText(Xmleable):
    def __init__(self, text, elem_name, attrs=None):
        self.text = text
        self.elem_name = elem_name
        self.attrs = attrs

    def generate_doc(self):
        self.doc = createElementContent(self.elem_name, str(self.text))
        if self.attrs:
            for k, v in self.attrs.items():
                self.doc.setAttribute(k, v)
