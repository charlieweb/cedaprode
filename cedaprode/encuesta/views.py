# -*- coding: UTF-8 -*-
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.views.generic.simple import direct_to_template
from django.contrib.auth.decorators import login_required
from django.forms.models import inlineformset_factory, modelformset_factory, formset_factory
from django.template import RequestContext
from django.db.models import Sum
from forms import *
from decorators import checar_permiso
from models import *
from utils import generar_grafo, generar_grafro_general

def index(request):
    if request.user.is_authenticated():
        return redirect('inicio')
    else:
        return redirect('user-login')

@login_required
def inicio(request):
    return direct_to_template(request, 'index.html')

@login_required
@checar_permiso
def llenar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, pk = encuesta_id)
    
    adjuntos = Adjunto.objects.filter(encuesta__id=encuesta_id)
    PreguntaInlineFormSet = inlineformset_factory(Encuesta, Respuesta,
                                                  form=RespuestaInlineForm,
                                                  can_delete=False,
                                                  max_num=0)
    if request.method == 'POST':
        formset = PreguntaInlineFormSet(request.POST, request.FILES, instance = encuesta)
        
        if formset.is_valid():
            formset.save()
            return redirect('mis-encuestas')
        # else:
        #     formset = PreguntaInlineFormSet(request.POST, instance = encuesta)  
    else:
        formset = PreguntaInlineFormSet(instance=encuesta)

    return render_to_response('encuesta/llenar_encuesta.html',
                    {'formset': formset, 'encuesta': encuesta.id,
                     'adjuntos':adjuntos},
                    context_instance=RequestContext(request))

