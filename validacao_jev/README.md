# Validação Jev (TypeSafe) × heurística do SVI-AC

Bateria de validação da tarefa binária **"este texto veicula desinformação em saúde?"**,
comparando o modelo System One do TypeSafe (`jev-latest`, `jev-1.13.0`) com a
heurística determinística de produção do SVI-AC (`boatos.match_boato` + `analise.SINAIS_CHECAGEM`).

Executada em 21/09/2026. Custo total em API: **US$ 0,0086** (204.551 tokens de entrada,
a US$ 0,042/Mtok; output é gratuito).

## Como a bateria foi construída

Não existia conjunto rotulado. O corpus de produção do SVI-AC tem 214 menções reais
(13/07–17/09/2026) e apenas **4** carregam veredito explícito de checagem — é quase todo
notícia legítima de campanha vacinal. A base `boatos` é um banco de *narrativas*, não uma
amostra rotulada. Portanto a validação exigiu montar ground truth de fora.

| Componente | n | Origem | Rótulo |
|---|---|---|---|
| Positivos | 221 | Claims com veredito **FALSO** de checadoras, via Google News RSS (`"É #FAKE que"` + termos de saúde) | `y=1` |
| Negativos | 187 | Manchetes reais do banco de produção do SVI-AC | `y=0` |
| Negativos | 4 | Claims com veredito **VERDADEIRO** das mesmas checadoras | `y=0` |
| **Total** | **412** | | |

Fontes do rótulo gravadas em `bateria.csv` (`fonte_rotulo`): `veredito_no_titulo`
(o próprio título carrega o veredito) ou `curadoria` (lido e classificado à mão).

Pipeline: `construir_bateria.py` → `coletar_checagens.py` → `consolidar_bateria.py` → `avaliar.py` → `analisar.py`.

## Resultado principal

Regra: `noul` com corte em 0,5. Bateria limpa (n=378; ver "Defeito de rótulo" abaixo).
Ambos medidos **no mesmo conjunto** (187 positivos / 191 negativos).

| Métrica | Jev | Heurística SVI |
|---|---|---|
| Acurácia | **0,899** | 0,545 |
| Precisão | 0,993 | 0,826 |
| Revocação | 0,802 | 0,102 |
| Especificidade | 0,995 | 0,979 |
| F1 | **0,888** | 0,181 |
| AUC-ROC | **0,985** | 0,540 |
| Brier | 0,0777 | 0,4550 |

> A heurística tem AUC 0,540 porque só sabe atribuir 0 ou 1 — não existe graduação.
> E a revocação de 0,102 é esperada: ver limitação 3.

Subconjunto vacina/pandemia (n=354, o escopo real do SVI): acurácia 0,912, AUC 0,987,
Brier 0,0709.

### População de produção — a única comparação justa

Nas 187 manchetes reais do SVI (todas legítimas, `y=0`), que é a população em que ambos
operam:

- **Heurística SVI: 4 falsos positivos (2,1%)** — `chip_vacina` em *"GDF vai castrar,
  vacinar e colocar chip em animais de rua"* (microchip animal); `vacina_experimental` em
  *"Vacina experimental contra câncer tem resultado positivo"* (2×, duplicata);
  `vacina_alterar_dna` em *"Existe vacina melhor? Grávida pode tomar? Altera o DNA?"* (explicativo).
- **Jev: 1 falso positivo (0,5%)** — *"Vacinação contra Covid em gestantes é classificada
  como 'extremamente preocupante' pela Sesacre"*, p=0,58.

## Três achados que mudam a decisão

### 1. O corte de 0,5 é ruim; 0,3 é bem melhor

| Corte | Acurácia | Precisão | Revocação | F1 |
|---|---|---|---|---|
| 0,3 | **0,939** | 0,977 | 0,898 | **0,936** |
| 0,4 | 0,918 | 0,981 | 0,850 | 0,911 |
| 0,5 | 0,899 | 0,993 | 0,802 | 0,888 |
| 0,6 | 0,865 | 1,000 | 0,727 | 0,842 |

### 2. O modelo é sistematicamente subconfiante no meio da escala

Curva de confiabilidade (noul, bateria limpa):

| Faixa | n | p médio | y médio | gap |
|---|---|---|---|---|
| 0,0–0,1 | 130 | 0,071 | 0,015 | +0,056 |
| 0,2–0,3 | 16 | 0,251 | 0,500 | **−0,249** |
| 0,3–0,4 | 10 | 0,341 | 0,900 | **−0,559** |
| 0,5–0,6 | 15 | 0,547 | 0,933 | −0,387 |
| 0,8–0,9 | 31 | 0,846 | 1,000 | −0,154 |
| 0,9–1,0 | 71 | 0,938 | 1,000 | −0,062 |

