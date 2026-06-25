from django.contrib import admin
from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'email', 'tipo_contato', 'assunto', 'criado_em']
    list_filter = ['tipo_contato', 'criado_em']
    search_fields = ['nome_completo', 'email', 'assunto', 'mensagem']
    readonly_fields = ['criado_em', 'atualizado_em']
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome_completo', 'email')
        }),
        ('Mensagem', {
            'fields': ('tipo_contato', 'assunto', 'mensagem')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
