from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import AMC, Scheme, SchemeCategory
from .serializers import AMCSerializer, SchemeSerializer, SchemeCategorySerializer
from .utils.parsers import import_schemes_from_file, import_navs_from_file

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class AMCListCreateAPIView(generics.ListCreateAPIView):
    queryset = AMC.objects.all().order_by('name')
    serializer_class = AMCSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']

class AMCDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AMC.objects.all()
    serializer_class = AMCSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class SchemeListAPIView(generics.ListAPIView):
    queryset = Scheme.objects.select_related('amc', 'category').all().order_by('name')
    serializer_class = SchemeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['amc', 'category', 'scheme_type', 'scheme_plan', 'riskometer']
    search_fields = ['name', 'scheme_code', 'isin']
    ordering_fields = ['name', 'aum', 'min_purchase_amount']

class SchemeCategoryListAPIView(generics.ListAPIView):
    queryset = SchemeCategory.objects.all().order_by('name')
    serializer_class = SchemeCategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

class SchemeUploadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES['file']
        try:
            count, errors = import_schemes_from_file(file_obj)
            return Response({
                'message': f'Successfully processed {count} schemes.',
                'errors': errors
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NAVUploadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES['file']
        try:
            count, errors = import_navs_from_file(file_obj)
            return Response({
                'message': f'Successfully processed {count} NAV records.',
                'errors': errors
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
