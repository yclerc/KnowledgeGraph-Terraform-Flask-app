"""
Support functions for app.py
"""

import sys

sys.path.append("C:/")
# if owlready2 installed in C:/, avoids traceback on windows machines
import json
from io import StringIO

# import owlready2
from owlready2 import *
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from PyPDF2 import PdfFileReader
import spacy
import en_core_web_sm

import boto3

# from boto3.dynamodb.types import TypeSerializer, TypeDeserializer


# Access to AWS DynamoDB cluster  __________________
# client for connection to hosted DynamoDB on AWS
client = boto3.client("dynamodb", region_name="eu-west-3")

# cliient for connection to local DynamoDB
# client = boto3.client("dynamodb", endpoint_url="http://localhost:8000")

dynamoTableName = "arxivTable"
# __________________________________________________


def scan_recursive(tableName, **kwargs):
    """
    Helper function to recursive scan dynamodb, avoids 1Mb max response limit
    """
    response = client.scan(TableName=tableName, **kwargs)
    if kwargs.get("Select") == "COUNT":
        return response.get("Count")
    data = response.get("Items")
    while "LastEvaluatedKey" in response:
        response = kwargs.get("table").scan(
            ExclusiveStartKey=response["LastEvaluatedKey"], **kwargs
        )
        data.extend(response["Items"])
    return data


def AWS_db_persisted_files():
    """
    Returns list of files already in DB.
    """
    file_lst = []
    instances = scan_recursive(dynamoTableName)
    for instance in instances:
        file_lst.append(instance["_id"]["S"])
    return file_lst


def AWS_db_check():
    """
    Returns number of items in DB or -1 if impossible to connect
    """
    try:
        count = scan_recursive(dynamoTableName, Select="COUNT")
        return count
    except:
        return -1


def create_onto():
    """
    Create ontology architecture.
    """
    onto = get_ontology("http://fil_rouge/onto.owl/")  # new ontology, chose an IRI
    with onto:

        class Person(Thing):
            # class Person is a subclass of Thing
            pass

        class Document(Thing):
            # subclass of not a Person
            is_a = [Not(onto.Person)]
            pass

        class has_title(Document >> str):
            # data property
            pass

        AllDisjoint([Person, Document])
        # A Person can make a document
        class makes(Person >> Document):
            pass

        class Author(Person):
            # as a Person who teaches some Course
            equivalent_to = [And([Person, makes.some(Document)])]

        class isReferredIn(Person >> Document):
            # A Person can be referred in a Document
            pass

        class Reference(Person):
            # as a Person referred in a document
            equivalent_to = [And([Person, isReferredIn.some(Document)])]

    # create ontology file from instances in AWS DynamoDB.
    instances = scan_recursive(dynamoTableName)
    for instance in instances:
        # loop in results from the query
        # for each item, instanciate onto
        with onto:
            doc_name = str(instance["_id"]["S"])
            new_doc = Document(name=doc_name)
            new_doc.has_title.append(instance["title"]["S"])
            for author in instance["Authors"]["SS"]:
                author_name = [str(author).replace("%20", " ")]
                #author_name = str(author).replace("%20", "_").replace(" ","_")
                #print(author_name)
                new_author = Person(name=author_name)
                new_author.makes.append(new_doc)
            for reference in instance["References"]["SS"]:
                ref_name = [str(reference).replace("%20", " ")]
                #ref_name = str(reference).replace("%20", "_").replace(" ","_")
                new_reference = Person(name=ref_name)
                new_reference.isReferredIn.append(new_doc)
    default_world.save(
        "./ontologies/world.owl"
    )  # generates ontology structure such as: <stud:Person rdf:about="http://students.org/alice">
    return default_world


def convert_pdf_to_txt(path):
    """get pdf content with pdfminer library"""
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, laparams=laparams)
    with open(path, "rb") as file:
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        password = ""
        maxpages = 0
        caching = True
        pagenos = set()
        for page in PDFPage.get_pages(
            file,
            pagenos,
            maxpages=maxpages,
            password=password,
            caching=caching,
            check_extractable=True,
        ):
            interpreter.process_page(page)
        text = retstr.getvalue()
    device.close()
    retstr.close()
    return text


def arxiv_db_check(arxiv_id):
    """check if file already in DB."""
    filter_dict = {"_id": {"S": arxiv_id}}
    resp = client.get_item(TableName=dynamoTableName, Key=filter_dict)
    item = resp.get("Item")
    if not item:
        return True
    else:
        return False


def process_arxiv_file(path, arxiv_id, title, authors_lst, post_trigger):
    """
    extracts necessary data and execute query for given arxiv file
    uses function defined above to get content of pdf file
    keeps text only after first occurence of word "REFERENCES"
    keeps all text in case REFERENCES cannot be found
    """
    # get full content
    content = convert_pdf_to_txt(path)
    # get references part only
    ref_position = content.find("REFERENCES")
    # in case references not found, keep all text
    if ref_position == -1:
        ref_position = content.find("References")
        if ref_position == -1:
            content_ref = content
        else:
            content_ref = content[ref_position:]
    else:
        content_ref = content[ref_position:]
    # to get named entities
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(content_ref)
    ref_lst = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            ref_lst.append(ent.text)
    # to remove duplicates
    ref_lst = list(dict.fromkeys(ref_lst))
    # Filter references based on exceptions
    exceptions = [
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "arxiv",
        ",",
        ":",
        "/",
        "]",
        "[",
        "\n",
        ">",
        "<",
        "ˇ",
    ]
    references = ref_lst
    filter_data = [x for x in references if all(y not in x for y in exceptions)]
    # Filter to keep only strings with a whitespace
    filter_data = [x for x in filter_data if " " in x]

    with open(path, "rb") as file:
        pdf = PdfFileReader(file)
        doc_info = pdf.getDocumentInfo()
        info = (
            arxiv_id,
            title,
            authors_lst,
            doc_info.producer,
            doc_info.subject,
            pdf.getNumPages(),
        )
    params = info + (filter_data,)
    if post_trigger == 1:
        # post to DynamoDB
        post = {
            "_id": {"S": arxiv_id},
            "title": {"S": title},
            "Authors": {"SS": json.loads(authors_lst)},
            "References": {"SS": filter_data},
        }
        resp = client.put_item(TableName=dynamoTableName, Item=post)
    return params
