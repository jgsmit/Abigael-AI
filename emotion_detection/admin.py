from django.contrib import admin
from .explainability_models import Insight, ExplainabilitySignal, InterventionEffectiveness, UserPattern, ConfidenceScore
from .explainability_models import InsightExport
from django.conf import settings
import os
import io

try:
	from reportlab.lib.pagesizes import letter
	from reportlab.pdfgen import canvas
	REPORTLAB_AVAILABLE = True
except Exception:
	REPORTLAB_AVAILABLE = False


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'title', 'category', 'confidence', 'period_end')
	search_fields = ('title', 'description')
	readonly_fields = ('data',)
	actions = ['export_selected_as_pdf']

	def export_selected_as_pdf(self, request, queryset):
		"""Admin action: create PDF exports for selected insights and register InsightExport records."""
		media_dir = getattr(settings, 'MEDIA_ROOT', None)
		if not media_dir:
			self.message_user(request, 'MEDIA_ROOT not configured; cannot write export files.', level=40)
			return

		export_dir = os.path.join(media_dir, 'insight_exports')
		os.makedirs(export_dir, exist_ok=True)

		created = 0
		for insight in queryset:
			filename = f'insight_{insight.id}.pdf'
			path = os.path.join(export_dir, filename)

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
				# Fallback: write an HTML file with .pdf extension so admin can still download
				with open(path, 'w', encoding='utf-8') as f:
					f.write(f"<h1>{insight.title}</h1>")
					f.write(f"<p>User: {insight.user.username} | Category: {insight.category}</p>")
					f.write(f"<div>{insight.description}</div>")

			# Create InsightExport record
			ie = InsightExport.objects.create(
				user=insight.user,
				export_format='pdf',
				title=f'Export of: {insight.title}',
				period_start=insight.period_start or insight.generated_at.date(),
				period_end=insight.period_end or insight.generated_at.date(),
				file_url=getattr(settings, 'MEDIA_URL', '/media/') + f'insight_exports/{filename}',
				is_shareable=False,
			)
			ie.insights_included.add(insight)
			created += 1

		self.message_user(request, f'Created {created} insight export(s).')
	export_selected_as_pdf.short_description = 'Export selected insights as PDF (creates InsightExport)'


@admin.register(ExplainabilitySignal)
class ExplainabilitySignalAdmin(admin.ModelAdmin):
	list_display = ('id', 'intervention', 'trigger_reason', 'confidence_score', 'created_at')
	search_fields = ('trigger_reason', 'explanation')


@admin.register(ConfidenceScore)
class ConfidenceScoreAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'subject', 'confidence', 'created_at')
	readonly_fields = ('factors', 'uncertainty_reasons')


@admin.register(InterventionEffectiveness)
class InterventionEffectivenessAdmin(admin.ModelAdmin):
	list_display = ('id', 'rule', 'helpful_rate', 'sample_size')


@admin.register(UserPattern)
class UserPatternAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'pattern_type', 'confidence', 'sample_size')


@admin.register(InsightExport)
class InsightExportAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'title', 'export_format', 'created_at', 'file_url')
	readonly_fields = ('file_url',)
	actions = ['regenerate_selected_exports']

	def regenerate_selected_exports(self, request, queryset):
		"""Regenerate selected exports (enqueue async task if available)."""
		created = 0
		for ie in queryset:
			try:
				from .export_tasks import generate_insight_export_task, generate_insight_export
				if generate_insight_export_task:
					generate_insight_export_task.delay(ie.id)
				else:
					generate_insight_export(ie.id)
				created += 1
			except Exception as e:
				self.message_user(request, f"Failed to regenerate {ie.id}: {e}")
		self.message_user(request, f"Regeneration requested for {created} export(s)")
	regenerate_selected_exports.short_description = 'Regenerate selected InsightExport files'
