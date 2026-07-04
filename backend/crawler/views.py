from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.report_service import build_report


@api_view(["POST"])
def crawl_topic(request):
    topic = request.data.get("topic", "").strip()

    if not topic:
        return Response({"error": "Topic is required"}, status=400)

    report = build_report(topic)
    return Response(report)