from rest_framework import serializers
from .models import Notification, EmailTemplate


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'link', 
                  'is_read', 'read_at', 'created_at']
        read_only_fields = ['id', 'created_at', 'read_at']


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ['id', 'name', 'template_type', 'subject', 'html_content', 
                  'text_content', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']