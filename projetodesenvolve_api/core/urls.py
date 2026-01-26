from django.urls import path
from .views import (
    FetchAndCSVView,
    FetchAndCSVStreamView,
    PDFUploadCompletoView,
    PDFUploadPorMesView,
    CSVListView,
    CSVDownloadView,
)

urlpatterns = [
    path('fetch-csv/', FetchAndCSVView.as_view(), name='fetch_csv'),
    path('fetch-csv-stream/', FetchAndCSVStreamView.as_view(), name='fetch_stream'),
    path('pdf/upload/', PDFUploadCompletoView.as_view(), name='pdf_upload_completo'),
    path('pdf/mes/upload/', PDFUploadPorMesView.as_view(), name='pdf_upload_por_mes'),
    path('csv-list/', CSVListView.as_view(), name='csv_list'),
    path('csv-download/<str:filename>/', CSVDownloadView.as_view(), name='csv_download'),
]