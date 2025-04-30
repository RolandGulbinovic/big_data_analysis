# Assignment 2 - Docker

Ran everything on Linux (Ubuntu). To download and install Docker I ran - `sudo apt install docker.io`

## Python code:
For this I created a very simple python script that takes a _.json_ file with information about movies from the last ~110 years and provides some quick summaries for each decade.
The script works like this:
- Cleans entries with missing cast or genre
- Calculates top actor and director for each decade
- Print results
- Saves results as:
  - _summary.json_
  - _summary.csv_
    
All output is saved directly to the current working directory.


The script is very simple because the main idea of the task was to implement containerisation using Docker.


## requirements.csv
The script imports a couple libraries - `json`, `os`, `collections`,  `pandas`. The only library that needs to be added to _requirements.csv_ is `pandas`, because it isn't included in base python.



## Dockerfile
The Dockerfile is pretty standard - the main lines are:

`RUN pip install --no-cache-dir -r requirements.txt` - Installs the packages (`pandas`)

`WORKDIR /app` - set work directory

Then we also copy the files that we want to be in our docker container:

`COPY requirements.txt .` - libraries

`COPY main.py .` - python script

`COPY data/ /app/data/` - folder with our input data


Then we show what to run when starting the container (our python script)
`CMD ["python", "your_script_name.py"]`

## Building docker image
1. First we build the docker image:

`docker build -t rgulbinovic/movie-summary .`

2. Run the container to see if it works:

`docker run -v $(pwd):/app rgulbinovic/movie-summary`

3. Push to dockerhub:

`docker login` - login to docker

`docker tag rgulbinovic/movie-summary rgulbinovic/movie-summary` - Add a tag to the image

`docker push rgulbinovic/movie-summary` - push it to dockerhub

To pull the docker image

`docker pull rgulbinovic/movie-summary`







