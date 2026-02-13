from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from .explainability_models import Insight, ExplainabilitySignal, ConfidenceScore
import json
import csv
from io import StringIO
from django.db.models import Count
from django.conf import settings
from django.http import FileResponse
import os
import io

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


@login_required
def insights_dashboard(request):
    user = request.user
    # Optional filter by category
    category = request.GET.get('category')
    qs = Insight.objects.filter(user=user)
    if category:
        qs = qs.filter(category=category)

    insights = qs.order_by('-period_end')[:100]

    # Aggregate counts by category for charting
    counts = Insight.objects.filter(user=user).values('category').annotate(count=Count('id'))
    category_counts = {c['category']: c['count'] for c in counts}

    return render(request, 'insights/dashboard.html', {
        'insights': insights,
        'category_counts_json': json.dumps(category_counts),
        'selected_category': category or '',
    })


@login_required
def insight_detail(request, insight_id):
    insight = get_object_or_404(Insight, id=insight_id, user=request.user)
    # Also pull related explainability signals
    signals = ExplainabilitySignal.objects.filter(intervention__user=request.user).order_by('-created_at')[:10]
    return render(request, 'insights/detail.html', {'insight': insight, 'signals': signals})


@login_required
def export_insight_json(request, insight_id):
    insight = get_object_or_404(Insight, id=insight_id, user=request.user)
    payload = {
        'title': insight.title,
        'description': insight.description,
        'data': insight.data,
        'confidence': insight.confidence,
        'suggested_action': getattr(insight, 'suggested_action', None),
        'period_start': str(insight.period_start) if insight.period_start else None,
        'period_end': str(insight.period_end) if insight.period_end else None,
    }
    return JsonResponse(payload)


@login_required
def export_insight_csv(request, insight_id):
    insight = get_object_or_404(Insight, id=insight_id, user=request.user)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['title', 'description', 'confidence', 'suggested_action', 'period_start', 'period_end', 'data'])
    writer.writerow([
        insight.title,
        insight.description,
        f"{insight.confidence:.2f}",
        insight.suggested_action or '',
        str(insight.period_start) if insight.period_start else '',
        str(insight.period_end) if insight.period_end else '',
        json.dumps(insight.data)
    ])

    resp = HttpResponse(buffer.getvalue(), content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="insight_{insight.id}.csv"'
    return resp


@login_required
def create_insight_export(request, insight_id):
    """Generate a PDF export for an insight and create an InsightExport record."""
    insight = get_object_or_404(Insight, id=insight_id, user=request.user)

    media_root = getattr(settings, 'MEDIA_ROOT', None)
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    if not media_root:
        return JsonResponse({'error': 'MEDIA_ROOT not configured'}, status=500)

    export_dir = os.path.join(media_root, 'insight_exports')
    os.makedirs(export_dir, exist_ok=True)

    filename = f'insight_{insight.id}.pdf'
    path = os.path.join(export_dir, filename)

    # Generate PDF (or fallback) and write to path
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
        with open(path, 'wb') as f:
            f.write(buf.read())
    else:
        # Fallback to simple HTML file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"<h1>{insight.title}</h1>")
            f.write(f"<p>User: {insight.user.username} | Category: {insight.category}</p>")
            f.write(f"<div>{insight.description}</div>")

    # Create InsightExport record (placeholder file will be generated)
    from .explainability_models import InsightExport
    ie = InsightExport.objects.create(
        user=insight.user,
        export_format='pdf',
        title=f'Export of: {insight.title}',
        period_start=insight.period_start or insight.generated_at.date(),
        period_end=insight.period_end or insight.generated_at.date(),
        is_shareable=False,
    )
    ie.insights_included.add(insight)

    # Use async task if available, else generate synchronously
    try:
        from .export_tasks import generate_insight_export_task, generate_insight_export
        if generate_insight_export_task:
            generate_insight_export_task.delay(ie.id)
        else:
            generate_insight_export(ie.id)
    except Exception:
        try:
            from .export_tasks import generate_insight_export
            generate_insight_export(ie.id)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # Return the export record; file_url may be populated shortly by the task
    return JsonResponse({'file_url': ie.file_url or '', 'export_id': ie.id})


@login_required
def download_insight_export(request, export_id):
    """Serve the generated export file for download."""
    from .explainability_models import InsightExport
    ie = get_object_or_404(InsightExport, id=export_id, user=request.user)

    media_root = getattr(settings, 'MEDIA_ROOT', None)
    if not media_root:
        return JsonResponse({'error': 'MEDIA_ROOT not configured'}, status=500)

    # convert file_url to path
    rel = ie.file_url.replace(getattr(settings, 'MEDIA_URL', '/media/'), '')
    path = os.path.join(media_root, rel)
    if not os.path.exists(path):
        return JsonResponse({'error': 'Export file not found'}, status=404)

    return FileResponse(open(path, 'rb'), as_attachment=True, filename=os.path.basename(path))