@login_required
def crear_encuesta(request):
    encuesta = Encuesta(usuario=request.user)
    if request.method == 'POST':
        form = EncuestaForm(request.POST, instance=encuesta)
        if form.is_valid():
            encuesta = form.save(commit=False)
            encuesta.save()
            return redirect('llenar-encuesta', encuesta_id = encuesta.id)
    else:
        form = EncuestaForm(instance=encuesta)
    return render_to_response('encuesta/crear_encuesta.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@login_required
def crear_organizacion(request):
    organizacion = Organizacion(creado_por=request.user)
    if request.method == 'POST':
        form = OrganizacionForm(request.POST, instance=organizacion)
        if form.is_valid():
            organizacion = form.save(commit=False)
            organizacion.save()
            return redirect('organizacion-detalle', pk=organizacion.id)
    else:
        form = OrganizacionForm(instance=organizacion)
    return render_to_response('encuesta/crear_organizacion.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@login_required
def editar_organizacion(request, organizacion_id):
    organizacion = get_object_or_404(Organizacion, creado_por=request.user, pk=organizacion_id)
    if request.method == 'POST':
        form = OrganizacionForm(request.POST, instance=organizacion)
        if form.is_valid():
            organizacion = form.save(commit=False)
            organizacion.save()
            return redirect('organizaciones')
    else:
        form = OrganizacionForm(instance=organizacion)
    return render_to_response('encuesta/editar_organizacion.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@login_required
def mis_encuestas(request):
    encuestas = Encuesta.objects.filter(usuario = request.user).order_by('organizacion')
    return render_to_response('encuesta/mis_encuestas.html', {'encuestas': encuestas},
                              context_instance=RequestContext(request))

@login_required
def resultado(request, encuesta_id, template_name):
    encuesta = get_object_or_404(Encuesta, pk=encuesta_id)
    adjuntos = Adjunto.objects.filter(encuesta__id=encuesta_id)
    #lista que tendra todos los resultados...
    resultados = []
    for categoria in Categoria.objects.all():
        puntaje = Respuesta.objects.filter(encuesta=encuesta,
                                           pregunta__categoria=categoria).aggregate(total=Sum('respuesta__puntaje'))['total']
        fila = {'categoria': categoria, 'puntaje': puntaje}
        respuestas = []
        for pregunta in Pregunta.objects.filter(categoria = categoria):
            respuesta = Respuesta.objects.get(encuesta = encuesta,
                                                  pregunta = pregunta)
            respuestas.append(respuesta)
        grafo_url = generar_grafo(respuestas, categoria.titulo)
        fila['respuestas'] = respuestas
        fila['grafo_url'] = grafo_url
        fila['total_maximo'] = len(respuestas) * 5
        resultados.append(fila)

    url_grafo = generar_grafro_general("Consolidado", [(r['puntaje'], (len(r['respuestas']*5))) for r in resultados],
                                       [r['categoria'].titulo for r in resultados])
    return render_to_response('encuesta/%s' % template_name,
                              {'encuesta': encuesta, 'resultados': resultados, 'url_grafo': url_grafo,'adjuntos':adjuntos},
                              context_instance=RequestContext(request))
@login_required
def resultados(request):
    if request.method == 'POST':
        form = BuscarResultadoForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['tipo'] and form.cleaned_data['municipio']:
                encuestas = Encuesta.objects.filter(organizacion__tipo = form.cleaned_data['tipo'], organizacion__municipio = form.cleaned_data['municipio'])
            elif form.cleaned_data['municipio']:
                encuestas = Encuesta.objects.filter(organizacion__tipo = form.cleaned_data['municipio'])
            elif form.cleaned_data['tipo']:
                encuestas = Encuesta.objects.filter(organizacion__tipo = form.cleaned_data['tipo'])
    else:
        form = BuscarResultadoForm()
        encuestas = Encuesta.objects.filter(usuario = request.user)

    return render_to_response('encuesta/resultados.html',
                              {'encuestas': encuestas, 'form': form},
                              context_instance=RequestContext(request))

@login_required
def organizaciones(request):
    organizaciones = Organizacion.objects.filter(creado_por=request.user)
    #form = BuscarForm()

    return render_to_response('encuesta/organizacion_list.html',
                              {'object_list': organizaciones},
                              #{'object_list': organizaciones, 'form': form},
                              context_instance=RequestContext(request))

@login_required
def buscar_orgs(request):
    if request.method == "POST":
        form = BuscarForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['tipo'] and form.cleaned_data['municipio']:
                resultados = Organizacion.objects.filter(tipo = form.cleaned_data['tipo'],municipio = form.cleaned_data['municipio'])
            elif form.cleaned_data['tipo']:
                resultados = Organizacion.objects.filter(tipo = form.cleaned_data['tipo'])
            elif form.cleaned_data['municipio']:
                resultados = Organizacion.objects.filter(tipo = form.cleaned_data['municipio'])

            return render_to_response('encuesta/buscar_orgs.html',
                              {'organizaciones': resultados, 'form': form},
                              context_instance=RequestContext(request))
    else:
        form = BuscarForm()
        return render_to_response('encuesta/buscar_orgs.html',
                          {'form': form},
                          context_instance=RequestContext(request))

@login_required
@checar_permiso
def adjuntar(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, pk=encuesta_id)
    adjunto =  Adjunto(encuesta = encuesta)

    if request.method == "POST":
        form  = AdjuntoForm(request.POST, request.FILES, instance=adjunto)
        if form.is_valid():
            form.save()
            return redirect('llenar-encuesta', encuesta_id=encuesta.id)
    else:
        form  = AdjuntoForm(instance=adjunto)

    return render_to_response('encuesta/adjuntar.html',
                      {'form': form},
                      context_instance=RequestContext(request))

@login_required
def ver_adjuntos(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, pk=encuesta_id)
    adjuntos =  Adjunto.objects.filter(encuesta = encuesta)

    return render_to_response('encuesta/ver_adjuntos.html',
                      {'adjuntos': adjuntos},
                      context_instance=RequestContext(request))

@login_required
@checar_permiso
def eliminar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, pk=encuesta_id)
    encuesta.delete()
    return redirect('resultados')

#Nuevo codigo

@login_required
#@checar_permiso
def informacion_extra(request, encuesta_id):
    cosa = get_object_or_404(Encuesta, pk=encuesta_id)
    #extra =  ExtraInformacion(encuesta = encuesta)
    initial_one = [{'integradas':1},
                   {'integradas':2},
                   {'integradas':3},
                   {'integradas':4},
                   {'integradas':5},
                   {'integradas':6},
                   {'integradas':7}
                   ]
    initial_two = [{'tipos':1},
                   {'tipos':2},
                   {'tipos':3},
                   {'tipos':4},
                   {'tipos':5}
                   ]
    Form1InlineFormSet = formset_factory(ExtraInformacionForm, 
                        extra = 7, max_num=7)
    Form3InlineFormSet = formset_factory(FrecuenciaInfoForm, 
                        extra = 5, max_num=5)

    if request.method == "POST":
        form1 = Form1InlineFormSet(request.POST)
        form2 = RubrosManejadosForm(request.POST)
        form3 = Form3InlineFormSet(request.POST)
        if form1.is_valid() and form2.is_valid():
            for unform1 in form1:
              obj = unform1.save(commit=False)
              obj.encuesta = cosa
              obj.save()
            unform2 = form2.save(commit=False)
            unform2.encuesta = cosa
            unform2.save()
            for unform3 in form3:
              obj = unform3.save(commit=False)
              obj.encuesta = cosa
              obj.save()
            return redirect('llenar-encuesta', encuesta_id=cosa.id)
    else:
        form1 = Form1InlineFormSet(initial=initial_one)
        form2 = RubrosManejadosForm()
        form3 = Form3InlineFormSet(initial=initial_two)

    return render_to_response('encuesta/extra_info.html',
                      {'form1':form1, 
                     'form2':form2,'form3':form3},
                      context_instance=RequestContext(request))

