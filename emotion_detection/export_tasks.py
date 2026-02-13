"""Tasks for generating Insight exports. Supports synchronous generation
and a Celery task wrapper if a Celery app is available.
"""
import os
import io
from django.conf import settings
from django.db import models

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

from .explainability_models import InsightExport

def _generate_pdf_bytes_for_insight(insight):
    """Return bytes of a simple PDF (or HTML fallback) for an Insight."""
    if REPORTLAB_AVAILABLE:
        buf = io.BytesIO()
        p = canvas.Canvas(buf, pagesize=letter)
        p.setFont('Helvetica-Bold', 14)
        p.drawString(72, 720, insight.title)
        p.setFont('Helvetica', 10)
        p.drawString(72, 700, f'User: {insight.user.username}  |  Category: {insight.category}')
        p.drawString(72, 680, f'Confidence: {insight.confidence:.2f}  |  Period: {insight.period_start} to {insight.period_end}')
        text = p.beginText(72, 640)
        for line in (insight.description or '').splitlines():
            text.textLine(line)
        p.drawText(text)
        p.showPage()
        p.save()
        buf.seek(0)
        return buf.read()
    else:
        # Simple HTML bytes
        html = f"<h1>{insight.title}</h1><p>User: {insight.user.username} | Category: {insight.category}</p><div>{insight.description}</div>"
        return html.encode('utf-8')


def generate_insight_export(export_id):
    """Generate the export file for the given InsightExport record.

    This function is safe to call synchronously. If Celery is available the
    admin can enqueue it.
    """
    try:
        ie = InsightExport.objects.get(id=export_id)
    except InsightExport.DoesNotExist:
        return False

    media_root = getattr(settings, 'MEDIA_ROOT', None)
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    if not media_root:
        return False

    export_dir = os.path.join(media_root, 'insight_exports')
    os.makedirs(export_dir, exist_ok=True)

    filename = f'insightexport_{ie.id}.pdf'
    path = os.path.join(export_dir, filename)

    # If multiple insights included, concatenate simple PDFs by appending
    content_bytes = b''
    included = ie.insights_included.all()
    if included.exists():
        for insight in included:
            content_bytes += _generate_pdf_bytes_for_insight(insight)
    else:
        # fallback: use title
        class Dummy:
            title = ie.title
            user = ie.user
            category = 'export'
            confidence = 0.0
            period_start = ie.period_start
            period_end = ie.period_end
            description = ''
        content_bytes = _generate_pdf_bytes_for_insight(Dummy())

    # Write bytes to file path
    mode = 'wb'
    with open(path, mode) as f:
        f.write(content_bytes)

    ie.file_url = media_url + f'insight_exports/{filename}'
    ie.save()
    return True


# Optional Celery task wrapper
try:
    from AbigaelAI.celery import app as celery_app

    @celery_app.task(name='emotion_detection.generate_insight_export')
    def generate_insight_export_task(export_id):
        return generate_insight_export(export_id)
    
    @celery_app.task(name='emotion_detection.periodic_regenerate_exports')
    def periodic_regenerate_exports(days=7):
        """Find shareable exports older than `days` and regenerate them."""
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=days)
        exports = InsightExport.objects.filter(is_shareable=True).filter(
            models.Q(file_url='') | models.Q(created_at__lte=cutoff)
        )
        results = []
        for ie in exports:
            try:
                generate_insight_export(ie.id)
                results.append(ie.id)
            except Exception:
                pass
        return results
except Exception:
    generate_insight_export_task = None
