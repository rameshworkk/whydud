eploy@whydud-primary:/opt/whydud/whydud$ nano /opt/whydud/whydud/docker/certs/origin.pem
deploy@whydud-primary:/opt/whydud/whydud$ nano /opt/whydud/whydud/docker/certs/origin-key.pem
deploy@whydud-primary:/opt/whydud/whydud$ chmod 600 /opt/whydud/whydud/docker/certs/origin-key.pem
deploy@whydud-primary:/opt/whydud/whydud$ cd /opt/whydud/whydud
git pull origin master
docker compose -f docker-compose.primary.yml build backend
docker compose -f docker-compose.primary.yml up -d
From github.com:rameshworkk/whydud
 * branch            master     -> FETCH_HEAD
Already up to date.
[+] Building 1.9s (17/17) FINISHED                                                                                                                                                        
 => [internal] load local bake definitions                                                                                                                                           0.0s
 => => reading from stdin 547B                                                                                                                                                       0.0s
 => [internal] load build definition from backend.Dockerfile                                                                                                                         0.0s
 => => transferring dockerfile: 2.25kB                                                                                                                                               0.0s
 => [internal] load metadata for docker.io/library/python:3.12-slim                                                                                                                  1.3s
 => [internal] load .dockerignore                                                                                                                                                    0.0s
 => => transferring context: 2B                                                                                                                                                      0.0s
 => [base 1/3] FROM docker.io/library/python:3.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c                                                       0.0s
 => [internal] load build context                                                                                                                                                    0.1s
 => => transferring context: 15.57kB                                                                                                                                                 0.0s
 => CACHED [base 2/3] WORKDIR /app                                                                                                                                                   0.0s
 => CACHED [base 3/3] RUN apt-get update && apt-get install -y --no-install-recommends     libpq-dev     gcc     g++     libffi-dev     curl     && rm -rf /var/lib/apt/lists/*      0.0s
 => CACHED [deps 1/4] COPY backend/requirements/base.txt requirements/base.txt                                                                                                       0.0s
 => CACHED [deps 2/4] COPY backend/requirements/prod.txt requirements/prod.txt                                                                                                       0.0s
 => CACHED [deps 3/4] RUN pip install -r requirements/prod.txt                                                                                                                       0.0s
 => CACHED [deps 4/4] RUN python -m spacy download en_core_web_sm                                                                                                                    0.0s
 => CACHED [production 1/3] COPY backend/ .                                                                                                                                          0.0s
 => CACHED [production 2/3] RUN DJANGO_SECRET_KEY=build-only-collectstatic-key     python manage.py collectstatic --no-input --settings=whydud.settings.prod                         0.0s
 => CACHED [production 3/3] RUN useradd --system --no-create-home whydud                                                                                                             0.0s
 => exporting to image                                                                                                                                                               0.0s
 => => exporting layers                                                                                                                                                              0.0s
 => => writing image sha256:4da759c6cb755177de94f78f13d07539b95a0fb22c2f462e28ff7be3cf8c0552                                                                                         0.0s
 => => naming to docker.io/library/whydud-backend                                                                                                                                    0.0s
 => resolving provenance for metadata file                                                                                                                                           0.1s
[+] build 1/1
 ✔ Image whydud-backend Built                                                                                                                                                         2.1s
[+] up 8/8
 ✔ Container whydud-meilisearch   Healthy                                                                                                                                             0.5s
 ✔ Container whydud-redis         Healthy                                                                                                                                             0.5s
 ✔ Container whydud-postgres      Healthy                                                                                                                                             0.5s
 ✔ Container whydud-backend       Running                                                                                                                                             0.0s
 ✔ Container whydud-celery-worker Running                                                                                                                                             0.0s
 ✔ Container whydud-frontend      Running                                                                                                                                             0.0s
 ✔ Container whydud-caddy         Running                                                                                                                                             0.0s
 ✔ Container whydud-celery-beat   Running                                                                                                                                             0.0s
deploy@whydud-primary:/opt/whydud/whydud$ docker compose -f docker-compose.primary.yml logs backend --tail=100
whydud-backend  |     response = self.process_request(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/middleware/common.py", line 48, in process_request
whydud-backend  |     host = request.get_host()
whydud-backend  |            ^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/http/request.py", line 202, in get_host
whydud-backend  |     raise DisallowedHost(msg)
whydud-backend  | django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | 172.18.0.6 - - [02/Mar/2026:18:54:53 +0000] "GET /api/v1/trending/products HTTP/1.1" 400 143 "-" "node"
whydud-backend  | 172.18.0.6 - - [02/Mar/2026:18:54:53 +0000] "GET /api/v1/trending/price-dropping HTTP/1.1" 400 143 "-" "node"
whydud-backend  | Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | Traceback (most recent call last):
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/core/handlers/exception.py", line 55, in inner
whydud-backend  |     response = get_response(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/utils/deprecation.py", line 119, in __call__
whydud-backend  |     response = self.process_request(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/middleware/common.py", line 48, in process_request
whydud-backend  |     host = request.get_host()
whydud-backend  |            ^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/http/request.py", line 202, in get_host
whydud-backend  |     raise DisallowedHost(msg)
whydud-backend  | django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | 172.18.0.6 - - [02/Mar/2026:18:58:06 +0000] "GET /api/v1/products?category=smartphones HTTP/1.1" 400 143 "-" "node"
whydud-backend  | Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | Traceback (most recent call last):
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/core/handlers/exception.py", line 55, in inner
whydud-backend  |     response = get_response(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/utils/deprecation.py", line 119, in __call__
whydud-backend  |     response = self.process_request(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/middleware/common.py", line 48, in process_request
whydud-backend  |     host = request.get_host()
whydud-backend  |            ^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/http/request.py", line 202, in get_host
whydud-backend  |     raise DisallowedHost(msg)
whydud-backend  | django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | 172.18.0.6 - - [02/Mar/2026:18:58:06 +0000] "GET /api/v1/products HTTP/1.1" 400 143 "-" "node"
whydud-backend  | 172.18.0.6 - - [02/Mar/2026:18:58:06 +0000] "GET /api/v1/deals HTTP/1.1" 400 143 "-" "node"
whydud-backend  | Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | Traceback (most recent call last):
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/core/handlers/exception.py", line 55, in inner
whydud-backend  |     response = get_response(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/utils/deprecation.py", line 119, in __call__
whydud-backend  |     response = self.process_request(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/middleware/common.py", line 48, in process_request
whydud-backend  |     host = request.get_host()
whydud-backend  |            ^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/http/request.py", line 202, in get_host
whydud-backend  |     raise DisallowedHost(msg)
whydud-backend  | django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | Traceback (most recent call last):
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/core/handlers/exception.py", line 55, in inner
whydud-backend  |     response = get_response(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/utils/deprecation.py", line 119, in __call__
whydud-backend  |     response = self.process_request(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/middleware/common.py", line 48, in process_request
whydud-backend  |     host = request.get_host()
whydud-backend  |            ^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/http/request.py", line 202, in get_host
whydud-backend  |     raise DisallowedHost(msg)
whydud-backend  | django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | 172.18.0.6 - - [02/Mar/2026:18:58:06 +0000] "GET /api/v1/trending/products HTTP/1.1" 400 143 "-" "node"
whydud-backend  | Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | Traceback (most recent call last):
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/core/handlers/exception.py", line 55, in inner
whydud-backend  |     response = get_response(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/utils/deprecation.py", line 119, in __call__
whydud-backend  |     response = self.process_request(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/middleware/common.py", line 48, in process_request
whydud-backend  |     host = request.get_host()
whydud-backend  |            ^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/http/request.py", line 202, in get_host
whydud-backend  |     raise DisallowedHost(msg)
whydud-backend  | django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | 172.18.0.6 - - [02/Mar/2026:18:58:06 +0000] "GET /api/v1/trending/price-dropping HTTP/1.1" 400 143 "-" "node"
whydud-backend  | Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | Traceback (most recent call last):
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/core/handlers/exception.py", line 55, in inner
whydud-backend  |     response = get_response(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/utils/deprecation.py", line 119, in __call__
whydud-backend  |     response = self.process_request(request)
whydud-backend  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/middleware/common.py", line 48, in process_request
whydud-backend  |     host = request.get_host()
whydud-backend  |            ^^^^^^^^^^^^^^^^^^
whydud-backend  |   File "/usr/local/lib/python3.12/site-packages/django/http/request.py", line 202, in get_host
whydud-backend  |     raise DisallowedHost(msg)
whydud-backend  | django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'. You may need to add 'backend' to ALLOWED_HOSTS.
whydud-backend  | 172.18.0.6 - - [02/Mar/2026:19:01:25 +0000] "GET /api/v1/products HTTP/1.1" 400 143 "-" "node"
deploy@whydud-primary:/opt/whydud/whydud$ 