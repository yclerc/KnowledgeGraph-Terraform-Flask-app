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

# Flask app
app = Flask(__name__)

@app.route("/")
def hello():
    status=model.AWS_db_check()
    if status == -1:
        json_output = {"Microservice Status": "DOWN", "Error Message":"Failed to connect to a database","API specifications": "https://documenter.getpostman.com/view/20033934/UVsLS6ja"}
        return json_output, 400
    json_output = {"Microservice Status": "UP", "Number of files in database":status,"API specifications": "https://documenter.getpostman.com/view/20033934/UVsLS6ja"}
    return json_output, 200

@app.route("/arxiv/test_nlp/", methods=["GET"])
def test_nlp():
    lst=[]
    test_lst=[2203.08617, 2203.08111, 2203.08015]
    for file_id in test_lst:
        search = arxiv.Search(id_list=[str(file_id)])
        result = next(search.results())
        file_name = "arxiv_downloaded_" + str(file_id) + ".pdf"
        result.download_pdf(dirpath="./downloads", filename=file_name)
        file_path = "./downloads/" + file_name
        authors_lst=['jean test']
        info = model.process_arxiv_file(
                file_path, file_id, result.title, authors_lst,0
            )
        file_ref_lst=info[6]
        with open('./tests/gt_texts/'+ str(file_id)+'.pdf.json', 'r') as json_file:
	        json_load = json.load(json_file)
        
        comparison = [value for value in file_ref_lst if value in json_load['named_entities']] 

        # score = true positives
        score= round(len(comparison)/len(json_load['named_entities']),2)
        #print(score*100)
        lst.append({"ID": str(file_id), "% true positives": score*100})
        os.remove(file_path)

    json_output={"Status": "Successfully performed reference tests", "Scores": lst}
    return json_output, 200

@app.route("/arxiv/unit/<input_arxiv_id>", methods=["GET"])
def unit_populate_from_arxiv(input_arxiv_id):
    try:
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
                file_path, arxiv_id, result.title, authors_lst,1
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
    except:
         json_output = {
             "Files added": 0,
             "Response": "It seems the ID you entered is not valid. Please consider using an accurate arxiv ID such as 2102.04706 or 2102.04706v1",
         }
         return json_output, 400

@app.route("/arxiv/batch/<int:batch_size>", methods=["GET"])
def batch_populate_from_arxiv(batch_size):

    # 3 min runtime on MacPro for 20 files. Check multi-threading to increase perf ??
    # generate guidance message

    try:
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

        #scan documents currently in DB
        file_lst = model.AWS_db_persisted_files()


        # Download PDF to a specified directory with a custom filename.
        for result in search.results():
            # to get unique id from arxiv uri
            arxiv_id = result.get_short_id()

            # to avoid persisting again files that are already in DB
            if (arxiv_id not in file_lst):
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
                    file_path, arxiv_id, result.title, authors_lst, 1
                )
                lst.append({"Title": result.title, "URI": result.pdf_url})
                file_id += 1
                os.remove(file_path)
        json_output = {"Files added": file_id, "Details": lst , "Response":"If 0 files were added, the database is already up to date with latest documents from arxiv. In this case, batch requests are not allowed. Please consider uploading specific documents through the /arxiv/unit/<input_arxiv_id> method"}
        return json_output, 200

    except:
        json_output = {
            "Files added": 0,
            "Response": "It seems your request has exceeded currently allowed network capabilities. Please consider using a smaller batch size or uploading specific documents through the /arxiv/unit/<input_arxiv_id> method",
        }
        return json_output, 500

@app.route("/onto/", methods=["GET"])
def get_onto():
    """to serve onto generated from DB"""
    path = ""
    world = model.create_onto()
    return send_from_directory("ontologies", "world.owl"), 200

if __name__ == "__main__":
    app.run(threaded=True, host="0.0.0.0", port=5000)
