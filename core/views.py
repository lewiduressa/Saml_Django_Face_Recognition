from django.conf import settings
from django.urls import reverse
from django.http import (HttpResponse, HttpResponseRedirect, HttpResponseServerError, JsonResponse)
from django.shortcuts import render
import json, base64, cv2

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

import face_recognition
import numpy as np
from pathlib import Path
from core.models import User
from django.contrib.auth import login
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.decorators import login_required


# Create your views here.

BASE_DIR = Path(__file__).resolve().parent.parent
FACE_ENCODINGS = []
FACE_NAMES = []

def init_saml_auth(req):
    SAML_FOLDER = BASE_DIR / 'core/saml'
    auth = OneLogin_Saml2_Auth(req, custom_base_path=str(SAML_FOLDER))
    return auth


def prepare_django_request(request):

    result = {
        'https': 'on' if request.is_secure() else 'off',
        'http_host': request.META['HTTP_HOST'],
        'script_name': request.META['PATH_INFO'],
        'get_data': request.GET.copy(),
        'post_data': request.POST.copy()
    }
    return result

def fr(frame):
    face_encodings = FACE_ENCODINGS.copy()
    # Resize frame of video to 1/4 size for faster face recognition processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
    name = "Unknown"

    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(
            face_encodings, face_encoding
        )

        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(
            face_encodings, face_encoding
        )
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            
            name = FACE_NAMES[best_match_index]
         
    
    return name

def slo(request):
    req = prepare_django_request(request)
    auth = init_saml_auth(req)
    name_id = session_index = name_id_format = name_id_nq = name_id_spnq = None
    if 'samlNameId' in request.session:
        name_id = request.session['samlNameId']
    if 'samlSessionIndex' in request.session:
        session_index = request.session['samlSessionIndex']
    if 'samlNameIdFormat' in request.session:
        name_id_format = request.session['samlNameIdFormat']
    if 'samlNameIdNameQualifier' in request.session:
        name_id_nq = request.session['samlNameIdNameQualifier']
    if 'samlNameIdSPNameQualifier' in request.session:
        name_id_spnq = request.session['samlNameIdSPNameQualifier']

    return HttpResponseRedirect(auth.logout(name_id=name_id, session_index=session_index, nq=name_id_nq, name_id_format=name_id_format, spnq=name_id_spnq))


def sls(request):
    errors = []
    error_reason = None
    not_auth_warn = False
    attributes = False
    paint_logout = False
    request_id = None
    request.session.flush()     # line added to go around MS Azure bug of not signing slo response

    success_slo = True

    return render(request, 'app2.html', {'errors': errors, 'error_reason': error_reason, 'not_auth_warn': not_auth_warn, 'success_slo': success_slo,
                                        'attributes': attributes, 'paint_logout': paint_logout})

def attrs(request):
    paint_logout = False
    attributes = False

    if 'samlUserdata' in request.session:
        paint_logout = True
        if len(request.session['samlUserdata']) > 0:
            attributes = request.session['samlUserdata'].items()
    return render(request, 'attrs.html',
                  {'paint_logout': paint_logout,
                   'attributes': attributes})

def metadata(request):
    # req = prepare_django_request(request)
    # auth = init_saml_auth(req)
    # saml_settings = auth.get_settings()
    saml_settings = OneLogin_Saml2_Settings(settings=None, custom_base_path=settings.SAML_FOLDER, sp_validation_only=True)
    metadata = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = HttpResponse(content=metadata, content_type='text/xml')
    else:
        resp = HttpResponseServerError(content=', '.join(errors))
    return resp


def root(request):
    req = prepare_django_request(request)
    auth = init_saml_auth(req)
    errors = []
    error_reason = None
    not_auth_warn = False
    success_slo = False
    attributes = False
    paint_logout = False

    if 'sso' in req['get_data']:
        return HttpResponseRedirect(auth.login())
    
    if request.method == 'POST':
        request_id = None  
        if 'AuthNRequestID' in request.session:
            request_id = request.session['AuthNRequestID']
        
        auth.process_response(request_id=request_id)
        errors = auth.get_errors()
        not_auth_warn = not auth.is_authenticated()

        if not errors and auth.is_authenticated():
            uemail = auth.get_attributes().get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress')[0]
            uname = auth.get_attributes().get('http://schemas.microsoft.com/identity/claims/displayname')[0]
            user, created = AuthUser.objects.get_or_create(username=uemail, defaults={'first_name': uname})
            if not created:
                user.first_name = uname
                user.save

            login(request, user)

            if 'AuthNRequestID' in request.session:
                del request.session['AuthNRequestID']
        elif auth.get_settings().is_debug_active():
            error_reason = auth.get_last_error_reason()

        paint_logout = not not_auth_warn
            
    print("serving root page")
    return render(request, "index.html", {'errors': errors, 'error_reason': error_reason, 'not_auth_warn': not_auth_warn, 'success_slo': success_slo,
                                          'attributes': attributes, 'paint_logout': paint_logout})

@login_required
def face_rec(request):
    if (request.method == 'POST'):
        try:
            data = json.loads(request.body)
            
            base64img = bytes(data.get('base64img').split(',')[1], 'utf-8')
            decodedImg = base64.b64decode(base64img)

            with open(f"core/img/{request.user.username}.jpg", "wb") as fh:
                fh.write(decodedImg)
            
            FACE_ENCODINGS.append(face_recognition.face_encodings(face_recognition.load_image_file(BASE_DIR / f"core/img/{request.user.username}.jpg"))[0])
            FACE_NAMES.append(request.user.first_name)

            return JsonResponse({'message': 'Success'}, status=200)

        except Exception as e:
            return JsonResponse({'message': 'Internal error'}, status=500)

        
@login_required
def face_rec2(request):
    if (request.method == 'POST'):
        try:
            data = json.loads(request.body)
            base64img = bytes(data.get('base64img').split(',')[1], 'utf-8')
            decodedImg = base64.b64decode(base64img)
            
            # Populate FACE_ENCODINGS and FACE_NAMES
            if len(FACE_ENCODINGS) == 0:
                d = Path(BASE_DIR / 'core/img')
                for f in d.iterdir():
                    uemail = f"{f.name}"[:-4]
                    uobjects = AuthUser.objects.filter(username=uemail)
                    if len(uobjects) != 0:
                        e = AuthUser.objects.filter(username=f"{f.name}").first()
                        face_img = face_recognition.load_image_file(BASE_DIR / f"core/img/{f.name}")
                        img_encoding = face_recognition.face_encodings(face_img)
                        FACE_ENCODINGS.append(img_encoding)
                        uname = uobjects.first().first_name
                        FACE_NAMES.append(uname)
            
            name = fr(cv2.imdecode(np.frombuffer(decodedImg, np.uint8), cv2.IMREAD_ANYCOLOR))
          
            
            return JsonResponse({'message': 'Success', 'name': name}, status=200)    
        except Exception as e:
            print(e)
            return JsonResponse({'message': 'Internal error'}, status=500)

def error_404(request, exception):
    print("404 triggered")
    return render(request, "404.html", status=404)

def error_500(request):
    print("500 triggered")
    return render(request, "500.html", status=500)

