deploy@whydud-replica:/opt/whydud/whydud$ docker compose -f docker-compose.replica.yml build
WARN[0000] /opt/whydud/whydud/docker-compose.replica.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Building 185.6s (23/30)                                                                                                                                                               
 => [internal] load local bake definitions                                                                                                                                           0.0s
 => => reading from stdin 1.64kB                                                                                                                                                     0.0s
 => [frontend internal] load build definition from frontend.Dockerfile                                                                                                               0.4s
 => => transferring dockerfile: 1.61kB                                                                                                                                               0.2s
 => [celery-scraping internal] load build definition from backend.Dockerfile                                                                                                         0.4s
 => => transferring dockerfile: 2.01kB                                                                                                                                               0.2s
 => [backend internal] load metadata for docker.io/library/python:3.12-slim                                                                                                          1.4s
 => [frontend internal] load metadata for docker.io/library/node:22-alpine                                                                                                           1.6s
 => [frontend internal] load .dockerignore                                                                                                                                           0.0s
 => => transferring context: 2B                                                                                                                                                      0.0s
 => [backend base 1/3] FROM docker.io/library/python:3.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c                                               0.0s
 => [celery-scraping internal] load build context                                                                                                                                    1.3s
 => => transferring context: 1.05MB                                                                                                                                                  1.1s
 => [frontend internal] load build context                                                                                                                                           1.1s
 => => transferring context: 1.19MB                                                                                                                                                  1.1s
 => [frontend base 1/2] FROM docker.io/library/node:22-alpine@sha256:e4bf2a82ad0a4037d28035ae71529873c069b13eb0455466ae0bc13363826e34                                                0.0s
 => CACHED [frontend base 2/2] WORKDIR /app                                                                                                                                          0.0s
 => CACHED [frontend builder 1/4] WORKDIR /app                                                                                                                                       0.0s
 => CACHED [frontend production 2/5] RUN addgroup --system --gid 1001 nodejs &&     adduser --system --uid 1001 nextjs                                                               0.0s
 => CACHED [celery-scraping base 2/3] WORKDIR /app                                                                                                                                   0.0s
 => CACHED [celery-scraping base 3/3] RUN apt-get update && apt-get install -y --no-install-recommends     libpq-dev     gcc     g++     libffi-dev     curl     && rm -rf /var/lib  0.0s
 => CACHED [celery-scraping deps 1/4] COPY backend/requirements/base.txt requirements/base.txt                                                                                       0.0s
 => CACHED [celery-scraping deps 2/4] COPY backend/requirements/prod.txt requirements/prod.txt                                                                                       0.0s
 => CANCELED [celery-scraping deps 3/4] RUN pip install -r requirements/prod.txt                                                                                                   181.4s
 => CACHED [frontend deps 1/2] COPY frontend/package.json frontend/package-lock.json* ./                                                                                             0.0s
 => CACHED [frontend deps 2/2] RUN npm ci --legacy-peer-deps                                                                                                                         0.0s
 => CACHED [frontend builder 2/4] COPY --from=deps /app/node_modules ./node_modules                                                                                                  0.0s
 => [frontend builder 3/4] COPY frontend/ .                                                                                                                                          1.1s
 => ERROR [frontend builder 4/4] RUN npm run build                                                                                                                                 179.1s
------                                                                                                                                                                                    
 > [frontend builder 4/4] RUN npm run build:                                                                                                                                              
6.480                                                                                                                                                                                     
6.480 > whydud-frontend@0.1.0 build                                                                                                                                                       
6.480 > next build                                                                                                                                                                        
6.480                                                                                                                                                                                     
11.34    ▲ Next.js 15.1.0                                                                                                                                                                 
11.34                                                                                                                                                                                     
11.41    Creating an optimized production build ...                                                                                                                                       
127.4  ✓ Compiled successfully                                                                                                                                                            
127.4    Linting and checking validity of types ...                                                                                                                                       
161.5    Collecting page data ...                                                                                                                                                         
174.1    Generating static pages (0/30) ...
178.1  ⨯ useSearchParams() should be wrapped in a suspense boundary at page "/verify-email". Read more: https://nextjs.org/docs/messages/missing-suspense-with-csr-bailout
178.1     at a (/app/.next/server/chunks/4929.js:1:7743)
178.1     at f (/app/.next/server/chunks/4929.js:1:24339)
178.1     at l (/app/.next/server/app/(auth)/verify-email/page.js:1:3696)
178.1     at nO (/app/node_modules/next/dist/compiled/next-server/app-page.runtime.prod.js:20:45959)
178.1     at nI (/app/node_modules/next/dist/compiled/next-server/app-page.runtime.prod.js:20:47734)
178.1     at nL (/app/node_modules/next/dist/compiled/next-server/app-page.runtime.prod.js:20:65533)
178.1     at nN (/app/node_modules/next/dist/compiled/next-server/app-page.runtime.prod.js:20:63164)
178.1     at n$ (/app/node_modules/next/dist/compiled/next-server/app-page.runtime.prod.js:20:46311)
178.1     at nI (/app/node_modules/next/dist/compiled/next-server/app-page.runtime.prod.js:20:47780)
178.1     at nI (/app/node_modules/next/dist/compiled/next-server/app-page.runtime.prod.js:20:62515)
178.1 Error occurred prerendering page "/verify-email". Read more: https://nextjs.org/docs/messages/prerender-error
178.1 Export encountered an error on /(auth)/verify-email/page: /verify-email, exiting the build.
178.1  ⨯ Static worker exited with code: 1 and signal: null
178.4 npm notice
178.4 npm notice New major version of npm available! 10.9.4 -> 11.11.0
178.4 npm notice Changelog: https://github.com/npm/cli/releases/tag/v11.11.0
178.4 npm notice To update run: npm install -g npm@11.11.0
178.4 npm notice
------
[+] build 0/3
 ⠙ Image whydud-backend         Building                                                                                                                                            186.1s
 ⠙ Image whydud-frontend        Building                                                                                                                                            186.1s
 ⠙ Image whydud-celery-scraping Building                                                                                                                                            186.1s
frontend.Dockerfile:34

--------------------

  32 |     ARG NEXT_PUBLIC_SITE_URL=https://whydud.com

  33 |     

  34 | >>> RUN npm run build

  35 |     

  36 |     # ---------------------------------------------------------------------------

--------------------

target frontend: failed to solve: process "/bin/sh -c npm run build" did not complete successfully: exit code: 1