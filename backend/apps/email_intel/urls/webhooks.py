from django.urls import path
from apps.email_intel.views import InboundEmailWebhookView, RazorpayWebhookView

urlpatterns = [
    path("email/inbound", InboundEmailWebhookView.as_view(), name="webhook-email-inbound"),
    path("razorpay", RazorpayWebhookView.as_view(), name="webhook-razorpay"),
]
