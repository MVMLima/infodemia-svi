# SVI — Sistema de Vigilância de Infodemia

Pipeline de monitoramento de desinformação em saúde (boatos antivacina, pandemia).
Coleta menções públicas → detecta picos de menção → classifica boatos → gera
alerta e relatório com **narrativas substitutas** prontas para resposta
(prebunking/debunking).

Feito para vigilância em saúde pública — originalmente para o estado do Acre —
mas **funciona em qualquer lugar**: basta clonar, configurar os termos e rodar.

## Recursos

- **Coleta** de menções via Google News RSS (`when=30d`) com fallback DuckDuckGo Lite.
- **Dedup** por título e **filtro de janela** por data real da notícia (pubDate) —
  o RSS retorna artigos antigos que são descartados.
- **Sentimento** por keyword matching PT-BR (contexto de saúde).
- **Picos** por z-score vs. média móvel (baseline mínimo para evitar alerta falso
  em série esparsa).
- **Classificação de boatos** por base de conhecimento com 10 boatos seed,
  narrativas substitutas e fontes oficiais. Fact-checks ("É #FAKE...") não contam
  como propagação.
- **Relatório markdown** executivo: resumo, comparativo 7d vs 7d anteriores,
  volume por termo, série diária, notícias novas com veículo real, picos, boatos,
  top veículos e recomendações.
- **Alerta** em padrão watchdog (stdout vazio = silêncio), ideal para cron.
- **Zero dependências externas** — apenas Python 3.8+ da stdlib.

## Instalação

```bash
git clone <url-do-repositorio> infodemia_svi
cd infodemia_svi
# (opcional) python3 -m venv .venv && source .venv/bin/activate
```

## Uso rápido

```bash
# Tudo em um comando: init_db → coleta → análise → relatório
bash run_pipeline.sh

# Ou passo a passo:
export PYTHONPATH=$PWD/scripts

python3 scripts/init_db.py          # 1. cria o banco SQLite (idempotente)
python3 scripts/coleta.py           # 2. coleta menções (stdout = JSON resumo)
python3 scripts/analise.py          # 3. detecta picos e classifica boatos
python3 scripts/relatorio.py        # 4. gera relatório markdown (stdout)
python3 scripts/alerta.py           # 5. alerta watchdog (vazio = sem alerta)

# Depois de entregar um briefing, marque as notícias como exibidas
# (o próximo relatório não repete):
python3 scripts/marcar_exibidas.py
```

O banco SQLite é criado em `data/infodemia.db` (pasta `data/` é ignorada pelo git).

## Configuração

### `scripts/config.json`

| Campo | Default | Descrição |
|---|---|---|
| `regiao` | `"Acre"` | Região/localidade adicionada às buscas |
| `termos` | 10 termos de vacina/pandemia | Termos monitorados |
| `limiar_zscore` | `2.0` | Limiar do z-score para marcar `ALERTA` |
| `janela_media` | `7` | Janela da média móvel (conceito estatístico) |
| `janela_dias` | `30` | Período da busca/relatório (dias) |
| `max_resultados_por_termo` | `10` | Máximo de resultados por termo por fonte |

### Localização do banco

Ordem de precedência:

1. Variável de ambiente **`SVI_DB_PATH`** (recomendado para deploy/CI):
   ```bash
   export SVI_DB_PATH=/caminho/para/infodemia.db
   ```
2. Campo `db_path` do `config.json` (opcional).
3. Default: `<raiz do projeto>/data/infodemia.db`.

## Agendamento (cron)

Exemplo de crontab (diário):

```cron
50 6 * * *  cd /caminho/infodemia_svi && PYTHONPATH=$PWD/scripts python3 scripts/coleta.py >> /var/log/svi_coleta.log 2>&1 && PYTHONPATH=$PWD/scripts python3 scripts/analise.py >> /var/log/svi_analise.log 2>&1
0 7 * * *   cd /caminho/infodemia_svi && PYTHONPATH=$PWD/scripts python3 scripts/alerta.py  # stdout vazio = silencioso
10 7 * * *  cd /caminho/infodemia_svi && PYTHONPATH=$PWD/scripts bash scripts/cron_relatorio.sh
```

Ou use os wrappers prontos que resolvem a raiz do projeto sozinhos:
`scripts/cron_coleta_analise.sh` (coleta + análise) e `scripts/cron_relatorio.sh`
(gera relatório + marca exibidas).

## Testes

```bash
export PYTHONPATH=$PWD/scripts
python3 -m unittest discover -s tests -v
```

Os testes usam banco temporário e rodam offline (sem rede).

## Estrutura

```
infodemia_svi/
├── run_pipeline.sh           ← pipeline completo em um comando
├── scripts/
│   ├── paths.py              ← resolução do caminho do banco (env → config → data/)
│   ├── config.json           ← termos, limiar, janelas, região
│   ├── init_db.py            ← schema SQLite + migração automática
│   ├── coleta.py             ← Google News RSS + DDG, dedup, sentimento
│   ├── analise.py            ← picos z-score + classificação de boatos
│   ├── boatos.py             ← base de boatos + matching anti-falso-positivo
│   ├── relatorio.py          ← relatório markdown executivo
│   ├── alerta.py             ← watchdog (cron no_agent)
│   ├── marcar_exibidas.py    ← dedup anti-repetição de briefing
│   └── *_diagnostico.py      ← utilitários de inspeção do banco
├── tests/                    ← unittest (offline)
└── data/                     ← SQLite criado em runtime (gitignored)
```

## Como funciona (nota metodológica)

- **Coleta**: Google News RSS com fallback DuckDuckGo Lite. Usa a data real da
  notícia (pubDate) e descarta fora da janela.
- **Picos**: z-score = (volume hoje − média dos N dias anteriores) / desvio.
  Exige baseline mínimo (≥4 dias com menção) para evitar ALERTA em série esparsa.
- **Boatos**: o texto precisa conter contexto de saúde e keywords de palavra
  única casam por word boundary (ex.: "mata" não casa "mata-mata da copa").
  Fact-checks são classificados para rastreabilidade, mas não contam como propagação.
- **Limitações**: apenas menções públicas indexadas (Google News/DDG) — WhatsApp
  e grupos fechados não são capturados. Keyword matching é heurística; para
  produção em larga escala, considerar modelo BERT pt-BR.

## Licença

MIT — veja [LICENSE](LICENSE).
