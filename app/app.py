"""
Flask app and routes creation
"""
import os
import json
import arxiv
from flask import Flask, request, redirect, url_for
from flask import render_template
from flask import Flask, send_from_directory
from werkzeug.utils import secure_filename
from models import model

# create folder for uploaded pdf files in current directory
UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__)) + "/uploads/"
DOWNLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__)) + "/downloads/"
ALLOWED_EXTENSIONS = {"pdf"}

# Flask app
app = Flask(__name__)

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER


@app.route("/")
def hello():
    status=model.AWS_db_check()
    if status == -1:
        json_output = {"Microservice Status": "DOWN", "Error Message":"Failed to connect to a database","API specifications": "https://documenter.getpostman.com/view/20033934/UVsLS6ja"}
        return json_output, 400
    json_output = {"Microservice Status": "UP", "Number of files in database":status,"API specifications": "https://documenter.getpostman.com/view/20033934/UVsLS6ja"}
    return json_output, 200


@app.route("/arxiv/unit/<input_arxiv_id>", methods=["GET", "POST"])
def unit_populate_from_arxiv(input_arxiv_id):

    #try:
        search = arxiv.Search(id_list=[input_arxiv_id])
        result = next(search.results())
        # initialize variables
        lst = []
        file_id = 0
        arxiv_id = result.get_short_id()

        # scan for existing documents in DB
        if model.arxiv_db_check(arxiv_id):
            file_name = "arxiv_downloaded_" + str(file_id) + ".pdf"
            result.download_pdf(dirpath="./downloads", filename=file_name)
            file_path = "./downloads/" + file_name

            authors_lst = []
            for author in result.authors:
                authors_lst.append(str(author))
                # print("Author: ", author)
            authors_lst = json.dumps(authors_lst)
            # path, title authors
            info = model.process_arxiv_file(
                file_path, arxiv_id, result.title, authors_lst
            )
            lst.append({"Title": result.title, "URI": result.pdf_url})
            file_id += 1
            os.remove(file_path)
            json_output = {"Files added": file_id, "Details": lst}
            return json_output, 200

        else:
            json_output = {
                "Files added": 0,
                "Response": "This file is already stored in the database",
            }
            return json_output, 400
    # except:
    #     json_output = {
    #         "Files added": 0,
    #         "Response": "It seems the ID you entered is not valid. Please consider using an accurate arxiv ID such as 2102.04706 or 2102.04706v1",
    #     }
    #     return json_output, 400


@app.route("/arxiv/batch/<int:batch_size>", methods=["GET", "POST"])
def batch_populate_from_arxiv(batch_size):

    # 3 min runtime on MacPro for 20 files. Check multi-threading to increase perf ??
    # generate guidance message

    #try:
        # search for selected query, returns latest documents related to the query from arxiv 
        search = arxiv.Search(
            query="Computer Science & AI",
            max_results=batch_size,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        # this flexibility allows for future improvements. 
        # use case: Have the API manage several knowledge tables to generate ontologies on various queries 

        # initialize variables
        lst = []
        file_id = 0

        # Download PDF to a specified directory with a custom filename.
        for result in search.results():
            # to get unique id from arxiv uri
            arxiv_id = result.get_short_id()

            # scan for existing documents in DB
            if model.arxiv_db_check(arxiv_id):
                file_name = "arxiv_downloaded_" + str(file_id) + ".pdf"
                result.download_pdf(dirpath="./downloads", filename=file_name)
                file_path = "./downloads/" + file_name

                authors_lst = []
                for author in result.authors:
                    authors_lst.append(str(author))
                    # print("Author: ", author)
                authors_lst = json.dumps(authors_lst)
                # path, title authors
                info = model.process_arxiv_file(
                    file_path, arxiv_id, result.title, authors_lst
                )
                lst.append({"Title": result.title, "URI": result.pdf_url})
                file_id += 1
                os.remove(file_path)
        json_output = {"Files added": file_id, "Details": lst , "Response":"If 0 files were added, the database is already up to date with latest documents from arxiv. In this case, batch requests are not allowed. Please consider uploading specific documents through the /arxiv/unit/<input_arxiv_id> method"}
        return json_output, 200

    # except:
    #     json_output = {
    #         "Files added": 0,
    #         "Response": "It seems your request has exceeded currently allowed network capabilities. Please consider using a smaller batch size or uploading specific documents through the /arxiv/unit/<input_arxiv_id> method",
    #     }
    #     return json_output, 500

@app.route("/onto/", methods=["GET"])
def get_onto():
    """to serve onto generated from DB"""
    path = ""
    world = model.create_onto()
    return send_from_directory("ontologies", "world.owl"), 200

"""
@app.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    #to get metadata of specific documents
    if request.method == "GET":
        if doc_id < 1 or doc_id > model.db_size():
            json_output = {"Text ID": "Invalid ID", "Meta Data": "No data"}
            return json_output, 400
        else:
            output = model.extract_info(doc_id)
            json_output = {
                "Text ID": doc_id,
                "Meta Data": {
                    "Title": output[0][0],
                    "Author": output[0][1],
                    "Producer": output[0][2],
                    "Subject": output[0][3],
                    "Pages": output[0][4],
                },
            }
            # print(json_output)
            return json_output, 200
"""

"""
@app.route("/text/<int:doc_id>", methods=["GET"])
def get_text(doc_id):
    #to get content of specific file
    
    if request.method == "GET":
        if doc_id < 1 or doc_id > model.db_size():
            json_output = {"Text ID": "Invalid ID", "Content": "No data"}
            return json_output, 400
        else:
            output = model.extract_content(doc_id)
            output_str = str(output[0][0])
            json_output = {"Text ID": doc_id, "Content": output_str}
            # print(json_output)
            return json_output, 200
"""
if __name__ == "__main__":
    app.run(threaded=True, host="0.0.0.0", port=5000)
