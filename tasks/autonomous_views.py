from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Max, Q
from .models import Task, EmotionTag, EmotionRecord, TaskEmotionPattern
from emotion_detection.emotion_detector import emotion_detector, get_emotion_recommendations
from emotion_detection.voice_detector import voice_detector
from emotion_detection.typing_detector import typing_detector
from emotion_detection.empathy_engine import empathy_engine
from emotion_detection.analytics_visualizer import analytics_visualizer
from emotion_detection.biofeedback_integrator import biofeedback_integrator
from emotion_detection.biofeedback_models import BiofeedbackDevice
from emotion_detection.autonomous_models import (
    EmotionEvent, TaskFeedback, RLModel, KnowledgeGraph, 
    AutoConfiguration, UserGoal, WeeklyReport, IndustryTrend
)
from emotion_detection.autonomous_learning import learning_manager, ReinforcementLearningEngine
from emotion_detection.celery_tasks import train_rl_models
import json

@login_required
def enhanced_dashboard(request):
    """Enhanced dashboard with real-time adaptation and RL recommendations"""
    user_tasks = Task.objects.filter(user=request.user).exclude(status='completed')
    
    # Get comprehensive emotion state from all sensors
    emotion_state = empathy_engine.get_comprehensive_emotion_state(request.user)
    current_emotion = emotion_state.get('combined', 'neutral')
    current_emotion_data = emotion_state
    
    # Get RL-based task recommendations
    rl_recommendations = get_rl_task_recommendations(request.user, user_tasks)
    
    # Get traditional recommendations as fallback
    traditional_recommendations = get_emotion_recommendations(current_emotion, user_tasks)
    
    # Combine recommendations (RL takes priority)
    recommendations = rl_recommendations if rl_recommendations else traditional_recommendations
    
    # Get recent emotion records from all sources
    recent_emotions = EmotionEvent.objects.filter(user=request.user).order_by('-timestamp')[:10]
    
    # Get task statistics
    total_tasks = Task.objects.filter(user=request.user).count()
    completed_tasks = Task.objects.filter(user=request.user, status='completed').count()
    pending_tasks = Task.objects.filter(user=request.user, status='pending').count()
    
    # Get biofeedback data if available
    stress_level = biofeedback_integrator.get_current_stress_level(request.user)
    energy_level = biofeedback_integrator.get_energy_level(request.user)
    
    # Get AI configuration for dynamic UI
    ui_config = get_dynamic_ui_config(request.user, current_emotion)
    
    # Generate empathetic message
    empathetic_message = empathy_engine.generate_empathetic_message(
        current_emotion, 
        current_task=recommendations[0] if recommendations else None
    )
    
    context = {
        'tasks': user_tasks,
        'recommendations': recommendations,
        'current_emotion': current_emotion,
        'current_emotion_data': current_emotion_data,
        'recent_emotions': recent_emotions,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'emotion_tags': EmotionTag.objects.all(),
        'empathetic_message': empathetic_message,
        'stress_level': stress_level,
        'energy_level': energy_level,
        'biofeedback_available': BiofeedbackDevice.objects.filter(user=request.user, is_active=True).exists(),
        'ui_config': ui_config,
        'rl_available': RLModel.objects.filter(user=request.user, is_active=True).exists(),
        'goals': UserGoal.objects.filter(user=request.user, is_active=True).order_by('target_date')[:3],
    }
    
    return render(request, 'dashboard/unified_dashboard.html', context)

