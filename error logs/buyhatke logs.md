_traceback(None)
whydud-celery-worker  | django.db.utils.OperationalError: connection failed: connection to server at "172.18.0.4", port 5432 failed: FATAL:  sorry, too many clients already
whydud-celery-worker  | [2026-03-07 05:30:19,921: INFO/MainProcess] Task apps.pricing.tasks.run_phase2_buyhatke[5fc1c7ff-8f5a-47cf-b64f-f28b66eec0a0] received
whydud-celery-worker  | [2026-03-07 05:30:20,639: INFO/ForkPoolWorker-2] HTTP Request: POST https://discordapp.com/api/webhooks/1478214042136088598/qXEuu5ZQCKpgprNJ3iOC6l-facfTpqNO7qPSL-UddxLbaxiTaZW3ky1oxD4Zmpb8VidE "HTTP/1.1 204 No Content"
whydud-celery-worker  | [2026-03-07 05:30:20,640: ERROR/ForkPoolWorker-2] Task apps.pricing.tasks.run_phase2_buyhatke[5fc1c7ff-8f5a-47cf-b64f-f28b66eec0a0] raised unexpected: OperationalError('connection failed: connection to server at "172.18.0.4", port 5432 failed: FATAL:  sorry, too many clients already')
whydud-celery-worker  | Traceback (most recent call last):
whydud-celery-worker  |   File "/usr/local/lib/python3.12/site-packages/django/db/backends/base/base.py", line 279, in ensure_conne