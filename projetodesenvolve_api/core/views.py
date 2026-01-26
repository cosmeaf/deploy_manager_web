import json
import os
import csv
import time
from io import BytesIO, StringIO
from datetime import datetime
import base64

from django.http import HttpResponse, StreamingHttpResponse, FileResponse
from django.views import View
from django.core.files.storage import FileSystemStorage
from django.utils import timezone  # Para fuso horário correto
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import requests
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER

from dotenv import load_dotenv
load_dotenv()

# CONFIGURAÇÃO GLOBAL DE FUSO HORÁRIO
TIME_ZONE = 'America/Sao_Paulo'
timezone.activate(timezone.get_fixed_timezone(-180))  

BASE_URL = os.getenv("BASE_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not all([BASE_URL, CLIENT_ID, CLIENT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD]):
    raise ValueError("Variáveis de ambiente faltando no .env")

USERS_FILE = "users.json"

USUARIOS_IGNORAR = {
    "login_service_user", "notes", "cms", "mariana_admin", "admin",
    "Instrutor", "dev", "teste", "Usuarioteste"
}

# Pasta para salvar CSVs
CSV_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media', 'certificados_csv')
os.makedirs(CSV_STORAGE_DIR, exist_ok=True)

# ===================== FUNÇÃO PARA GERAR PDF =====================
def gerar_pdf(dados, titulo_mes="Completo"):
    df = pd.DataFrame(dados)

    if 'created_date' in df.columns:
        df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')

    if titulo_mes != "Completo":
        mes = int(titulo_mes) if titulo_mes.isdigit() else 12
        df = df[df['created_date'].dt.month == mes]

    if df.empty:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph("Nenhum certificado encontrado para o período.", styles['Normal'])]
        doc.build(story)
        buffer.seek(0)
        return buffer

    df['grade_float'] = pd.to_numeric(df['grade'], errors='coerce')

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    PRIMARY_COLOR = rl_colors.HexColor("#003366")
    GRAY = rl_colors.HexColor("#666666")

    title_style = ParagraphStyle('TitleCustom', parent=styles['Heading1'], fontSize=28,
                                 spaceAfter=30, alignment=TA_CENTER, textColor=PRIMARY_COLOR,
                                 fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=18,
                                    spaceAfter=40, alignment=TA_CENTER, textColor=GRAY)

    story = []

    story.append(Paragraph("RELATÓRIO DE CERTIFICADOS", title_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Projeto Desenvolve", subtitle_style))
    if titulo_mes != "Completo":
        meses_nomes = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        story.append(Paragraph(f"Mês de Referência: <b>{meses_nomes[int(titulo_mes)]}</b>",
                               ParagraphStyle('Periodo', parent=styles['Normal'], fontSize=16, alignment=TA_CENTER)))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Gerado em: {timezone.localtime(datetime.now()).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    story.append(PageBreak())

    total = len(df)
    alunos = df['username'].nunique()
    cursos = df['course_display_name'].nunique()
    media = df['grade_float'].mean()
    max_nota = df['grade_float'].max()
    min_nota = df['grade_float'].min()

    story.append(Paragraph("Resumo Executivo", styles['Heading1']))
    story.append(Spacer(1, 0.8*cm))

    resumo_data = [
        ["Métrica", "Valor"],
        ["Total de Certificados", f"{total:,}"],
        ["Alunos Únicos", alunos],
        ["Cursos Diferentes", cursos],
        ["Média das Notas", f"{media:.2f}" if not pd.isna(media) else "N/A"],
        ["Nota Máxima", f"{max_nota:.2f}" if not pd.isna(max_nota) else "N/A"],
        ["Nota Mínima", f"{min_nota:.2f}" if not pd.isna(min_nota) else "N/A"],
    ]
    resumo_table = Table(resumo_data, colWidths=[9*cm, 6*cm])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, rl_colors.grey),
    ]))
    story.append(resumo_table)
    story.append(Spacer(1, 1.5*cm))

    # Gráfico em memória
    bins = [0, 0.6, 0.7, 0.8, 0.9, 1.0]
    labels = ['<0.60', '0.60-0.69', '0.70-0.79', '0.80-0.89', '0.90-1.00']
    df['faixa'] = pd.cut(df['grade_float'], bins=bins, labels=labels, include_lowest=True)
    dist = df['faixa'].value_counts().sort_index()

    plt.figure(figsize=(10, 6))
    bars = plt.bar(dist.index.astype(str), dist.values, color="#0099CC", edgecolor="#003366")
    plt.title(f'Distribuição de Notas - {titulo_mes if titulo_mes != "Completo" else "Todos"}')
    plt.xlabel('Faixa de Nota')
    plt.ylabel('Quantidade')
    for bar in bars:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., h + 5, f'{int(h)}', ha='center', va='bottom')
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()

    story.append(Paragraph("Distribuição das Notas", styles['Heading2']))
    story.append(Image(img_buffer, width=15*cm, height=9*cm))
    story.append(PageBreak())

    # Tabela
    story.append(Paragraph("Detalhamento dos Certificados", styles['Heading1']))
    story.append(Spacer(1, 0.5*cm))

    headers = ["Aluno", "Curso", "Nota", "Data de Emissão", "Status"]
    table_data = [headers]
    for _, row in df.iterrows():
        table_data.append([
            row['username'],
            row['course_display_name'],
            row['grade'],
            row['created_date'].strftime('%d/%m/%Y') if pd.notna(row['created_date']) else "N/A",
            "Emitido"
        ])

    detail_table = Table(table_data, colWidths=[4.5*cm, 7*cm, 1.5*cm, 2.5*cm, 2*cm])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F8F9FA")]),
    ]))
    story.append(detail_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

# Rota tradicional: busca, gera CSV, SALVA EM DISCO e retorna download
class FetchAndCSVView(APIView):
    @swagger_auto_schema(operation_description="Busca certificados na API real, salva CSV no servidor e retorna para download.")
    def get(self, request):
        start_time = timezone.localtime(datetime.now())
        print(f"\n[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] === BUSCA TRADICIONAL INICIADA ===")

        if not os.path.exists(USERS_FILE):
            return Response({"error": "users.json não encontrado."}, status=500)

        with open(USERS_FILE, "r", encoding="utf-8") as f:
            usernames = json.load(f)

        print(f"Carregados {len(usernames)} usuários.")

        # Token
        token_url = f"{BASE_URL}/oauth2/access_token/"
        payload = {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "scope": "read write"
        }

        try:
            resp_token = requests.post(token_url, data=payload, timeout=10)
            resp_token.raise_for_status()
            access_token = resp_token.json()["access_token"]
        except Exception as e:
            print(f"ERRO TOKEN: {str(e)}")
            return Response({"error": f"Erro ao obter token: {str(e)}"}, status=500)

        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        all_certificates = []

        for username in usernames:
            if username.lower() in {u.lower() for u in USUARIOS_IGNORAR}:
                continue

            url = f"{BASE_URL}/api/certificates/v0/certificates/{username}/"

            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code in [404, 500]:
                    continue
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if isinstance(data, list):
                    all_certificates.extend(data)
            except Exception:
                continue

            time.sleep(0.3)

        if not all_certificates:
            return Response({"message": "Nenhum certificado encontrado."}, status=200)

        # Gerar CSV
        buffer = StringIO(newline='')
        writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)

        headers_csv = [
            "username", "course_display_name", "course_id", "course_organization",
            "grade", "certificate_type", "status", "is_passing",
            "created_date", "modified_date", "download_url"
        ]
        writer.writerow(headers_csv)

        for cert in all_certificates:
            row = [str(cert.get(k, "")) for k in headers_csv]
            writer.writerow(row)

        csv_content = buffer.getvalue().encode('utf-8')
        buffer.close()

        # SALVAR EM DISCO
        fs = FileSystemStorage(location=CSV_STORAGE_DIR)
        filename = f"certificados_{timezone.localtime(datetime.now()).strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = fs.save(filename, BytesIO(csv_content))

        print(f"CSV SALVO AUTOMATICAMENTE EM DISCO: {file_path}")

        # Retorna para download no frontend
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

