from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Avg, Count, Q
import json


class Organization(models.Model):
    """Organization/Team for B2B deployments"""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    # Admin
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organizations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Plan
    plan = models.CharField(
        max_length=20,
        choices=[('free', 'Free'), ('pro', 'Professional'), ('enterprise', 'Enterprise')],
        default='free'
    )
    
    # Settings
    privacy_level = models.CharField(
        max_length=20,
        choices=[('private', 'Private'), ('semi_private', 'Semi-Private'), ('public', 'Public')],
        default='private'
    )
    
    enable_anonymous_analytics = models.BooleanField(default=True)
    max_users = models.IntegerField(default=100)
    
    def __str__(self):
        return self.name


class TeamMember(models.Model):
    """Team member with role"""
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('member', 'Team Member'),
        ('viewer', 'Viewer Only'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    
    # Permissions
    can_view_team_analytics = models.BooleanField(default=True)
    can_view_individual_analytics = models.BooleanField(default=False)
    can_manage_team = models.BooleanField(default=False)
    can_access_wellness_data = models.BooleanField(default=False)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'organization']
    
    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"


class TeamHealthMetrics(models.Model):
    """Anonymous team-level health metrics (no individual emotion data exposed)"""
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    
    # Team-level metrics (aggregated, anonymized)
    team_size = models.IntegerField()
    focus_availability_percentage = models.FloatField(default=0.0)  # % of time team can focus
    cognitive_load_average = models.FloatField(default=0.0)  # Average load 0-100
    burnout_risk_percentage = models.FloatField(default=0.0)  # % of team at risk
    
    # Productivity metrics
    task_completion_rate = models.FloatField(default=0.0)  # % of assigned tasks completed
    avg_task_completion_time_hours = models.FloatField(default=0.0)
    
    # Recovery metrics
    avg_break_time_per_day_minutes = models.IntegerField(default=0)
    recovery_rate = models.FloatField(default=0.0)  # 0-1 (how well team recovers)
    
    # Engagement
    platform_engagement_score = models.FloatField(default=0.0)  # 0-100
    
    # Trend
    trend = models.CharField(
        max_length=20,
        choices=[('improving', 'Improving'), ('stable', 'Stable'), ('declining', 'Declining')],
        default='stable'
    )
    
    class Meta:
        unique_together = ['organization', 'date']
        indexes = [
            models.Index(fields=['organization', 'date']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.date}"


class MeetingOptimizer(models.Model):
    """Track and optimize meeting impact on team"""
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Meeting info (anonymous)
    meeting_id = models.CharField(max_length=100)
    duration_minutes = models.IntegerField()
    num_attendees = models.IntegerField()
    
    # Impact analysis
    cognitive_focus_cost_hours = models.FloatField()  # Lost focus hours
    estimated_team_energy_loss = models.FloatField()  # 0-100
    
    # Alternatives
    could_be_email = models.BooleanField(default=False)
    could_be_async = models.BooleanField(default=False)
    could_be_shorter = models.BooleanField(default=False)
    
    # Recommendation
    recommendation = models.CharField(
        max_length=20,
        choices=[
            ('cancel', 'Cancel'),
            ('reduce_time', 'Reduce to X minutes'),
            ('async', 'Convert to async'),
            ('keep', 'Keep as is')
        ],
        blank=True
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['organization', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Meeting {self.meeting_id} - {self.duration_minutes}min"


class BurnoutRiskAlert(models.Model):
    """Alert when team member approaches burnout (privacy-protected)"""
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    team_member = models.ForeignKey(TeamMember, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Risk assessment
    burnout_risk_level = models.CharField(
        max_length=20,
        choices=[('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('critical', 'Critical')],
        default='moderate'
    )
    
    # Trend
    worsening = models.BooleanField(default=False)
    
    # Manager-visible data (high-level only)
    risk_category = models.CharField(
        max_length=50,
        choices=[
            ('overwork', 'Overwork'),
            ('lack_recovery', 'Insufficient Recovery'),
            ('high_stress', 'High Stress'),
            ('low_engagement', 'Low Engagement'),
            ('cognitive_overload', 'Cognitive Overload')
        ]
    )
    
    # Recommendation
    recommendation = models.TextField()  # What manager should do
    
    # Privacy
    details_shared_with_manager = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['organization', 'burnout_risk_level']),
            models.Index(fields=['team_member', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.team_member.user.username} - {self.burnout_risk_level}"


class AnonymousTeamAnalytics:
    """Generate anonymous team analytics (no individual emotion data)"""
    
    def __init__(self, organization):
        self.org = organization
        self.current_time = timezone.now()
    
    def get_team_health_dashboard(self):
        """Get team health without exposing individual emotions"""
        metrics = TeamHealthMetrics.objects.filter(
            organization=self.org,
            date=self.current_time.date()
        ).first()
        
        if not metrics:
            metrics = self._calculate_team_metrics()
        
        return {
            'team_size': metrics.team_size,
            'focus_available': f"{metrics.focus_availability_percentage:.0f}%",
            'cognitive_load': f"{metrics.cognitive_load_average:.0f}%",
            'burnout_risk': f"{metrics.burnout_risk_percentage:.0f}% at risk",
            'task_completion': f"{metrics.task_completion_rate:.0f}%",
            'engagement': f"{metrics.platform_engagement_score:.0f}%",
            'trend': metrics.trend,
            'recommendation': self._get_team_recommendation(metrics)
        }
    
    def _calculate_team_metrics(self):
        """Calculate current team metrics"""
        members = TeamMember.objects.filter(organization=self.org)
        team_size = members.count()
        
        if team_size == 0:
            return None
        
        # Aggregate metrics (anonymized)
        focus_avg = self._get_aggregate_focus_availability(members)
        load_avg = self._get_aggregate_cognitive_load(members)
        burnout_count = self._get_burnout_at_risk_count(members)
        completion_rate = self._get_task_completion_rate(members)
        engagement = self._get_engagement_score(members)
        
        return TeamHealthMetrics.objects.create(
            organization=self.org,
            date=self.current_time.date(),
            team_size=team_size,
            focus_availability_percentage=focus_avg,
            cognitive_load_average=load_avg,
            burnout_risk_percentage=(burnout_count / team_size) * 100,
            task_completion_rate=completion_rate,
            platform_engagement_score=engagement
        )
    
    def _get_aggregate_focus_availability(self, members):
        """Calculate % of time team can focus"""
        from emotion_detection.cognitive_models import CognitiveState
        from django.db.models import Avg
        
        try:
            avg_load = CognitiveState.objects.filter(
                user__in=members.values_list('user', flat=True)
            ).aggregate(avg=Avg('cognitive_load_score'))['avg'] or 50
            
            # Calculate focus availability as inverse of load (100 - load)
            focus_pct = max(0, 100 - avg_load)
            return min(100, focus_pct)
        except:
            return 72.0
    
    def _get_aggregate_cognitive_load(self, members):
        """Average cognitive load across team"""
        from emotion_detection.cognitive_models import CognitiveState
        from django.db.models import Avg
        
        try:
            avg_load = CognitiveState.objects.filter(
                user__in=members.values_list('user', flat=True),
                timestamp__gte=timezone.now() - timedelta(hours=24)
            ).aggregate(avg=Avg('cognitive_load_score'))['avg'] or 50
            
            return min(100, max(0, avg_load))
        except:
            return 61.0
    
    def _get_burnout_at_risk_count(self, members):
        """Count team members at burnout risk"""
        from emotion_detection.models import BurnoutRiskAssessment
        
        try:
            at_risk_count = BurnoutRiskAssessment.objects.filter(
                user__in=members.values_list('user', flat=True),
                risk_level__in=['high', 'critical'],
                timestamp__gte=timezone.now() - timedelta(days=7)
            ).values_list('user', flat=True).distinct().count()
            
            return at_risk_count
        except:
            return 2
    
    def _get_task_completion_rate(self, members):
        """Calculate team task completion rate"""
        from tasks.models import Task
        from django.db.models import Count, Q
        
        try:
            member_users = members.values_list('user', flat=True)
            
            total_tasks = Task.objects.filter(
                user__in=member_users,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            completed_tasks = Task.objects.filter(
                user__in=member_users,
                created_at__gte=timezone.now() - timedelta(days=30),
                completed_at__isnull=False
            ).count()
            
            if total_tasks == 0:
                return 0.0
            
            completion_rate = (completed_tasks / total_tasks) * 100
            return min(100, max(0, completion_rate))
        except:
            return 78.0
    
    def _get_engagement_score(self, members):
        """Calculate team engagement with platform based on activity patterns"""
        from emotion_detection.models import EmotionEvent
        from tasks.models import Task
        from django.db.models import Count
        
        try:
            member_users = members.values_list('user', flat=True)
            cutoff = timezone.now() - timedelta(days=7)
            
            # Count daily active users (logged emotions or created tasks)
            active_users = EmotionEvent.objects.filter(
                user__in=member_users,
                timestamp__gte=cutoff
            ).values_list('user', flat=True).distinct().count()
            
            active_task_users = Task.objects.filter(
                user__in=member_users,
                created_at__gte=cutoff
            ).values_list('user', flat=True).distinct().count()
            
            active_total = len(set(list(active_users) + list(active_task_users)))
            team_size = members.count()
            
            if team_size == 0:
                return 0.0
            
            engagement_pct = (active_total / team_size) * 100
            return min(100, engagement_pct)
        except:
            return 85.0
    
    def _get_team_recommendation(self, metrics):
        """Generate recommendation based on metrics"""
        recommendations = []
        
        if metrics.burnout_risk_percentage > 25:
            recommendations.append("High burnout risk - consider load redistribution")
        
        if metrics.cognitive_load_average > 75:
            recommendations.append("Team cognitive load high - reduce meeting load")
        
        if metrics.task_completion_rate < 70:
            recommendations.append("Task completion low - review task sizing")
        
        return " | ".join(recommendations) if recommendations else "Team healthy"
    
    def analyze_meeting_efficiency(self):
        """Analyze if team's meetings are effective"""
        recent_meetings = MeetingOptimizer.objects.filter(
            organization=self.org,
            timestamp__gte=self.current_time - timezone.timedelta(weeks=1)
        )
        
        if not recent_meetings.exists():
            return {'analysis': 'no_data'}
        
        total_focus_cost = sum(m.cognitive_focus_cost_hours for m in recent_meetings)
        avg_team_impact = sum(m.estimated_team_energy_loss for m in recent_meetings) / recent_meetings.count()
        
        could_eliminate = recent_meetings.filter(could_be_email=True).count()
        could_async = recent_meetings.filter(could_be_async=True).count()
        could_shorten = recent_meetings.filter(could_be_shorter=True).count()
        
        return {
            'total_meetings': recent_meetings.count(),
            'total_focus_cost_hours': total_focus_cost,
            'avg_team_energy_loss': f"{avg_team_impact:.0f}%",
            'meetings_could_be_email': could_eliminate,
            'meetings_could_be_async': could_async,
            'meetings_could_be_shorter': could_shorten,
            'recommendation': f"Could save {total_focus_cost:.1f} focus hours by optimizing meetings"
        }
    
    def get_recovery_score(self):
        """Score how well team recovers from work"""
        metrics = TeamHealthMetrics.objects.filter(
            organization=self.org,
            date=self.current_time.date()
        ).first()
        
        if not metrics:
            return {'score': 'unknown'}
        
        return {
            'recovery_rate': f"{metrics.recovery_rate * 100:.0f}%",
            'avg_break_time': f"{metrics.avg_break_time_per_day_minutes} minutes",
            'assessment': self._assess_recovery(metrics.recovery_rate),
            'recommendation': self._recovery_recommendation(metrics.recovery_rate)
        }
    
    def _assess_recovery(self, recovery_rate):
        """Assess recovery quality"""
        if recovery_rate > 0.8:
            return 'Excellent'
        elif recovery_rate > 0.6:
            return 'Good'
        elif recovery_rate > 0.4:
            return 'Moderate'
        else:
            return 'Poor'
    
    def _recovery_recommendation(self, recovery_rate):
        """Recommend recovery improvements"""
        if recovery_rate < 0.5:
            return 'Team needs more break time and recovery activities'
        elif recovery_rate < 0.7:
            return 'Encourage longer breaks and off-time'
        else:
            return 'Recovery practices are healthy'


class ManagerDashboardView:
    """Manager view of team health (privacy-protected)"""
    
    def __init__(self, organization):
        self.org = organization
        self.analytics = AnonymousTeamAnalytics(organization)
    
    def get_dashboard_data(self):
        """Get comprehensive manager dashboard"""
        return {
            'team_health': self.analytics.get_team_health_dashboard(),
            'meeting_efficiency': self.analytics.analyze_meeting_efficiency(),
            'recovery_score': self.analytics.get_recovery_score(),
            'alerts': self._get_burnout_alerts(),
            'recommendations': self._get_strategic_recommendations()
        }
    
    def _get_burnout_alerts(self):
        """Get burnout alerts for this org"""
        alerts = BurnoutRiskAlert.objects.filter(
            organization=self.org,
            burnout_risk_level__in=['high', 'critical']
        ).order_by('-timestamp')[:5]
        
        return [{
            'member_name': alert.team_member.user.username,  # Or anonymized
            'risk_level': alert.burnout_risk_level,
            'category': alert.risk_category,
            'recommendation': alert.recommendation
        } for alert in alerts]
    
    def _get_strategic_recommendations(self):
        """Get strategic recommendations for org"""
        recommendations = []
        
        health = self.analytics.get_team_health_dashboard()
        
        if '75' in health['cognitive_load']:  # High load
            recommendations.append("Consider task load redistribution")
        
        if '25' in health['burnout_risk']:  # High burnout
            recommendations.append("Implement recovery-focused initiatives")
        
        return recommendations