@login_required
def get_rl_task_recommendations(request):
    """Get RL-based task recommendations"""
    if request.method == 'GET':
        try:
            user = request.user
            
            # Check if RL model is available
            rl_model = RLModel.objects.filter(user=user, is_active=True).first()
            if not rl_model:
                return JsonResponse({'status': 'error', 'message': 'RL model not available'})
            
            # Get available tasks
            available_tasks = Task.objects.filter(user=user, status='pending').order_by('-priority')
            
            if not available_tasks.exists():
                return JsonResponse({'status': 'success', 'recommendations': []})
            
            # Get RL engine
            rl_engine = ReinforcementLearningEngine(user)
            
            # Get current state
            state = rl_engine.get_state_vector(user)
            
            # Get Q-values for all tasks
            q_values = rl_engine.predict_q_values(state, list(available_tasks))
            
            # Sort tasks by Q-value
            task_q_pairs = list(zip(available_tasks, q_values))
            task_q_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # Return top recommendations
            top_tasks = task_q_pairs[:5]
            recommendations = []
            
            for task, q_value in top_tasks:
                recommendations.append({
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'priority': task.priority,
                    'q_value': q_value,
                    'reasoning': f'RL recommendation (Q-value: {q_value:.2f})'
                })
            
            return JsonResponse({'status': 'success', 'recommendations': recommendations})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def submit_task_feedback(request):
    """Submit feedback for completed task"""
    if request.method == 'POST':
        try:
            task_id = request.POST.get('task_id')
            task_satisfaction = int(request.POST.get('task_satisfaction', 3))
            emotion_before = request.POST.get('emotion_before', 'neutral')
            emotion_after = request.POST.get('emotion_after', 'neutral')
            emotion_change = int(request.POST.get('emotion_change', 0))
            completion_time = float(request.POST.get('completion_time', 60))
            difficulty = int(request.POST.get('difficulty', 3))
            focus_level = int(request.POST.get('focus_level', 3))
            ai_helpfulness = int(request.POST.get('ai_helpfulness', 3))
            ai_tone = request.POST.get('ai_tone', 'empathetic')
            
            # Get task
            task = get_object_or_404(Task, id=task_id, user=request.user)
            
            # Create feedback record
            feedback = TaskFeedback.objects.create(
                user=request.user,
                task=task,
                task_satisfaction=task_satisfaction,
                emotion_before=emotion_before,
                emotion_after=emotion_after,
                emotion_change_rating=emotion_change,
                completion_time_minutes=completion_time,
                perceived_difficulty=difficulty,
                focus_level=focus_level,
                ai_helpfulness=ai_helpfulness,
                ai_tone_preference=ai_tone
            )
            
            # Calculate and store reward
            rl_engine = ReinforcementLearningEngine(request.user)
            reward = rl_engine.calculate_reward(feedback)
            
            # Trigger immediate RL training (asynchronously)
            train_rl_models.delay()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Feedback submitted successfully',
                'reward': reward
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def get_dynamic_ui_config(request):
    """Get dynamic UI configuration based on emotion and preferences"""
    user = request.user
    current_emotion = request.GET.get('current_emotion', 'neutral')
    
    # Get user's UI preferences
    ui_configs = AutoConfiguration.objects.filter(user=user, category='ui_theme')
    
    # Default configurations
    config = {
        'theme': 'default',
        'primary_color': '#007bff',
        'secondary_color': '#6c757d',
        'background_style': 'light',
        'animation_speed': 'normal',
        'message_tone': 'empathetic'
    }
    
    # Apply emotion-based adaptations
    emotion_themes = {
        'stressed': {
            'theme': 'calm',
            'primary_color': '#28a745',
            'background_style': 'soft',
            'animation_speed': 'slow'
        },
        'focused': {
            'theme': 'productive',
            'primary_color': '#007bff',
            'background_style': 'minimal',
            'animation_speed': 'fast'
        },
        'happy': {
            'theme': 'energetic',
            'primary_color': '#ffc107',
            'background_style': 'bright',
            'animation_speed': 'normal'
        },
        'calm': {
            'theme': 'peaceful',
            'primary_color': '#17a2b8',
            'background_style': 'soft',
            'animation_speed': 'slow'
        }
    }
    
    if current_emotion in emotion_themes:
        config.update(emotion_themes[current_emotion])
    
    # Apply user-specific configurations
    for ui_config in ui_configs:
        if ui_config.parameter_name in config:
            config[ui_config.parameter_name] = ui_config.parameter_value.get('value', config[ui_config.parameter_name])
    
    return config

