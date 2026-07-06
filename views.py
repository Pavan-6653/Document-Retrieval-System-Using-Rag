from django.shortcuts import render
from django.http import HttpResponse
from transformers import pipeline
import pymysql
from datetime import date
import numpy as np
from numpy import dot
from numpy.linalg import norm
import os
import torch
from .model_loader import get_models


global uname

qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")


# ---------------- GENERATION ---------------- #

def GenerationAction(request):
    if request.method == 'POST':
        query = request.POST.get('t1')
        upload_dir = "RagApp/static/files"

        txt_files = [
            os.path.join(upload_dir, f)
            for f in os.listdir(upload_dir)
            if f.lower().endswith(".txt")
        ]

        if not txt_files:
            answer = "No text document uploaded."
        else:
            latest_file = max(txt_files, key=os.path.getmtime)

            with open(latest_file, "r", encoding="utf-8", errors="ignore") as f:
                context_text = f.read()

            result = qa_pipeline(question=query, context=context_text)

            answer = result["answer"].strip()
            score = result["score"]

            if answer == "" or score < 0.30:
                answer = "Answer not found in the recently uploaded document."

        output = "<b>Input Text :</b> " + query + "<br/><br/><b>Generated Text :</b> " + answer
        return render(request, "Generation.html", {"data": output})


def Generation(request):
    return render(request, 'Generation.html', {})


def Retrieval(request):
    return render(request, 'Retrieval.html', {})


# ---------------- DOWNLOAD ---------------- #

def DownloadFile(request):
    name = request.GET.get('name', False)
    filepath = os.path.join('RagApp/static/files', name)

    if not os.path.exists(filepath):
        return HttpResponse("File not found")

    with open(filepath, "rb") as file:
        response = HttpResponse(file.read(), content_type='application/force-download')
        response['Content-Disposition'] = f'attachment; filename={name}'
        return response


# ---------------- RETRIEVAL (FIXED) ---------------- #

def RetrievalAction(request):
    if request.method == 'POST':
        tokenizer, retriever, model = get_models()

        query_text = request.POST.get('t1', '').strip().lower()

        documents = []
        names = []
        rag_vectors = []

        base_path = 'RagApp/static/files'

        for filename in os.listdir(base_path):
            filepath = os.path.join(base_path, filename)

            # ✅ READ SAFELY (FIXED)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
                    data = file.read()
            except:
                continue  # skip unreadable files

            if not data.strip():
                continue

            names.append(filename)

            if len(data) > 2500:
                data = data[:2500]

            data = data.strip().lower()

            # Encode document
            inputs = tokenizer(data, return_tensors="pt", truncation=True)
            input_ids = inputs["input_ids"]

            with torch.no_grad():
                doc_vector = model.question_encoder(input_ids)[0]

            doc_vector = doc_vector.detach().numpy().ravel()
            rag_vectors.append(doc_vector)

        if not rag_vectors:
            return render(request, 'UserScreen.html', {"data": "No valid documents found."})

        rag_vectors = np.asarray(rag_vectors)

        # Encode query
        inputs = tokenizer(query_text, return_tensors="pt", truncation=True)
        input_ids = inputs["input_ids"]

        with torch.no_grad():
            query_vector = model.question_encoder(input_ids)[0]

        query_vector = query_vector.detach().numpy().ravel()

        # Compute similarity
        search_results = []

        for i in range(len(rag_vectors)):
            if norm(rag_vectors[i]) == 0 or norm(query_vector) == 0:
                continue

            score = dot(rag_vectors[i], query_vector) / (norm(rag_vectors[i]) * norm(query_vector))

            if score > 0.50:
                search_results.append([names[i], float(score)])

        search_results.sort(key=lambda x: x[1], reverse=True)

        # Build HTML
        result = "<table border=1 align=center><tr><th>File Name</th><th>Score</th><th>Download</th></tr>"

        for file_name, score in search_results:
            result += f"<tr><td>{file_name}</td><td>{score:.4f}</td>"
            result += f"<td><a href='DownloadFile?name={file_name}'>Download</a></td></tr>"

        result += "</table><br/><br/>"

        return render(request, 'UserScreen.html', {'data': result})


# ---------------- UPLOAD ---------------- #

def UploadDocumentAction(request):
    if request.method == 'POST':
        global uname

        uploaded_file = request.FILES['t1']
        fname = uploaded_file.name
        filepath = os.path.join("RagApp/static/files", fname)

        if os.path.exists(filepath):
            os.remove(filepath)

        # ✅ SAVE FILE SAFELY
        with open(filepath, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        current_date = str(date.today())

        db_connection = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='rag',
            charset='utf8'
        )

        db_cursor = db_connection.cursor()

        sql = "INSERT INTO documents VALUES (%s, %s, %s)"
        db_cursor.execute(sql, (uname, fname, current_date))

        db_connection.commit()

        status = "Document successfully uploaded" if db_cursor.rowcount == 1 else "Upload failed"

        return render(request, 'UploadDocument.html', {
            'data': f'<font size="3" color="blue">{status}</font>'
        })


def UploadDocument(request):
    return render(request, 'UploadDocument.html', {})


# ---------------- AUTH ---------------- #

def UserLogin(request):
    return render(request, 'UserLogin.html', {})


def Register(request):
    return render(request, 'Register.html', {})


def Aboutus(request):
    return render(request, 'Aboutus.html', {})


def index(request):
    return render(request, 'index.html', {})


def Contactus(request):
    name = "Ameerpet"
    output = f'<iframe width="625" height="350" src="https://maps.google.com/maps?q={name}&output=embed"></iframe>'
    return render(request, 'Contactus.html', {'data1': output})


def RegisterAction(request):
    if request.method == 'POST':
        username = request.POST.get('t1')
        password = request.POST.get('t2')
        contact = request.POST.get('t3')
        email = request.POST.get('t4')
        address = request.POST.get('t5')

        con = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='rag')

        with con:
            cur = con.cursor()
            cur.execute("SELECT username FROM register")
            if any(row[0] == username for row in cur.fetchall()):
                return render(request, 'Register.html', {'data': 'Username already exists'})

        db = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='rag')
        cur = db.cursor()

        cur.execute(
            "INSERT INTO register VALUES (%s, %s, %s, %s, %s)",
            (username, password, contact, email, address)
        )

        db.commit()

        return render(request, 'Register.html', {'data': 'Signup successful'})


def UserLoginAction(request):
    if request.method == 'POST':
        global uname

        username = request.POST.get('t1')
        password = request.POST.get('t2')

        con = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='rag')

        with con:
            cur = con.cursor()
            cur.execute("SELECT username, password FROM register")

            for row in cur.fetchall():
                if row[0] == username and row[1] == password:
                    uname = username
                    return render(request, 'UserScreen.html', {'data': 'Welcome ' + username})

        return render(request, 'UserLogin.html', {'data': 'Login failed'})