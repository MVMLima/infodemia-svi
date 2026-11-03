# Changelog

Todas as mudanças relevantes do SVI — Sistema de Vigilância de Infodemia.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-11-03

Primeira versão estável, publicada para reuso por outros órgãos públicos.

### Adicionado

- **Núcleo de coleta** (`scripts/coleta.py`): menções via Google News RSS
  (`when=30d`) com fallback DuckDuckGo Lite; deduplicação por título; descarte
  por data real da notícia (`pubDate`) fora da janela; sentimento por casamento
  de palavras-chave em PT-BR com contexto de saúde.
- **Detecção de picos** (`scripts/analise.py`): z-score sobre média móvel,
  com baseline mínimo de 4 dias com menção para evitar alerta em série esparsa.
- **Base de boatos** (`scripts/boatos.py`): 10 narrativas seed com palavras-chave
  de detecção, narrativas substitutas e fontes oficiais. Fact-checks ("É #FAKE…")
  são classificados para rastreabilidade mas não contam como propagação.
- **Relatório executivo** (`scripts/relatorio.py`): resumo, comparativo 7d contra
  7d anteriores, volume por termo, série diária, notícias novas com veículo real,
  picos e boatos.
- **Alerta watchdog** (`scripts/alerta.py`): saída vazia quando não há alerta,
  compatível com cron silencioso.
- **Parametrização** (`scripts/config.json`): região, termos de busca, limiar de
  z-score, janela de média, janela de dias e máximo de resultados por termo.
- **Empacotamento**: `Dockerfile`, integração contínua com execução de testes
  (`.github/workflows/ci.yml`) e publicação de container em GHCR.
- **Triagem SVI-AC nº 01/2026** (`triagens/`): análise da peça que atribui ao
  estudo Ophir & Shir-Raz (EXCLI Journal, 03/09/2026) a conclusão de que a vacina
  Pfizer "afetava diretamente o coração". Classificação: enganoso. Inclui
  evidência (suplemento CC-BY via Europe PMC) e script de auditoria que reproduz
  15 de 15 conferências da tabela de verificação dos autores.
- **Validação comparativa** (`validacao_jev/`): bateria rotulada de 412 itens
  (378 após limpeza) comparando o modelo System One do TypeSafe (`jev-latest`)
  com a heurística determinística de produção. Acurácia 0,899 × 0,545; AUC-ROC
  0,985 × 0,540; na população real de produção, 1 falso positivo (0,5%) contra
  4 (2,1%). Inclui análise de ponto de corte, com 0,3 superando 0,5.

### Notas

- Python 3.8+ com apenas biblioteca padrão — nenhuma dependência externa, nenhuma
  chave de API necessária.
- A coleta depende de Google News RSS, interface não documentada e sem garantia
  de disponibilidade, com fallback em DuckDuckGo Lite.
- O motor é genérico; a base de boatos e as narrativas substitutas são específicas
  do Acre e do tema vacinal, e exigem curadoria própria por parte do órgão adotante.
- O núcleo publicado não realiza chamadas a serviços de LLM. Detecção,
  classificação e computação quantitativa são determinísticas e auditáveis.
- Licença MIT — veja [LICENSE](LICENSE).