# Rota SSE: streaming de logs e progresso (salva CSV ao final)
class FetchAndCSVStreamView(View):
    def get(self, request):
        def event_stream():
            start_time = timezone.localtime(datetime.now())
            yield f"data: {json.dumps({'type': 'start', 'time': start_time.isoformat()})}\n\n"

            if not os.path.exists(USERS_FILE):
                yield f"data: {json.dumps({'type': 'error', 'message': 'users.json não encontrado'})}\n\n"
                return

            with open(USERS_FILE, "r", encoding="utf-8") as f:
                usernames = json.load(f)

            total = len(usernames)
            yield f"data: {json.dumps({'type': 'total', 'total': total})}\n\n"

            # Token
            token_url = f"{BASE_URL}/oauth2/access_token/"
            payload = {
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
                "scope": "read write"
            }

            try:
                resp_token = requests.post(token_url, data=payload, timeout=10)
                resp_token.raise_for_status()
                access_token = resp_token.json()["access_token"]
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Token error: {str(e)}'})}\n\n"
                return

            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

            all_certificates = []
            processed = 0

            for idx, username in enumerate(usernames, 1):
                if username.lower() in {u.lower() for u in USUARIOS_IGNORAR}:
                    line = f"[{idx}/{total}] {username} → Ignorando usuário interno"
                    yield f"data: {json.dumps({'type': 'log', 'line': line})}\n\n"
                    processed += 1
                    yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': total})}\n\n"
                    continue

                line = f"[{idx}/{total}] {username.ljust(35)} → "
                yield f"data: {json.dumps({'type': 'log', 'line': line})}\n\n"

                url = f"{BASE_URL}/api/certificates/v0/certificates/{username}/"

                try:
                    resp = requests.get(url, headers=headers, timeout=30)
                    if resp.status_code in [404, 500]:
                        full_line = line + "Nenhum (ou erro interno)"
                        yield f"data: {json.dumps({'type': 'log', 'line': full_line})}\n\n"
                        processed += 1
                        yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': total})}\n\n"
                        continue

                    if resp.status_code != 200:
                        full_line = line + f"Erro {resp.status_code}"
                        yield f"data: {json.dumps({'type': 'log', 'line': full_line})}\n\n"
                        processed += 1
                        yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': total})}\n\n"
                        continue

                    data = resp.json()
                    if isinstance(data, list):
                        count = len(data)
                        all_certificates.extend(data)
                        full_line = line + f"{count} cert(s)"
                    else:
                        full_line = line + "Formato inválido"
                        count = 0

                    yield f"data: {json.dumps({'type': 'log', 'line': full_line})}\n\n"
                except Exception as e:
                    full_line = line + f"Erro: {str(e)}"
                    yield f"data: {json.dumps({'type': 'log', 'line': full_line})}\n\n"

                processed += 1
                yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': total})}\n\n"

                time.sleep(0.3)

            # Finaliza
            yield f"data: {json.dumps({'type': 'complete', 'total_certificados': len(all_certificates)})}\n\n"

            # Gera CSV em base64
            buffer = StringIO()
            writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
            headers_csv = [
                "username", "course_display_name", "course_id", "course_organization",
                "grade", "certificate_type", "status", "is_passing",
                "created_date", "modified_date", "download_url"
            ]
            writer.writerow(headers_csv)
            for cert in all_certificates:
                row = [str(cert.get(k, "")) for k in headers_csv]
                writer.writerow(row)

            csv_content = buffer.getvalue().encode('utf-8')
            csv_base64 = base64.b64encode(csv_content).decode('utf-8')
            buffer.close()

            # SALVAR EM DISCO
            fs = FileSystemStorage(location=CSV_STORAGE_DIR)
            filename = f"certificados_{timezone.localtime(datetime.now()).strftime('%Y%m%d_%H%M%S')}.csv"
            file_path = fs.save(filename, BytesIO(csv_content))

            print(f"CSV SALVO AUTOMATICAMENTE EM DISCO (SSE): {file_path}")

            yield f"data: {json.dumps({'type': 'csv_ready', 'base64': csv_base64})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

