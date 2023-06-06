import sys

import traceback
from xml.dom import minidom

default_document = minidom.Document()


def createElementContent(name, content):
    if type(content) != str:
        content = str(content)
    ans = default_document.createElement(name)
    text = default_document.createTextNode(content)
    ans.appendChild(text)
    return ans


def createCDataContent(name, content):
    ans = default_document.createElement(name)
    text = default_document.createCDATASection(str(content))
    ans.appendChild(text)
    return ans


class Xmleable(object):
    doc = default_document.createTextNode("Empty")

    def fix_values(self):
        pass

    def generate_doc(self):
        pass

    def validate(self, erros, observs):
        pass

    def check_validation(self, errors, observs):
        try:
            self.fix_values()
        except Exception as e:
            errors.append({
                "code": 0,
                "detail": "Error fixing values on " + str(self.__class__) + ". " + str(e)
            })
        try:
            self.validate(errors, observs)
        except AssertionError:
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb)  # Fixed format
            tb_info = traceback.extract_tb(tb)
            filename, line, func, text = tb_info[-1]
            print('An error occurred on line {} in statement {}'.format(line, text))
        except Exception as e:
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb)  # Fixed format
            tb_info = traceback.extract_tb(tb)
            filename, line, func, text = tb_info[-1]
            print('An error occurred on line {} in statement {}'.format(line, text))
            errors.append({
                "code": 0,
                "detail": "Error validating errors on " + str(self.__class__) + ": " + str(e)
            })

        for _, v in self.__dict__.items():
            if v is None:
                continue
            if type(v) == list:
                for x in v:
                    if issubclass(x.__class__, Xmleable):
                        x.check_validation(errors, observs)
            elif issubclass(v.__class__, Xmleable):
                v.check_validation(errors, observs)

    def get_document(self):
        self.fix_values()
        self.generate_doc()
        return self.doc