ECE = 0,126. Tradução: **o ranking é excelente (AUC 0,985), mas a escala de probabilidade
não é utilizável como está.** Quem quiser ler `p` como probabilidade real precisa
recalibrar (isotônica/Platt) num conjunto de retenção. Para triagem por ordenação, já serve.

### 3. O gate de confiança discrimina, mas não cobre

Acurácia sobe monotonicamente com a confiança do Choice:

| Faixa de confiança | n | acerto |
|---|---|---|
| 0,0–0,4 | 15 | 0,333 |
| 0,4–0,6 | 24 | 0,750 |
| 0,6–0,8 | 40 | 0,800 |
| 0,8–0,9 | 38 | 0,868 |
| 0,9–1,0 | 295 | 0,956 |

Roteando confiança < 0,6 para humano: 9,5% da bateria, com acerto de 48,7% (moeda ao ar).
**Mas 40 dos 60 erros estão na faixa de alta confiança** — o gate pega só 1/3 dos erros.
Serve como filtro, não como garantia.

## Limitações (declaradas)

1. **Revocação 0,802 é piso, não valor real.** Dos 59 falsos negativos, 27 são checagens de
   autenticidade de mídia e 9 estão fora do escopo de saúde — são defeitos de rótulo meus, não
   erros do modelo. Descontando esses, a revocação sobe para **0,877** (23 erros genuínos em 187).
2. **Defeito de rótulo corrigido parcialmente.** O G1 Fato ou Fake publica muita checagem de
   autenticidade (`"É #FAKE que vídeo mostre X"`). Ao remover o prefixo do veredito sobra uma
   *descrição de mídia*, não uma afirmação falsa. 34 positivos caíram nessa categoria e foram
   excluídos da métrica principal (`analisar.py`).
3. **A comparação com a heurística favorece o Jev por construção.** O `match_boato` foi feito
   para manchetes de Google News contra um conjunto fechado de 10 narrativas vacinais. Meus
   positivos são claims cruas, em boa parte fora desse conjunto. A comparação válida é só na
   população de produção (seção acima) — e ali a heurística até se comporta bem no grosso do
   corpus, errando 2,1%.
4. **O baseline que importa foi testado** (ver seção "Confronto com DeepSeek-V4.1-Flash"),
   mas num único conjunto e com ruído de rótulo. Vencer a heurística de 30 linhas de regex era
   barra baixa; contra o LLM de produção o resultado foi o inverso do esperado.
5. **Achados de calibração vêm de uma bateria desbalanceada e com ruído de rótulo.**
   As curvas precisam de reconfirmação num conjunto maior e com rótulo revisado por humano.

## Erros genuínos do modelo (amostra)

Predominam claims de **impersonação institucional** ou de política pública, que a base de
10 narrativas não cobre: *"presidente da Anvisa disse que população corre risco ao tomar
vacinas experimentais"* (p=0,20), *"governo não pode obrigar pessoas a se vacinar contra
Covid-19"* (p=0,21), *"MPF em Uberlândia fez pedido para que vacinação seja interrompida"*
(p=0,21), *"fabricantes de vacina têm protocolo que preconiza aplicação no braço direito"*.
Sugere que ampliar a base de narrativas para incluir impersonação de autoridade sanitária
teria efeito direto na revocação.

## Confronto com DeepSeek-V4.1-Flash (o LLM de produção)

Mesma bateria, mesmo enunciado, mesmo formato de resposta (JSON com `papel` +
`probabilidade`). 412/412 respostas válidas. Script: `avaliar_deepseek.py`.

| Regra | Acurácia | Precisão | Revocação | Especificidade | F1 | AUC | Brier | ECE |
|---|---|---|---|---|---|---|---|---|
| Jev / noul @0,5 | 0,899 | 0,993 | 0,802 | 0,995 | 0,888 | **0,985** | 0,0777 | 0,1259 |
| Jev / choice | 0,929 | 0,971 | 0,882 | 0,974 | 0,924 | 0,928 | 0,0714 | — |
| DeepSeek / prob @0,5 | **0,931** | 0,994 | 0,866 | 0,995 | **0,926** | 0,968 | **0,0622** | 0,0856 |
| DeepSeek / choice | **0,931** | 0,994 | 0,866 | 0,995 | **0,926** | 0,931 | 0,0688 | — |

> ECE e Brier das regras `choice` são degenerados (saída binária) e não comparáveis.
> Só as linhas de probabilidade medem calibração de fato.

**No limiar padrão, o DeepSeek ganha.** Melhor acurácia, melhor F1, melhor Brier.

**No limiar certo, o Jev empata por cima.** Varredura de limiar:

