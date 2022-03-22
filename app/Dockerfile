
FROM python:3.8-slim as builder
ADD . /pdfextract
WORKDIR /pdfextract
RUN python3 --version

#preinstall spacy and model to avoid crashing container image
RUN pip install -U spacy
RUN python -m spacy download en_core_web_sm
#RUN python -m spacy download en_core_web_trf

# to get other requirements
RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["python", "app.py"]

# execute the script:
CMD [ "python", "app.py" ]


# FROM public.ecr.aws/lambda/python:3.8 #traceback on requirements.txt
# FROM python:3.8-slim #traceback container run cannot find arxiv
