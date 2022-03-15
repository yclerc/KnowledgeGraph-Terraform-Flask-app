"""
Support functions for app.py
"""
from io import StringIO
import json
from urllib.parse import unquote_plus

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

from PyPDF2 import PdfFileReader

import spacy
import en_core_web_sm

import boto3
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

import dns


# Access to MongoDB Atlas cluster __________________
"""
url = "mongodb+srv://<PARAMETER1>:<PARAMETER2>@ycfilrouge.z8etj.mongodb.net/ycfilrouge?retryWrites=true&w=majority"
cluster=MongoClient(url, tlsCAFile=certifi.where())
mongo_db=cluster["arxiv"]
collection=mongo_db["arxiv-AI"]
"""
# _________________________________________________

# Access to AWS DynamoDB cluster  __________________

# client for connection to hosted DynamoDB on AWS
client = boto3.client("dynamodb", region_name="eu-west-3")

# cliient for connection to local DynamoDB
# client = boto3.client('dynamodb', endpoint_url="http://localhost:8000")

dynamoTableName = "arxivTable"
# __________________________________________________

# if owlready2 installed in C:/, avoids traceback on windows machines
import sys

sys.path.append("C:/")
# import owlready2
from owlready2 import *


# Helper function to recursive scan dynamodb, avoids 1Mb max response limit
def scanRecursive(tableName, **kwargs):
    """
    NOTE: Anytime you are filtering by a specific equivalency attribute such as id, name
    or date equal to ... etc., you should consider using a query not scan

    kwargs are any parameters you want to pass to the scan operation
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


def create_onto():
    """
    Create ontology architecture
    """
    onto = get_ontology(
        "http://fil_rouge/onto.owl/"
    )  # new ontology, chose an IRI
    with onto:
        # Define a Person
        class Person(Thing):  # class Person is a subclass of Thing
            pass
        # Define a Document
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
        # Define Author class
        class Author(Person):
            # as a Person who teaches some Course
            equivalent_to = [And([Person, makes.some(Document)])]
        # A Person can be referred in a Document
        class isReferredIn(Person >> Document):
            pass
        # Define Reference class
        class Reference(Person):
            # as a Person who teaches some Course
            equivalent_to = [And([Person, isReferredIn.some(Document)])]

    # create ontology file from instances in MongoDB Atlas.
    # instances=collection.find()
    # create ontology file from instances in AWS DynamoDB.
    instances = scanRecursive(dynamoTableName)

    for instance in instances:
        # loop in results from the query 
        # for each item, instanciate onto
        with onto:
            # tests:
            # use [] to avoid encoding issue with Protege
            # doc_name=str([instance['title']['S']])
            # print(instance['_id']['S'])
            # new_doc= Document(name=doc_name)

            doc_name = str(instance["_id"]["S"])
            new_doc = Document(name=doc_name)
            new_doc.has_title = [instance["title"]["S"]]
            for author in instance["Authors"]["SS"]:
                author_name = [str(author).replace("%20", " ")]
                new_author = Person(name=author_name)
                new_author.makes = [new_doc]
            for reference in instance["References"]["SS"]:
                ref_name = [str(reference).replace("%20", " ")]
                new_reference = Person(name=ref_name)
                new_reference.isReferredIn = [new_doc]
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
    """check if file already in DB. If yes, skip. Also return info in message"""
    """
    # to check on mongo Atlas DB 
    filter_dict = {"_id":arxiv_id}
    if collection.count_documents(filter_dict, limit = 1) != 0:
        return False
    else: return True
    """
    # to check on DynamoDB
    filter_dict = {"_id": {"S": arxiv_id}}
    resp = client.get_item(TableName=dynamoTableName, Key=filter_dict)
    item = resp.get("Item")
    if not item:
        return True
    else:
        return False


def process_arxiv_file(path, arxiv_id, title, authors_lst):
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
    nlp = en_core_web_sm.load()
    # nlp = spacy.load('en_core_web_sm')
    doc = nlp(content_ref)
    ref_lst = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            ref_lst.append(ent.text)

    # to remove duplicates
    ref_lst = list(dict.fromkeys(ref_lst))

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
    params = info + (str(ref_lst),)

    """
    # post to MongoDB
    post={
        "_id": arxiv_id,
        "title": title,
        "Authors": json.loads(authors_lst),
        "References": ref_lst
    }
    #collection.insert_one(post)
    """

    # post to DynamoDB
    post = {
        "_id": {"S": arxiv_id},
        "title": {"S": title},
        "Authors": {"SS": json.loads(authors_lst)},
        "References": {"SS": ref_lst},
    }
    resp = client.put_item(TableName=dynamoTableName, Item=post)

    return arxiv_id, params

"""
def db_size():
    #returns number of rows in table DOCUMENTS
    db = sqlite3.connect("Documents.sqlite")
    cur = db.cursor()
    cur.execute("select * from DOCUMENTS")
    return len(cur.fetchall())
"""

"""
def extract_info(doc_id):
    "extracts info columns from select row in DB
    db = sqlite3.connect("Documents.sqlite")
    cur = db.cursor()
    cur.execute(
        "select title, author, producer, subject, pages \
                from DOCUMENTS WHERE id=(?)",
        (doc_id,),
    )
    output = cur.fetchall()
    return output
"""

"""
def extract_content(doc_id):
    "extract "content" column from select row in DB
    db = sqlite3.connect("Documents.sqlite")
    cur = db.cursor()
    cur.execute("select content from DOCUMENTS WHERE id=(?)", (doc_id,))
    output = cur.fetchall()
    return output
"""

"""
def process_file(path):
    #extract necessary data and execute sql query for given file
    #use function defined above to get content of pdf file
    #use PyPDF2 to get metadata
    
    db = sqlite3.connect("Documents.sqlite")
    cur = db.cursor()
    content = convert_pdf_to_txt(path)
    with open(path, "rb") as file:
        pdf = PdfFileReader(file)
        doc_info = pdf.getDocumentInfo()
        info = (
            doc_info.title,
            doc_info.author,
            doc_info.producer,
            doc_info.subject,
            pdf.getNumPages(),
        )
    params = info + (str(content),)
    cur.execute(
        "insert into DOCUMENTS \
    (title,author,producer,subject,pages,content) \
    VALUES (?, ?, ?, ?, ?, ?)",
        params,
    )
    doc_id = cur.lastrowid
    db.commit()
    return doc_id, params
"""