| Limiar | Jev | DeepSeek |
|---|---|---|
| 0,3 | acc 0,939 · F1 **0,936** | acc 0,934 · F1 0,929 |
| 0,5 | acc 0,899 · F1 0,888 | acc 0,931 · F1 0,926 |
| 0,7 | acc 0,817 · F1 0,774 | acc 0,926 · F1 0,920 |

O Jev ganha em *ordenação* (AUC 0,985 × 0,968) mas seu limiar nativo está mal colocado.
Escolher 0,3 olhando esta bateria, porém, é estimativa otimista — exige validação em
conjunto retido.

### Onde os dois divergem

- Concordam em **346/378 itens (91,5%)**, com **95,4% de acerto** nesses.
- Divergem em **32 itens (8,5%)**: o DeepSeek acerta 22, o Jev acerta 10.
- Ou seja: na zona difícil, **o DeepSeek é quase 2× melhor**. O Jev não traz ganho de ensemble.

### Calibração: perfis opostos

| Faixa | n (Jev) | Jev p·méd | y·méd | n (DS) | DS p·méd | y·méd |
|---|---|---|---|---|---|---|
| 0,0–0,1 | 130 | 0,071 | 0,015 | 198 | 0,008 | 0,051 |
| 0,1–0,2 | 60 | 0,127 | 0,150 | 15 | 0,117 | 0,867 |
| 0,3–0,4 | 10 | 0,341 | 0,900 | 0 | — | — |
| 0,8–0,9 | 31 | 0,846 | 1,000 | 17 | 0,844 | 1,000 |
| 0,9–1,0 | 71 | 0,938 | 1,000 | 131 | 0,946 | 0,992 |

O DeepSeek é **bimodal e decisivo** (198 itens abaixo de 0,1 e 131 acima de 0,9; só ~21 no
meio) e bem calibrado nos extremos. O Jev espalha a massa pelo meio e é gravemente
subconfiante ali. ECE: DeepSeek 0,086 × Jev 0,126.

### Produção e custo

Nas 187 manchetes reais do SVI, os dois sinalizam **exatamente a mesma manchete** (1/187 =
0,5%) — *"Vacinação contra Covid em gestantes é classificada como extremamente preocupante
pela Sesacre"*. Empate na população de produção.

| | Jev | DeepSeek-V4.1-Flash |
|---|---|---|
| Entrada | 187.795 tokens | 124.919 tokens |
| Saída | gratuita | 104.780 tokens (inclui raciocínio) |
| Custo da bateria | **US$ 0,0079** | US$ 0,1632 (pico) / US$ 0,0816 (fora de pico) |
| Latência | 41 s (412 itens, 8 threads) | 81 s (412 itens, 16 threads) |

Preços DeepSeek conforme `api-docs.deepseek.com/quick_start/pricing` (consultado 21/09/2026);
Jev conforme `docs.typesafe.ai/models`. **O Jev é 10× a 20× mais barato** — a saída gratuita
é o que decide, porque no DeepSeek os tokens de raciocínio dominam a conta.

### Conclusão para o SVI

Para esta tarefa, **o Jev não justifica substituir o DeepSeek** — não ganha em qualidade de
decisão, só em custo e em ordenação. O uso defensável é como **primeiro estágio barato**:
filtrar volume com o Jev e mandar ao DeepSeek só a faixa ambígua. E antes de qualquer adoção,
validar o limiar em conjunto retido e com rótulo revisado por humano.

## Como reproduzir

```bash
cd ~/Documentos/Projetos/infodemia_svi/validacao_jev
export SVI_DB_PATH=/home/marc/.hermes/data/infodemia/infodemia.db
. ~/.hermes/.secrets/typesafe.env      # TYPESAFE_API_KEY

python3 construir_bateria.py           # manchetes reais + rotulos de curadoria
python3 coletar_checagens.py           # claims com veredito (Google News RSS)
python3 consolidar_bateria.py          # bateria_final.csv
python3 avaliar.py                     # chama a API (cacheia em resultados_jev.csv)
python3 analisar.py                    # metricas limpas + calibracao
python3 comparar_baseline.py           # Jev x heuristica na populacao de producao
python3 checar_gate.py                 # gate de confianca

# confronto com o LLM de producao
. ~/.hermes/.env                       # DEEPSEEK_API_KEY
python3 avaliar_deepseek.py            # retomavel (resultados_deepseek.jsonl)
python3 comparar_modelos.py            # tabela final Jev x DeepSeek
```

`avaliar.py` usa cache: `--recache` para forçar novas chamadas à API.
`avaliar_deepseek.py` é retomável: reexecutar só refaz o que faltou.
`comparar_modelos.py` importa `metricas` de `analisar.py`, que respeita o parâmetro de
corte — a de `avaliar.py` ignora (é a mesma função com assinatura enganosa: o 3º argumento
é `rotulo`, não `corte`).
