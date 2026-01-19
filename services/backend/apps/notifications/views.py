from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from .models import Notification, EmailTemplate
from .serializers import NotificationSerializer, EmailTemplateSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        notifications = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'message': f'{updated} notifications marked as read'})
    
    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        deleted_count = self.get_queryset().filter(is_read=True).delete()[0]
        return Response({'message': f'{deleted_count} notifications deleted'})


class EmailTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    
    @action(detail=True, methods=['post'])
    def test_send(self, request, pk=None):
        template = self.get_object()
        test_email = request.data.get('email', request.user.email)
        
        from .tasks import send_email_task
        send_email_task.delay(
            recipient_email=test_email,
            subject=f"[TEST] {template.subject}",
            html_content=template.html_content,
            text_content=template.text_content,
            template_type=template.template_type
        )
        
        return Response({'message': f'Test email sent to {test_email}'})
