
# KnowledgeGraph-Terraform-Flask-app

- _Author:_ [Yann CLERC](https://github.com/yclerc)
- _Description:_ Deployment framework to AWS for secure, autoscaling, High-Availability microservices
- _Provided microservice:_ In this example, we use an API generating Knowledge Graphs from [arxiv.org](https://arxiv.org)
- _Use:_
    * with provided flask app, no modifications required 
    * with your own flask app
        - replace the content of folder [./app/](./app/) by your own miscroservice
        - update requirements.txt
        - update Dockerfile
        - update terraform files config.tf and variables.tf
        - That's it ! :)






---
**Table of Contents**  
- [General info](#general-info)
- [Install](#install)
  - [Quickstart](#quickstart)
  - [Select endpoint for database](#select-endpoint-for-database)
  - [Launch microservice on localhost](#launch-microservice-on-localhost)
  - [Docker locally](#docker-locally)
- [Deploy with IaaC](#deploy-with-iaac)
  - [Docker push to AWS](#docker-push-to-aws)
  - [Deploy Terraform plan](#deploy-terraform-plan)
  - [Remove deployed architecture](#remove-deployed-architecture)
- [Use](#use)
  - [API manager](#api-manager)
  - [Routes definition](#routes-definition)
  - [Test](#test)
  - [Work with generated ontology](#work-with-generated-ontology)
 

---
**To Do (dev):** 
- document API with swagger / others
- update routes definitions in README.md
- perform large batch from local to AWS DB endpoint
- create route to show what is already in DB -- Nice To Have
- onto url with arxiv id instead of title --> Done
- clean code --> Done
- delete downloaded files --> Done
- route to add by arxiv_ID --> Done
- push to github --> Done
---



# General info
This project deploys an API on AWS according to the following workflow:
![devops](./images/devops.png)
	



# Install

## Quickstart

This package requires python 3 (including venv), git and a recent OS.

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

## Select endpoint for database

Various DB available: 

    - local DynamoDB, for integration testing
    - hosted MongoDB Atlas DB, initial choice to expose the API (ask admin for credentials)
    - hosted AWS DynamoDB, for production 

Select chosen option by commenting/uncommenting related lines in [models/model.py](./app/models/model.py)

If you wish to use a local DynamoDB, you should configure it using the following commands:
Refer to this [tutorial](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) for details.


    $ aws dynamodb create-table     --table-name arxivTable     --attribute-definitions AttributeName=_id,AttributeType=S --key-schema AttributeName=_id,KeyType=HASH     --billing-mode PAY_PER_REQUEST --endpoint-url http://localhost:8000

If needed, you can destroy the table using the command: 

    $ aws dynamodb delete-table --table-name arxivTable --endpoint-url http://localhost:8000

## Launch microservice on localhost

    $ cd app/
    $ python app.py

Open http://localhost:5000 in a browser to interact with the API 


## Docker locally

build and run container using following commands.


    $ docker build -t KnowledgeGraph-Terraform-Flask-app .
    $ docker run -d -p 5000:5000 KnowledgeGraph-Terraform-Flask-app
    $ curl http://localhost:5000


# Deploy with IaaC

Resulting architecture generated in AWS :
![Flask-Microservice](./images/Flask-Microservice.png)

Refer to this [tutorial](https://aws.amazon.com/blogs/opensource/deploying-python-flask-microservices-to-aws-using-open-source-tools/) to get more details. Use commands below to ensure proper deployment.


## Docker push to AWS
---
**NB:** 
This step assumes you already have a configured programatic access to an active AWS account 

---

Create repository on AWS ECR:

    $ aws ecr create-repository --repository-name KnowledgeGraph-Terraform-Flask-app --image-scanning-configuration scanOnPush=true --region eu-west-3 


Get credentials:

    $ aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin <AWS ID>.dkr.ecr.eu-west-3.amazonaws.com/KnowledgeGraph-Terraform-Flask-app

From your browser open the AWS Console, open Services, Elastic Container Registry. 

Select the KnowledgeGraph-Terraform-Flask-app. The ECR URI will be needed later on.

Log into the ECR service of your AWS account (use your own AWS_ID):

    $ aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin <AWS_ID>.dkr.ecr.eu-west-3.amazonaws.com/KnowledgeGraph-Terraform-Flask-app

Tag and push to ECR:

    $ docker tag KnowledgeGraph-Terraform-Flask-app:latest <AWS_ID>.dkr.ecr.eu-west-3.amazonaws.com/KnowledgeGraph-Terraform-Flask-app:latest

    $ docker push <AWS_ID>.dkr.ecr.eu-west-3.amazonaws.com/KnowledgeGraph-Terraform-Flask-app:latest

## Deploy Terraform plan 


    $ cd ..
    $ cd  /terraform
    $ terraform init
---
The Terraform code will deploy the following configuration:
- IAM: Identity access management policy configuration
- VPC: Public and private subnets, routes, and a NAT Gateway
- EC2: Autoscaling implementation
- ECS: Cluster configuration
- ALB: Load balancer configuration
- DynamoDB: Table configuration
- CloudWatch: Alert metrics configuration
---


    # check configuration files:
    $ terraform validate 

    # prepare and print execution plan:
    # this command prompts for a valid ECR URI (see) AWS console)
    $ terraform plan  
    
    # deploy plan to AWS:
    $ terraform apply 



## Remove deployed architecture 

Delete the API completely from AWS: 

    $ terraform destroy

You can finally delete the ECR registry directly from your browser in AWS console. 



# Use

## API manager 




## Routes definition

### Upload a file

Post a file to the server:

**Request through web UI**

    HTTP Method: POST
    Route: /

**Request using curl**

    HTTP Method: POST
    Route: /upload
    
    $ curl POST -F file=@"./uploads/test.pdf" localhost:5000/upload

NB: for Windows users, in case of error, remove aliase for curl using the following command:

    $ Remove-item alias:curl


### Check an uploaded file

Get the status of an uploaded file and show his meta data:

**Request**

    HTTP Method: GET
    Route: /documents/<id>
    # Replace <id> by ID of the chosen document
    # The ID was returned in response of an upload file request

    $ curl localhost:5000/documents/1

### Text of an uploaded file

Get content of an uploaded file:

**Request**

    HTTP Method: GET
    Route: /text/<id>
    # Replace <id> by ID of the chosen document
    # The ID was returned in response of an upload file request

    $ curl localhost:5000/text/1


## Test

### black
Clean code automatically on app files by using black package:


    $ black <file_path> 

### pylint

    $ python -m pylint <filename>.py

### pytest

    $ python -m pytest




## Work with generated ontology 