@login_required
def real_time_emotion_update(request):
    """Real-time emotion update with UI adaptation"""
    if request.method == 'POST':
        try:
            emotion_data = json.loads(request.body)
            new_emotion = emotion_data.get('emotion', 'neutral')
            confidence = emotion_data.get('confidence', 0.0)
            
            # Store emotion event
            EmotionEvent.objects.create(
                user=request.user,
                emotion=new_emotion,
                confidence=confidence,
                source='manual',
                raw_features=emotion_data
            )
            
            # Get new UI configuration
            ui_config = get_dynamic_ui_config(request.user, new_emotion)
            
            # Get new task recommendations
            user_tasks = Task.objects.filter(user=request.user, status='pending')
            recommendations = get_emotion_recommendations(new_emotion, user_tasks)
            
            # Generate new empathetic message
            message = empathy_engine.generate_empathetic_message(new_emotion)
            
            return JsonResponse({
                'status': 'success',
                'ui_config': ui_config,
                'recommendations': [{'id': t.id, 'title': t.title} for t in recommendations[:3]],
                'message': message
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def knowledge_graph_view(request):
    """View personal knowledge graph"""
    user = request.user
    
    # Get knowledge graph data
    graph_nodes = KnowledgeGraph.objects.filter(user=user)
    
    # Build graph structure
    nodes = []
    edges = []
    
    for node in graph_nodes:
        nodes.append({
            'id': node.id,
            'label': node.entity_name,
            'type': node.entity_type,
            'size': node.data_points_count,
            'color': get_node_color(node.entity_type),
            'success_rate': node.success_rate
        })
        
        # Add edges
        for related_id, strength in node.relationship_strength.items():
            edges.append({
                'from': node.id,
                'to': related_id,
                'strength': strength,
                'type': node.relationship_type.get(str(related_id), 'related')
            })
    
    context = {
        'nodes': json.dumps(nodes),
        'edges': json.dumps(edges),
        'graph_stats': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'entity_types': list(set(node['type'] for node in nodes))
        }
    }
    
    return render(request, 'tasks/knowledge_graph.html', context)

@login_required
def goals_view(request):
    """View and manage long-term goals"""
    user = request.user
    
    # Get user's goals
    active_goals = UserGoal.objects.filter(user=user, is_active=True).order_by('target_date')
    completed_goals = UserGoal.objects.filter(user=user, is_active=False).order_by('-target_date')[:5]
    
    # Get goal progress
    for goal in active_goals:
        # Calculate progress based on related tasks
        related_tasks = Task.objects.filter(
            user=user,
            title__icontains=goal.goal_title.split()[0],  # Simple matching
            status='completed'
        ).count()
        
        total_tasks = Task.objects.filter(
            user=user,
            title__icontains=goal.goal_title.split()[0]
        ).count()
        
        if total_tasks > 0:
            goal.current_progress = (related_tasks / total_tasks) * 100
        else:
            goal.current_progress = 0
    
    context = {
        'active_goals': active_goals,
        'completed_goals': completed_goals,
        'industry_trends': IndustryTrend.objects.all()[:5]
    }
    
    return render(request, 'tasks/goals.html', context)

@login_required
def weekly_reports_view(request):
    """View AI-generated weekly reports"""
    user = request.user
    
    # Get user's reports
    reports = WeeklyReport.objects.filter(user=user).order_by('-week_start')[:12]
    
    context = {
        'reports': reports,
        'has_reports': reports.exists()
    }
    
    return render(request, 'tasks/weekly_reports.html', context)

@login_required
def federated_learning_status(request):
    """View federated learning status and contribute data"""
    user = request.user
    
    # Check if user has opted into federated learning
    opt_in_status = AutoConfiguration.objects.filter(
        user=user,
        category='federated_learning',
        parameter_name='opt_in'
    ).first()
    
    is_opted_in = opt_in_status.parameter_value.get('value', False) if opt_in_status else False
    
    # Get contribution statistics
    from emotion_detection.autonomous_models import FederatedLearningNode
    user_node = FederatedLearningNode.objects.filter(node_id=f"user_{user.id}").first()
    
    context = {
        'is_opted_in': is_opted_in,
        'contribution_count': user_node.total_contributions if user_node else 0,
        'last_contribution': user_node.last_contribution if user_node else None,
        'global_models': RLModel.objects.filter(model_name='task_optimization').count()
    }
    
    return render(request, 'tasks/federated_learning.html', context)

@login_required
def toggle_federated_learning(request):
    """Toggle federated learning participation"""
    if request.method == 'POST':
        try:
            opt_in = request.POST.get('opt_in') == 'true'
            
            AutoConfiguration.objects.update_or_create(
                user=request.user,
                category='federated_learning',
                parameter_name='opt_in',
                defaults={
                    'parameter_value': {'value': opt_in},
                    'adjustment_reason': f'User {"opted in" if opt_in else "opted out"} of federated learning'
                }
            )
            
            if opt_in:
                # Create user node for federated learning
                from emotion_detection.autonomous_models import FederatedLearningNode
                FederatedLearningNode.objects.update_or_create(
                    node_id=f"user_{request.user.id}",
                    defaults={
                        'organization': 'Individual',
                        'is_active': True
                    }
                )
            
            return JsonResponse({
                'status': 'success',
                'message': f'Federated learning {"enabled" if opt_in else "disabled"}'
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def get_node_color(entity_type):
    """Get color for knowledge graph node based on entity type"""
    colors = {
        'emotion': '#ff6b6b',
        'task_type': '#4ecdc4',
        'time_period': '#45b7d1',
        'context': '#96ceb4',
        'performance': '#feca57',
        'emotion_task': '#ff9ff3',
        'time_pattern': '#54a0ff'
    }
    return colors.get(entity_type, '#95afc0')
