import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q
from tasks.models import Task, EmotionRecord, TaskEmotionPattern
from emotion_detection.models import EmotionSnapshot, EmotionAnalysis
from emotion_detection.voice_typing_models import VoiceEmotionRecord, TypingEvent

class EmotionAnalyticsVisualizer:
    def __init__(self):
        self.color_palette = {
            'happy': '#2ECC71',
            'sad': '#3498DB', 
            'angry': '#E74C3C',
            'fearful': '#9B59B6',
            'disgusted': '#F39C12',
            'surprised': '#E67E22',
            'neutral': '#95A5A6',
            'focused': '#1ABC9C',
            'stressed': '#E74C3C',
            'calm': '#3498DB',
            'excited': '#F1C40F',
            'tired': '#7F8C8D'
        }
    
    def generate_emotion_timeline_chart(self, user, days=7):
        """Generate emotion timeline visualization"""
        try:
            # Get emotion data for the specified period
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get facial emotion records
            facial_records = EmotionRecord.objects.filter(
                user=user,
                timestamp__gte=cutoff_date
            ).order_by('timestamp')
            
            # Get voice emotion records
            voice_records = VoiceEmotionRecord.objects.filter(
                session__user=user,
                timestamp__gte=cutoff_date
            ).order_by('timestamp')
            
            # Get typing emotion records
            typing_records = TypingEvent.objects.filter(
                pattern__user=user,
                timestamp__gte=cutoff_date,
                inferred_emotion__isnull=False
            ).order_by('timestamp')
            
            # Create timeline data
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=('Facial Emotions', 'Voice Emotions', 'Typing Emotions'),
                vertical_spacing=0.08
            )
            
            # Add facial emotions
            if facial_records.exists():
                facial_data = []
                for record in facial_records:
                    facial_data.append({
                        'timestamp': record.timestamp,
                        'emotion': record.emotion,
                        'confidence': record.confidence
                    })
                
                facial_df = pd.DataFrame(facial_data)
                
                for emotion in facial_df['emotion'].unique():
                    emotion_data = facial_df[facial_df['emotion'] == emotion]
                    fig.add_trace(
                        go.Scatter(
                            x=emotion_data['timestamp'],
                            y=emotion_data['confidence'],
                            mode='markers+lines',
                            name=f'Facial: {emotion}',
                            line=dict(color=self.color_palette.get(emotion, '#95A5A6')),
                            marker=dict(size=6)
                        ),
                        row=1, col=1
                    )
            
            # Add voice emotions
            if voice_records.exists():
                voice_data = []
                for record in voice_records:
                    voice_data.append({
                        'timestamp': record.timestamp,
                        'emotion': record.emotion,
                        'confidence': record.confidence
                    })
                
                voice_df = pd.DataFrame(voice_data)
                
                for emotion in voice_df['emotion'].unique():
                    emotion_data = voice_df[voice_df['emotion'] == emotion]
                    fig.add_trace(
                        go.Scatter(
                            x=emotion_data['timestamp'],
                            y=emotion_data['confidence'],
                            mode='markers+lines',
                            name=f'Voice: {emotion}',
                            line=dict(color=self.color_palette.get(emotion, '#95A5A6')),
                            marker=dict(size=6)
                        ),
                        row=2, col=1
                    )
            
            # Add typing emotions
            if typing_records.exists():
                typing_data = []
                for record in typing_records:
                    typing_data.append({
                        'timestamp': record.timestamp,
                        'emotion': record.inferred_emotion,
                        'confidence': record.confidence
                    })
                
                typing_df = pd.DataFrame(typing_data)
                
                for emotion in typing_df['emotion'].unique():
                    emotion_data = typing_df[typing_df['emotion'] == emotion]
                    fig.add_trace(
                        go.Scatter(
                            x=emotion_data['timestamp'],
                            y=emotion_data['confidence'],
                            mode='markers+lines',
                            name=f'Typing: {emotion}',
                            line=dict(color=self.color_palette.get(emotion, '#95A5A6')),
                            marker=dict(size=6)
                        ),
                        row=3, col=1
                    )
            
            fig.update_layout(
                title=f'Emotion Timeline - Last {days} Days',
                height=800,
                showlegend=True,
                hovermode='x unified'
            )
            
            fig.update_yaxes(title_text='Confidence', row=1, col=1)
            fig.update_yaxes(title_text='Confidence', row=2, col=1)
            fig.update_yaxes(title_text='Confidence', row=3, col=1)
            fig.update_xaxes(title_text='Time', row=3, col=1)
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            print(f"Timeline chart error: {e}")
            return "<p>Error generating timeline chart</p>"
    
    def generate_emotion_distribution_pie(self, user, days=30):
        """Generate emotion distribution pie chart"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get all emotion records
            emotion_records = EmotionRecord.objects.filter(
                user=user,
                timestamp__gte=cutoff_date
            )
            
            if not emotion_records.exists():
                return "<p>No emotion data available</p>"
            
            # Count emotions
            emotion_counts = emotion_records.values('emotion').annotate(
                count=Count('emotion')
            ).order_by('-count')
            
            # Create pie chart
            labels = [item['emotion'] for item in emotion_counts]
            values = [item['count'] for item in emotion_counts]
            colors = [self.color_palette.get(label, '#95A5A6') for label in labels]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                marker_colors=colors,
                textinfo='label+percent',
                textposition='auto'
            )])
            
            fig.update_layout(
                title=f'Emotion Distribution - Last {days} Days',
                height=500
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            print(f"Pie chart error: {e}")
            return "<p>Error generating pie chart</p>"
    
    def generate_productivity_heatmap(self, user, days=30):
        """Generate emotion vs task productivity heatmap"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get task completion patterns
            patterns = TaskEmotionPattern.objects.filter(
                user=user
            ).order_by('-completion_rate')
            
            if not patterns.exists():
                return "<p>No productivity patterns available</p>"
            
            # Create heatmap data
            emotions = list(set([p.emotion for p in patterns]))
            task_types = list(set([p.task_type for p in patterns]))
            
            # Create matrix
            z_matrix = []
            for task_type in task_types:
                row = []
                for emotion in emotions:
                    pattern = patterns.filter(emotion=emotion, task_type=task_type).first()
                    if pattern:
                        row.append(pattern.completion_rate * 100)  # Convert to percentage
                    else:
                        row.append(0)
                z_matrix.append(row)
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=z_matrix,
                x=emotions,
                y=task_types,
                colorscale='RdYlGn',
                hoverongaps=False,
                text=[[f'{val:.1f}%' for val in row] for row in z_matrix],
                texttemplate='%{text}',
                textfont={"size": 10}
            ))
            
            fig.update_layout(
                title='Task Completion Rate by Emotion (%)',
                xaxis_title='Emotion',
                yaxis_title='Task Type',
                height=500
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            print(f"Heatmap error: {e}")
            return "<p>Error generating heatmap</p>"
    
    def generate_energy_curve_chart(self, user, days=7):
        """Generate daily emotional energy curve"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get emotion records grouped by hour
            emotion_records = EmotionRecord.objects.filter(
                user=user,
                timestamp__gte=cutoff_date
            )
            
            if not emotion_records.exists():
                return "<p>No emotion data available</p>"
            
            # Create hourly energy data
            hourly_data = {}
            for record in emotion_records:
                hour = record.timestamp.hour
                energy_score = self._calculate_energy_score(record.emotion)
                
                if hour not in hourly_data:
                    hourly_data[hour] = []
                hourly_data[hour].append(energy_score)
            
            # Calculate average energy per hour
            hours = list(range(24))
            avg_energy = []
            for hour in hours:
                if hour in hourly_data:
                    avg_energy.append(np.mean(hourly_data[hour]))
                else:
                    avg_energy.append(0)
            
            # Create energy curve
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hours,
                y=avg_energy,
                mode='lines+markers',
                line=dict(color='#3498DB', width=3),
                marker=dict(size=8),
                name='Average Energy Level'
            ))
            
            # Add energy zones
            fig.add_hrect(
                y0=0.7, y1=1.0,
                fillcolor="green", opacity=0.2,
                layer="below", line_width=0,
                annotation_text="High Energy"
            )
            
            fig.add_hrect(
                y0=0.3, y1=0.7,
                fillcolor="yellow", opacity=0.2,
                layer="below", line_width=0,
                annotation_text="Medium Energy"
            )
            
            fig.add_hrect(
                y0=0.0, y1=0.3,
                fillcolor="red", opacity=0.2,
                layer="below", line_width=0,
                annotation_text="Low Energy"
            )
            
            fig.update_layout(
                title='Daily Emotional Energy Curve',
                xaxis_title='Hour of Day',
                yaxis_title='Energy Level',
                height=400,
                xaxis=dict(tickmode='array', tickvals=hours)
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            print(f"Energy curve error: {e}")
            return "<p>Error generating energy curve</p>"
    
    def generate_multimodal_comparison(self, user, days=7):
        """Generate comparison chart for multimodal emotion detection"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get data from all sensors
            facial_data = EmotionRecord.objects.filter(
                user=user,
                timestamp__gte=cutoff_date
            )
            
            voice_data = VoiceEmotionRecord.objects.filter(
                session__user=user,
                timestamp__gte=cutoff_date
            )
            
            typing_data = TypingEvent.objects.filter(
                pattern__user=user,
                timestamp__gte=cutoff_date,
                inferred_emotion__isnull=False
            )
            
            # Create comparison data
            sensor_data = {
                'Facial Detection': self._aggregate_emotions(facial_data),
                'Voice Analysis': self._aggregate_voice_emotions(voice_data),
                'Typing Patterns': self._aggregate_typing_emotions(typing_data)
            }
            
            # Create grouped bar chart
            fig = go.Figure()
            
            all_emotions = set()
            for sensor_emotions in sensor_data.values():
                all_emotions.update(sensor_emotions.keys())
            
            all_emotions = sorted(list(all_emotions))
            
            for sensor_name, emotions in sensor_data.items():
                values = [emotions.get(emotion, 0) for emotion in all_emotions]
                fig.add_trace(go.Bar(
                    name=sensor_name,
                    x=all_emotions,
                    y=values,
                    marker_color=self._get_sensor_color(sensor_name)
                ))
            
            fig.update_layout(
                title='Multimodal Emotion Detection Comparison',
                xaxis_title='Emotion',
                yaxis_title='Detection Count',
                barmode='group',
                height=500
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            print(f"Multimodal comparison error: {e}")
            return "<p>Error generating comparison chart</p>"
    
    def _calculate_energy_score(self, emotion):
        """Calculate energy score for emotion (0-1 scale)"""
        energy_mapping = {
            'excited': 1.0,
            'happy': 0.8,
            'focused': 0.7,
            'angry': 0.6,
            'stressed': 0.5,
            'neutral': 0.4,
            'surprised': 0.4,
            'calm': 0.3,
            'sad': 0.2,
            'tired': 0.1,
            'fearful': 0.1,
            'disgusted': 0.1
        }
        return energy_mapping.get(emotion, 0.4)
    
    def _aggregate_emotions(self, emotion_records):
        """Aggregate emotion records by emotion type"""
        return emotion_records.values('emotion').annotate(count=Count('emotion')).order_by('-count')
    
    def _aggregate_voice_emotions(self, voice_records):
        """Aggregate voice emotion records"""
        return voice_records.values('emotion').annotate(count=Count('emotion')).order_by('-count')
    
    def _aggregate_typing_emotions(self, typing_records):
        """Aggregate typing emotion records"""
        return typing_records.values('inferred_emotion').annotate(count=Count('inferred_emotion')).order_by('-count')
    
    def _get_sensor_color(self, sensor_name):
        """Get color for sensor type"""
        colors = {
            'Facial Detection': '#3498DB',
            'Voice Analysis': '#E74C3C',
            'Typing Patterns': '#2ECC71'
        }
        return colors.get(sensor_name, '#95A5A6')

# Global visualizer instance
analytics_visualizer = EmotionAnalyticsVisualizer()
