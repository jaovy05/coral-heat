from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone


class Contact(models.Model):
    TIPO_CHOICES = [
        ('parceria', 'Parceria'),
        ('problema', 'Reportar Problema'),
        ('duvida', 'Dúvida'),
        ('outro', 'Outro'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contatos', null=True, blank=True)
    nome_completo = models.CharField(max_length=255)
    email = models.EmailField()
    tipo_contato = models.CharField(max_length=20, choices=TIPO_CHOICES)
    assunto = models.CharField(max_length=255)
    mensagem = models.TextField()
    deletado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.nome_completo} - {self.assunto}"
    
    def pode_editar(self):
        """Retorna True se a mensagem pode ser editada (menos de 2 minutos)"""
        agora = timezone.now()
        diferenca = agora - self.criado_em
        return diferenca < timedelta(minutes=2)
    
    def pode_deletar(self):
        """Retorna True se a mensagem pode ser deletada (não está deletada)"""
        return not self.deletado
