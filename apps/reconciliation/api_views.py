from rest_framework import generics, status, parsers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import RTAFile
from .serializers import RTAFileSerializer
from .parsers import CAMSParser, KarvyParser, FranklinParser, CAMSXLSParser, KarvyXLSParser
import threading
from django.db import connections

class ReconciliationAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = RTAFileSerializer
    queryset = RTAFile.objects.all().order_by('-uploaded_at')
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def perform_create(self, serializer):
        rta_file = serializer.save(file_name=self.request.FILES['file'].name)

        # Trigger Parser Sync
        parser = None
        filename = rta_file.file_name.lower()

        if rta_file.rta_type == RTAFile.RTA_CAMS:
            if filename.endswith('.xls') or filename.endswith('.xlsx'):
                parser = CAMSXLSParser(rta_file)
            else:
                parser = CAMSParser(rta_file)
        elif rta_file.rta_type == RTAFile.RTA_KARVY:
            if filename.endswith('.xls') or filename.endswith('.xlsx'):
                    parser = KarvyXLSParser(rta_file)
            else:
                parser = KarvyParser(rta_file)
        elif rta_file.rta_type == RTAFile.RTA_FRANKLIN:
            parser = FranklinParser(rta_file)

        if parser:
            def run_parser():
                try:
                    parser.parse()
                finally:
                    connections.close_all()

            thread = threading.Thread(target=run_parser)
            thread.start()
        else:
            rta_file.status = RTAFile.STATUS_FAILED
            rta_file.error_log = "Unknown RTA Type"
            rta_file.save()
