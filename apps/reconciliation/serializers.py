from rest_framework import serializers
from .models import RTAFile

class RTAFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RTAFile
        fields = ['id', 'rta_type', 'file', 'file_name', 'status', 'uploaded_at', 'error_log']
        read_only_fields = ['file_name', 'status', 'uploaded_at', 'error_log']
