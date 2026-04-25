import os, joblib, json
import pandas as pd
import numpy as np
from docx import Document
from pypdf import PdfReader
import re

from django.conf import settings
from django.contrib.auth import authenticate
from django.shortcuts import render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import PredictionHistory, UserProfile
from .serializers import RegisterSerializer, UserSerializer, PredictionHistorySerializer, UserProfileSerializer


# ------------------------ LOAD MODELS ------------------------
PIPELINE_PATH = os.path.join(settings.BASE_DIR, "artifacts", "pipeline.pkl")
LE_PATH = os.path.join(settings.BASE_DIR, "artifacts", "label_encoder.pkl")

PIPELINE = None
LE = None
PIPELINE_MTIME = None
LE_MTIME = None


def load_artifacts(force=False):
    global PIPELINE, LE, PIPELINE_MTIME, LE_MTIME

    pipeline_mtime = os.path.getmtime(PIPELINE_PATH)
    le_mtime = os.path.getmtime(LE_PATH)

    if force or PIPELINE is None or PIPELINE_MTIME != pipeline_mtime:
        PIPELINE = joblib.load(PIPELINE_PATH)
        PIPELINE_MTIME = pipeline_mtime
        print("ML Pipeline Loaded Successfully!")

    if force or LE is None or LE_MTIME != le_mtime:
        LE = joblib.load(LE_PATH)
        LE_MTIME = le_mtime
        print("Label Encoder Loaded Successfully!")

try:
    load_artifacts(force=True)
except Exception as e:
    print("❌ Pipeline Load Error:", e)


def _extract_resume_text(uploaded_file):
    """Extract text from txt/pdf/docx resume uploads."""
    if uploaded_file is None:
        return ""

    max_size = 5 * 1024 * 1024  # 5MB
    if uploaded_file.size and uploaded_file.size > max_size:
        raise ValueError("Resume file is too large. Please upload a file smaller than 5MB.")

    filename = (uploaded_file.name or "").lower()

    if filename.endswith('.txt'):
        return uploaded_file.read().decode('utf-8', errors='ignore').strip()

    if filename.endswith('.pdf'):
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages).strip()

    if filename.endswith('.docx'):
        uploaded_file.seek(0)
        doc = Document(uploaded_file)
        lines = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(lines).strip()

    raise ValueError("Unsupported resume format. Please upload .txt, .pdf, or .docx")


def _to_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    return float(value)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parse_resume_view(request):
    """Accepts multipart resume file and returns extracted skills as a list."""
    resume_file = request.FILES.get('resume')
    if not resume_file:
        return Response({"error": "No resume file uploaded"}, status=400)

    try:
        text = _extract_resume_text(resume_file)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    text_l = (text or "").lower()

    SKILL_VOCAB = [
        'python','java','javascript','react','angular','vue','django','flask',
        'sql','postgresql','mysql','mongodb','aws','azure','google cloud','gcp',
        'docker','kubernetes','git','linux','c++','c#','php','ruby','node','express',
        'tensorflow','pytorch','scikit-learn','nlp','computer vision','aws certified',
        'data science','machine learning','deep learning','devops','html','css',
        'rest api','graphql','jira','agile','spark','hadoop','excel','tableau',
        'power bi','business intelligence','qa','testing','selenium','cisco','networking'
    ]

    found = []
    for skill in SKILL_VOCAB:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_l):
            found.append(skill)

    if 'c++' not in found and re.search(r'\bc\+\+\b', text_l):
        found.append('c++')

    found_unique = []
    for s in found:
        if s not in found_unique:
            found_unique.append(s)
        if len(found_unique) >= 20:
            break

    return Response({"skills": found_unique})



# ------------------------ REGISTER ------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "User registered successfully"}, status=201)
    return Response(serializer.errors, status=400)



# ------------------------ LOGIN ------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "username": user.username
        })
    
    return Response({"error": "Invalid username or password"}, status=401)



# ------------------------ PROFILE ------------------------
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method in ['PUT', 'PATCH']:
        user = request.user
        user_fields = {
            'first_name': request.data.get('first_name'),
            'last_name': request.data.get('last_name'),
            'email': request.data.get('email'),
            'username': request.data.get('username'),
        }

        for field_name, value in user_fields.items():
            if value is not None:
                setattr(user, field_name, value)
        user.save()

        incoming_form_data = request.data.get('form_data')
        if isinstance(incoming_form_data, dict):
            profile.form_data = incoming_form_data
            profile.save()

    profile_data = UserProfileSerializer(profile).data
    return Response({
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'form_data': profile_data.get('form_data', {}),
        'updated_at': profile_data.get('updated_at'),
    })