# Rotas de PDF (sem mudanças)
class PDFUploadCompletoView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Recebe CSV via upload e gera PDF completo.",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True)
        ]
    )
    def post(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "Arquivo CSV obrigatório."}, status=400)

        csv_file = request.FILES['file']
        try:
            content = csv_file.read().decode('utf-8')
            df = pd.read_csv(StringIO(content))
            dados = df.to_dict('records')
        except Exception as e:
            return Response({"error": f"Erro ao ler CSV: {str(e)}"}, status=400)

        pdf_buffer = gerar_pdf(dados, "Completo")
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_completo.pdf"'
        return response

class PDFUploadPorMesView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Recebe CSV via upload e gera PDF filtrado por mês.",
        manual_parameters=[
            openapi.Parameter('mes', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True)
        ]
    )
    def post(self, request):
        mes_str = request.GET.get('mes')
        if not mes_str or not mes_str.isdigit() or not (1 <= int(mes_str) <= 12):
            return Response({"error": "Mês inválido (1-12)."}, status=400)

        if 'file' not in request.FILES:
            return Response({"error": "Arquivo CSV obrigatório."}, status=400)

        csv_file = request.FILES['file']
        try:
            content = csv_file.read().decode('utf-8')
            df = pd.read_csv(StringIO(content))
            dados = df.to_dict('records')
        except Exception as e:
            return Response({"error": f"Erro ao ler CSV: {str(e)}"}, status=400)

        pdf_buffer = gerar_pdf(dados, mes_str)
        meses_nomes = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="relatorio_{meses_nomes[int(mes_str)]}.pdf"'
        return response

# Lista histórico de CSVs salvos (com data/hora em Brasília)
class CSVListView(APIView):
    def get(self, request):
        files = []
        if os.path.exists(CSV_STORAGE_DIR):
            for f in sorted(os.listdir(CSV_STORAGE_DIR), reverse=True):
                if f.endswith('.csv'):
                    path = os.path.join(CSV_STORAGE_DIR, f)
                    size = os.path.getsize(path)
                    # Data/hora local de Brasília
                    created_utc = datetime.fromtimestamp(os.path.getctime(path))
                    created_br = timezone.localtime(created_utc)
                    created = created_br.strftime('%d/%m/%Y %H:%M:%S')
                    files.append({
                        'filename': f,
                        'created_at': created,
                        'size_mb': round(size / 1024 / 1024, 2),
                        'download_url': f'/api/certificados/csv-download/{f}/'
                    })
        return Response(files)

# Download de CSV salvo
class CSVDownloadView(APIView):
    def get(self, request, filename):
        file_path = os.path.join(CSV_STORAGE_DIR, filename)
        if not os.path.exists(file_path):
            return Response({"error": "Arquivo não encontrado."}, status=404)
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)