# Eu Edito — Configuração de Infraestrutura na Railway (Web + Motion Worker)

A arquitetura já está preparada para rodar tanto em **serviço único** (padrão atual) quanto distribuída com **Motion Worker dedicado + Volume Persistente** na Railway sem alterar o domínio principal.

## 1. Serviço Principal (já existente)
- **Repositório / Branch**: mesmo repositório GitHub (`main`) e `Dockerfile` atual.
- **Start Command**: padrão do `Dockerfile` (`python backend/server.py`).
- **Domínio**: mantido sem alterações.
- **Variáveis de ambiente recomendadas**:
  - `GROQ_API_KEY`: chave Groq para transcrição rápida e análise contextual de Motion Graphics (mantenha apenas nas variáveis da Railway, nunca no código).
  - `EU_EDITO_STORAGE_DIR=/data/eu_edito`: aponta para o Volume persistente montado em `/data`.
  - `MOTION_WORKER_URL=http://motion-worker.railway.internal:8091`: URL privada do Motion Worker na rede interna da Railway.
  - `INTERNAL_WORKER_TOKEN=<token-secreto-gerado-na-railway>`: segredo compartilhado para autenticar chamadas entre serviços internos (`X-Worker-Token`).

## 2. Novo Serviço: Motion Worker (`motion-worker`)
Crie um segundo serviço no mesmo projeto da Railway apontando para o **mesmo repositório GitHub e `Dockerfile`**:
- **Custom Start Command**: `python backend/motion_worker.py` (ou configure `SERVICE_ROLE=worker` mantendo o Start Command padrão).
- **Networking**: **não** gere domínio público (use apenas rede interna privada na porta `8091`).
- **Variáveis de ambiente**:
  - `PORT=8091`
  - `SERVICE_ROLE=worker`
  - `EU_EDITO_STORAGE_DIR=/data/eu_edito`
  - `INTERNAL_WORKER_TOKEN=<mesmo-token-do-servico-principal>`
  - `MOTION_MAX_WORKERS=2` (limita renderizações simultâneas para proteger RAM/CPU)

## 3. Armazenamento Persistente (Volume / Object Storage)
- No painel da Railway, adicione um **Volume** montado em `/data` (ou conecte um bucket S3/R2 caso prefira sincronização externa multi-região).
- Com `EU_EDITO_STORAGE_DIR=/data/eu_edito`, os vídeos enviados, arquivos `.mov` transparentes de Motion Graphics (`_motion_assets/`), B-rolls (`_brolls/`), Cards (`_cards/`) e exportações finais sobrevivem a reinicializações e novos deploys.

## 4. Verificações pós-deploy no painel da Railway
1. `GET https://<seu-dominio>/health` retorna `{"ok": true, ...}`.
2. Nos logs do serviço `motion-worker`, confirmar `Eu Edito Motion Worker listening on 0.0.0.0:8091`.
3. No app, clicar em **✨ Analisar vídeo e sugerir Motion Graphics**, testar **▶ Gerar camada** e exportar o vídeo final verificando que os Motion Graphics aparecem sobrepostos no `.mp4`.
