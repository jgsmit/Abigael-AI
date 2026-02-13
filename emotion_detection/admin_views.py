from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.urls import reverse
from .explainability_models import InsightExport


@staff_member_required
def insight_export_list(request):
    exports = InsightExport.objects.all().order_by('-created_at')[:200]
    return render(request, 'admin/insight_exports/list.html', {'exports': exports})


@staff_member_required
def insight_export_detail(request, export_id):
    ie = get_object_or_404(InsightExport, id=export_id)
    return render(request, 'admin/insight_exports/detail.html', {'export': ie})


@staff_member_required
def insight_export_regenerate(request, export_id):
    ie = get_object_or_404(InsightExport, id=export_id)
    from .export_tasks import generate_insight_export_task, generate_insight_export
    try:
        if generate_insight_export_task:
            generate_insight_export_task.delay(ie.id)
            messages.success(request, 'Regeneration enqueued.')
        else:
            generate_insight_export(ie.id)
            messages.success(request, 'Regeneration completed.')
    except Exception as e:
        messages.error(request, f'Regeneration failed: {e}')

    return redirect(reverse('admin_insight_export_detail', args=[ie.id]))