# ------------------------ PREDICT ------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def predict_view(request):

    # check model loaded
    try:
        load_artifacts()
    except Exception as e:
        return Response({"error": f"Model not loaded on server: {e}"}, status=500)

    if PIPELINE is None or LE is None:
        return Response({"error": "Model not loaded on server"}, status=500)

    data = request.data
    resume_file = request.FILES.get("resume")

    resume_text = ""
    resume_used = False
    resume_filename = None
    if resume_file is not None:
        try:
            resume_text = _extract_resume_text(resume_file)
            resume_used = bool(resume_text)
            resume_filename = resume_file.name
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception:
            return Response({"error": "Unable to read resume file. Try another file."}, status=400)

    try:
        cgpa = _to_float(data.get("CGPA"), default=0.0)
        experience = _to_float(data.get("Years of Experience"), default=0.0)
    except (TypeError, ValueError):
        return Response({
            "error": "CGPA and Years of Experience must be valid numbers"
        }, status=400)

    manual_signals = [
        data.get("Degree"),
        data.get("Major"),
        data.get("Specialization"),
        data.get("Certification"),
        data.get("Preferred Industry"),
        data.get("Skills") or data.get("skills"),
        data.get("CGPA"),
        data.get("Years of Experience"),
    ]
    if not any((str(v).strip() if v is not None else "") for v in manual_signals) and not resume_used:
        return Response({
            "error": "Please fill prediction fields or upload a resume"
        }, status=400)

    skills_text = (data.get("Skills") or data.get("skills") or "").strip()
    if resume_text:
        # Keep only a useful chunk to avoid oversized payload for vectorizer.
        resume_chunk = resume_text.replace('\x00', ' ')[:5000]
        skills_text = f"{skills_text}, {resume_chunk}".strip(", ")

    # Construct row for prediction
    row = {
        "CGPA": cgpa,
        "Years of Experience": experience,
        "Degree": (data.get("Degree") or "Unknown").strip(),
        "Major": (data.get("Major") or "Unknown").strip(),
        "Specialization": (data.get("Specialization") or "Unknown").strip(),
        "Certification": (data.get("Certification") or "Unknown").strip(),
        "Preferred Industry": (data.get("Preferred Industry") or "Unknown").strip(),
        "Skills": skills_text
    }

    df = pd.DataFrame([row])

    try:
        # Prediction
        pred_enc = PIPELINE.predict(df)
        if LE is not None:
            try:
                pred_label = LE.inverse_transform(pred_enc)[0]
            except Exception:
                pred_label = str(pred_enc[0])
        else:
            pred_label = str(pred_enc[0])

        # Probability for all classes
        top3_roles = [pred_label]
        top3_prob = []
        if hasattr(PIPELINE, "predict_proba"):
            prob = PIPELINE.predict_proba(df)[0]

            # Top 3 roles
            top3_idx = np.argsort(prob)[::-1][:3]

            if LE is not None:
                try:
                    top3_roles = LE.inverse_transform(top3_idx).tolist()
                except Exception:
                    classes = getattr(PIPELINE, "classes_", None)
                    if classes is not None:
                        top3_roles = [str(classes[i]) for i in top3_idx]
                    else:
                        top3_roles = [str(i) for i in top3_idx]
            else:
                classes = getattr(PIPELINE, "classes_", None)
                if classes is not None:
                    top3_roles = [str(classes[i]) for i in top3_idx]
                else:
                    top3_roles = [str(i) for i in top3_idx]

            top3_prob = (prob[top3_idx] * 100).round(2).tolist()

        # Save history
        PredictionHistory.objects.create(
            user=request.user,
            input_data=json.dumps(row),
            predicted=pred_label,
            meta={
                "resume_used": resume_used,
                "resume_filename": resume_filename
            }
        )

        # FINAL result for result.html
        return Response({
            "predicted_role": pred_label,
            "top3_roles": top3_roles,
            "top3_probabilities": top3_prob,
            "resume_used": resume_used,
            "resume_filename": resume_filename
        })

    except Exception as e:
        error_text = str(e).lower()
        if "idf" in error_text and "fit" in error_text:
            try:
                load_artifacts(force=True)
                pred_enc = PIPELINE.predict(df)
                if LE is not None:
                    try:
                        pred_label = LE.inverse_transform(pred_enc)[0]
                    except Exception:
                        pred_label = str(pred_enc[0])
                else:
                    pred_label = str(pred_enc[0])

                top3_roles = [pred_label]
                top3_prob = []
                if hasattr(PIPELINE, "predict_proba"):
                    prob = PIPELINE.predict_proba(df)[0]
                    top3_idx = np.argsort(prob)[::-1][:3]

                    if LE is not None:
                        try:
                            top3_roles = LE.inverse_transform(top3_idx).tolist()
                        except Exception:
                            classes = getattr(PIPELINE, "classes_", None)
                            if classes is not None:
                                top3_roles = [str(classes[i]) for i in top3_idx]
                            else:
                                top3_roles = [str(i) for i in top3_idx]
                    else:
                        classes = getattr(PIPELINE, "classes_", None)
                        if classes is not None:
                            top3_roles = [str(classes[i]) for i in top3_idx]
                        else:
                            top3_roles = [str(i) for i in top3_idx]

                    top3_prob = (prob[top3_idx] * 100).round(2).tolist()

                PredictionHistory.objects.create(
                    user=request.user,
                    input_data=json.dumps(row),
                    predicted=pred_label,
                    meta={
                        "resume_used": resume_used,
                        "resume_filename": resume_filename
                    }
                )

                return Response({
                    "predicted_role": pred_label,
                    "top3_roles": top3_roles,
                    "top3_probabilities": top3_prob,
                    "resume_used": resume_used,
                    "resume_filename": resume_filename
                })
            except Exception:
                pass

        return Response({"error": str(e)}, status=500)



# ------------------------ HISTORY ------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history_view(request):
    qs = PredictionHistory.objects.filter(user=request.user).order_by("-created_at")
    ser = PredictionHistorySerializer(qs, many=True)
    return Response(ser.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def history_delete_view(request, history_id):
    record = PredictionHistory.objects.filter(id=history_id, user=request.user).first()
    if not record:
        return Response({"error": "History record not found"}, status=404)

    record.delete()
    return Response({"message": "History record deleted"}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    refresh_token = request.data.get("refresh")

    # For JWT setups without blacklist app, logout still succeeds client-side by removing tokens.
    if not refresh_token:
        return Response({"message": "Logged out"}, status=200)

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except (TokenError, AttributeError, Exception):
        pass

    return Response({"message": "Logged out"}, status=200)




