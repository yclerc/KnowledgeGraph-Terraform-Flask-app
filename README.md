# KnowledgeGraph-Terraform-Flask-app

API to generate Knowledge Graphs from scientic documents hsting platforme arxiv.org


## To Do: 
    - update README
    - route to show what is already in DB
    - large batch from local to AWS DB endpoint
    - document API with swagger 
    - ______
    - onto url with arxiv id instead of title --> Done
    - clean code --> Done
    - delete downloaded files --> Done
    - route to add by arxiv_ID --> Done
    - push to github --> Done


# Install

## Dependencies

This package requires python 3 (including venv), git and a recent OS


## KnowledgeGraph-Terraform-Flask-app

Clone and go to the newly created repository :

    $ git clone <https address>
    $ cd KnowledgeGraph-Terraform-Flask-app

Create a virtualenv and activate it: (here our venv is called "deploy")

    $ python -m venv deploy
    $ source deploy/bin/activate

Or on Windows cmd:

    $ python -m venv deploy
    $ deploy\Scripts\activate

Install requirements from txt file:

    $ pip install -r requirements.txt

# Run

    $ python app.py

Open http://localhost:5000 in a browser to try the software

## API specification

### Upload a file

Post a file to the server:

**Request**

    HTTP Methode: POST
    Route: /

### Check an uploaded file

Get the status of an uploaded file and show his meta data:

**Request**

    HTTP Methode: GET
    Route: /documents/<id>
    # Replace <id> by ID of the chosen document
    # The ID was returned in response of an upload file request

### Text of an uploaded file

Get content of an uploaded file:

**Request**

    HTTP Methode: GET
    Route: /text/<id>
    # Replace <id> by ID of the chosen document
    # The ID was returned in response of an upload file request

# Test
### pylint

    $ python -m pylint <filename>.py

### pytest

    $ python -m pytest

# Docker
    $ docker build -t KnowledgeGraph-Terraform-Flask-app .
    $ docker run -d -p 5000:5000 KnowledgeGraph-Terraform-Flask-app
    $ curl http://localhost:5000


# Docker push to AWS
    $ aws ecr create-repository --repository-name KnowledgeGraph-Terraform-Flask-app --image-scanning-configuration scanOnPush=true --region eu-west-3 

    $ aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 327059905592.dkr.ecr.eu-west-3.amazonaws.com/flask-docker-demo-app

# local Dynamo

    $ aws dynamodb create-table     --table-name arxivTable     --attribute-definitions AttributeName=_id,AttributeType=S                 --key-schema AttributeName=_id,KeyType=HASH     --billing-mode PAY_PER_REQUEST --endpoint-url http://localhost:8000

    $ aws dynamodb delete-table --table-name arxivTable --endpoint-url http://localhost:8000
