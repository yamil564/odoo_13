
from lxml import etree


def validate_xsd(xsd_file_path, xml_doc):
    xsd_tree = etree.parse(xsd_file_path)
    xml_tree = etree.fromstring(xml_doc)

    schema = etree.XMLSchema(xsd_tree)

    return schema.validate(xml_tree)
