import resend
import os

resend.api_key = os.environ.get('RESEND_API_KEY')

r = resend.Emails.send({
    "from": "Whydud <noreply@whydud.com>",
    "to": ["ramesh4nani@gmail.com"],
    "subject": "Whydud Resend Test",
    "html": "<p>If you see this, Resend is working. All the best for the Whydud Project</p>"
})

print(r)  # Should return {'id': 'some-uuid'}