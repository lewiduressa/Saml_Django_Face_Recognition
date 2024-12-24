from django.conf import settings
from django.urls import reverse
from django.http import (HttpResponse, HttpResponseRedirect, HttpResponseServerError)
from django.shortcuts import render
from pathlib import Path

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

BASE_DIR = Path(__file__).resolve().parent.parent

def init_saml_auth(req):
    SAML_FOLDER = BASE_DIR / 'app2/saml'
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

def acs(request):
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

        if not errors:
            if 'AuthNRequestID' in request.session:
                del request.session['AuthNRequestID']
            request.session['samlUserdata'] = auth.get_attributes()
            request.session['samlNameId'] = auth.get_nameid()
            request.session['samlNameIdFormat'] = auth.get_nameid_format()
            request.session['samlNameIdNameQualifier'] = auth.get_nameid_nq()
            request.session['samlNameIdSPNameQualifier'] = auth.get_nameid_spnq()
            request.session['samlSessionIndex'] = auth.get_session_index()
        elif auth.get_settings().is_debug_active():
            error_reason = auth.get_last_error_reason()
            
        if 'samlUserdata' in request.session:
            paint_logout = True
            if len(request.session['samlUserdata']) > 0:
                attributes = request.session['samlUserdata'].items()

    return render(request, 'app2.html', {'errors': errors, 'error_reason': error_reason, 'not_auth_warn': not_auth_warn, 'success_slo': success_slo,
                                        'attributes': attributes, 'paint_logout': paint_logout})

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

