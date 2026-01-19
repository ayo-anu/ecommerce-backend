from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from .models import (
    DailySales, ProductAnalytics, CategoryAnalytics, 
    UserActivity, SalesReport, CustomerSegment
)
from .serializers import (
    DailySalesSerializer, ProductAnalyticsSerializer,
    CategoryAnalyticsSerializer, UserActivitySerializer,
    SalesReportSerializer, DashboardStatsSerializer
)
from apps.orders.models import Order
from apps.products.models import Product


class AnalyticsDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        previous_start = start_date - timedelta(days=30)
        
        current_orders = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            payment_status='paid'
        )
        
        current_stats = current_orders.aggregate(
            total_revenue=Sum('total'),
            total_orders=Count('id'),
            average_order_value=Avg('total')
        )
        
        previous_orders = Order.objects.filter(
            created_at__date__gte=previous_start,
            created_at__date__lt=start_date,
            payment_status='paid'
        )
        
        previous_stats = previous_orders.aggregate(
            total_revenue=Sum('total'),
            total_orders=Count('id')
        )
        
        revenue_growth = self._calculate_growth(
            current_stats['total_revenue'], 
            previous_stats['total_revenue']
        )
        order_growth = self._calculate_growth(
            current_stats['total_orders'],
            previous_stats['total_orders']
        )
        
        current_customers = current_orders.values('user').distinct().count()
        previous_customers = previous_orders.values('user').distinct().count()
        customer_growth = self._calculate_growth(current_customers, previous_customers)
        
        top_products = ProductAnalytics.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values(
            'product__name', 'product__id'
        ).annotate(
            total_revenue=Sum('revenue'),
            total_sold=Sum('units_sold')
        ).order_by('-total_revenue')[:10]
        
        top_categories = CategoryAnalytics.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values(
            'category__name'
        ).annotate(
            total_revenue=Sum('total_revenue')
        ).order_by('-total_revenue')[:5]
        
        daily_sales = DailySales.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        sales_chart_data = {
            'labels': [str(sale.date) for sale in daily_sales],
            'revenue': [float(sale.total_revenue) for sale in daily_sales],
            'orders': [sale.total_orders for sale in daily_sales]
        }
        
        recent_orders = Order.objects.filter(
            payment_status='paid'
        ).select_related('user').prefetch_related('items').order_by('-created_at')[:10]
        
        recent_orders_data = [{
            'id': str(order.id),
            'order_number': order.order_number,
            'customer': order.user.email,
            'total': float(order.total),
            'status': order.status,
            'created_at': order.created_at.isoformat()
        } for order in recent_orders]
        
        data = {
            'total_revenue': current_stats['total_revenue'] or 0,
            'total_orders': current_stats['total_orders'] or 0,
            'total_customers': current_customers,
            'average_order_value': current_stats['average_order_value'] or 0,
            'revenue_growth': revenue_growth,
            'order_growth': order_growth,
            'customer_growth': customer_growth,
            'top_products': list(top_products),
            'top_categories': list(top_categories),
            'recent_orders': recent_orders_data,
            'sales_chart_data': sales_chart_data
        }
        
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)
    
    def _calculate_growth(self, current, previous):
        if current is None:
            current = 0
        if previous is None:
            previous = 0
        
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)
    
    @action(detail=False, methods=['get'])
    def sales_trend(self, request):
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_sales = DailySales.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        serializer = DailySalesSerializer(daily_sales, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def product_performance(self, request):
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        product_analytics = ProductAnalytics.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('product')
        
        serializer = ProductAnalyticsSerializer(product_analytics, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def category_performance(self, request):
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        category_analytics = CategoryAnalytics.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('category')
        
        serializer = CategoryAnalyticsSerializer(category_analytics, many=True)
        return Response(serializer.data)


class UserActivityViewSet(viewsets.ModelViewSet):
    queryset = UserActivity.objects.all()
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return UserActivity.objects.all().select_related('user', 'product', 'category')
        return UserActivity.objects.filter(user=user).select_related('product', 'category')

    
    def perform_create(self, serializer):
        session_id = self.request.session.session_key or self.request.META.get('HTTP_X_SESSION_ID', '')
        
        serializer.save(
            user=self.request.user if self.request.user.is_authenticated else None,
            session_id=session_id,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            referrer=self.request.META.get('HTTP_REFERER', '')
        )
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class SalesReportViewSet(viewsets.ModelViewSet):
    queryset = SalesReport.objects.all()
    serializer_class = SalesReportSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        report_type = request.data.get('report_type', 'daily')
        start_date = datetime.strptime(request.data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.data.get('end_date'), '%Y-%m-%d').date()
        
        from .tasks import generate_sales_report
        result = generate_sales_report.delay(report_type, str(start_date), str(end_date), request.user.id)
        
        return Response({
            'message': 'Report generation started',
            'task_id': result.id
        }, status=status.HTTP_202_ACCEPTED)
