
# TODO COMPLETO - Pet Paparico

## Status atual do projeto

O projeto Pet Paparico está em funcionamento como uma aplicação Django monolítica que oferece gerenciamento de pets, controle de alimentação e uma interface web integrada. A comunicação com o ESP32 está prevista via configuração em `server_django/pet_feeder_django/settings.py`, mas o projeto também funciona localmente usando a lógica de simulação de dispositivo e rotas internas.

### O que já está implementado

- autenticação de usuários com login, cadastro e logout
- gerenciamento de pets com foto, dados básicos e porção padrão
- alimentação manual com registro em histórico
- agendamentos de alimentação
- painel de visualização de histórico e consumo
- monitoramento de status do dispositivo e nível de ração
- controle e calibração de servo
- reabastecimento do reservatório
- páginas de câmeras e mídia
- notificações internas e envio de e-mail em desenvolvimento via console
- interface web com foco em acessibilidade e navegação por rotas HTML

### Tecnologias principais

- Python 3.12
- Django 6.0.4
- Django REST Framework
- SQLite
- Tailwind CSS (via CDN e ferramentas no `package.json`)
- ESP32 com firmware Arduino (documentação em `esp32_firmware/`)

---

## Estrutura do repositório

### Arquivos principais
- `README.md` — documentação principal do projeto
- `TODO_COMPLETO.md` — visão geral de status e próximos passos
- `requirements.txt` — dependências Python
- `package.json` — scripts e dependências de frontend/desenvolvimento
- `start.sh` — script de inicialização do projeto
- `esp32_firmware/` — firmware e documentação do ESP32
- `server_django/` — aplicação Django

### Backend Django
- `server_django/api/` — models, views, serializers, rotas e templates
- `server_django/pet_feeder_django/` — configurações do projeto Django

---

## Funcionalidades atuais

### Usuários e pets
- cadastro e edição de conta de usuário
- cadastro e edição de pets com foto e dados básicos
- definição de quantidade padrão de ração por pet

### Alimentação
- alimentação manual via interface web
- registro persistente em histórico de alimentação
- agendamentos de alimentação registrados no backend

### Dispositivo / IoT
- roteamento para endpoints de controle do dispositivo
- status online/offline disponível via API
- leitura de nível de ração
- calibração de servo
- reabastecimento do reservatório
- simulador de ESP32 disponível para testes locais

### Notificações
- notificações internas ao usuário
- testes de envio de notificações de baixo nível de ração
- envio de e-mail em modo console para desenvolvimento

### Acessibilidade e interface
- navegação por rotas web claras
- foco visível e elementos acessíveis
- layout responsivo para diferentes tamanhos de tela

---

## Ajustes recentes realizados

- atualizada a documentação `README.md` e `TODO_COMPLETO.md` para refletir a estrutura real do projeto
- validada a presença de `server_django/pet_feeder_django/settings.py` com `ESP32_BASE_URL` e `EMAIL_BACKEND` em console
- confirmada a organização de rotas em `server_django/api/urls.py` e `server_django/api/web_urls.py`
- identificado que o diretório atual não contém metadados Git (`.git` ausente)

---

## Próximos passos recomendados

### Prioridade alta
- validar o fluxo completo com hardware ESP32 disponível
- criar testes automatizados adicionais para rotas de alimentação e notificações
- organizar e documentar claramente os endpoints REST do projeto
- validar configuração de ambiente de desenvolvimento sem `fixtures` quebrados

### Prioridade média
- implementar deploy local com Docker ou containerização leve
- melhorar dashboards e relatórios de consumo de ração
- adicionar controle de ordem de agendamentos e limites de porções
- revisar UX de páginas de câmeras e notificações

### Prioridade baixa
- adicionar suporte a WebSocket ou notificações push reais
- criar documentação de instalação do firmware ESP32 mais detalhada
- revisar segurança para produção: `DEBUG=False`, configuração de e-mail segura, e CORS mais restrito
- definir variáveis de ambiente para credenciais sensíveis

---

## Observações adicionais

- A aplicação parece organizada para desenvolvimento local, mas não foi possível comparar alterações de versões anteriores por falta do repositório Git.
- O frontend está baseado em templates Django, sem um SPA separado atualmente.
- A comunicação do backend com o ESP32 depende de um endereço configurado em `ESP32_BASE_URL` e pode usar um simulador em modo de desenvolvimento.

---

## Documentos de suporte

- `README.md` — documentação atual do projeto
- `esp32_firmware/README.md` — documentação do firmware e integração ESP32
- `server_django/pet_feeder_django/settings.py` — configuração de ambiente e endpoints do ESP32
- `server_django/api/web_urls.py` — rotas da interface web
- `server_django/api/urls.py` — rotas da API REST
