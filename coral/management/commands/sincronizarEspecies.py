from django.core.management.base import BaseCommand, CommandError
from coral.services.obis_species_sync import ObisSpeciesSync

class Command(BaseCommand):
    help = "Busca espécies marinhas (corais, peixes, etc.) via API OBIS para as regiões do banco."

    def add_arguments(self, parser):
        # Permite filtrar por uma região específica se não quiser rodar todas de uma vez
        parser.add_argument('--regiao_id', type=int, default=None, help="ID da região específica para sincronizar")

    def handle(self, *args, **kwargs):
        servico = ObisSpeciesSync()
        try:
            regiao_id = kwargs['regiao_id']
            self.stdout.write(self.style.WARNING(f"Iniciando sincronização de espécies com a API OBIS..."))
            
            # Passamos o log do django para o serviço conseguir printar no terminal
            servico.sincronizar(regiao_id=regiao_id, log_func=self.stdout.write)
            
            self.stdout.write(self.style.SUCCESS("Sincronização de biodiversidade concluída com sucesso!"))
        except Exception as e:
            raise CommandError(f"Erro na operação de sincronização: {e}")