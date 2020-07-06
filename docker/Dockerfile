FROM python:3

WORKDIR /code

ADD ./all-requirements.txt ./all-requirements.txt
RUN pip install -r all-requirements.txt
ADD ./ ./
RUN pip install -r requirements.txt
