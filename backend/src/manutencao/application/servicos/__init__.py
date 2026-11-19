"""Serviços de aplicação (Service Layer): casos de uso que coordenam repositórios e entidades.

Cada serviço recebe suas portas **pelo construtor** (ADR-0005), nunca importa uma implementação
concreta e não duplica regra de domínio: carrega o contexto, chama a entidade e salva.
"""
