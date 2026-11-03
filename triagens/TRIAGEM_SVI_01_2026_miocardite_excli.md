# TRIAGEM DE INFODEMIA — SVI-AC Nº 01/2026

**Assunto:** peça em circulação que atribui a um estudo da revista EXCLI Journal a conclusão de que "a vacina Pfizer contra a COVID-19 afetava diretamente o coração".

**Data da triagem:** 13/10/2026
**Elaboração:** SVI-AC — triagem interna
**Natureza:** documento interno de triagem. Não constitui posição institucional da SESACRE.
**Classificação:** **ENGANOSO** — a fonte primária existe e é real; a conclusão foi invertida pela manchete.
**Boato relacionado (base SVI):** vacina_mata (id 4) — tática "falsa causalidade". Mapeamento imperfeito, ver item 10.
**Situação no monitoramento:** **não capturada** pela coleta do SVI-AC (0 menções a miocardite, pericardite, EXCLI ou Israel na base, que cobre 13/07/2026 a 12/10/2026).

---

## 1. Resumo executivo

A peça analisada é um print de texto em português, fundo preto, **sem veículo, assinatura, logotipo ou data**. Ela resume um artigo científico que existe de fato, publicado na EXCLI Journal em 03/09/2026 pelos autores Ophir e Shir-Raz, sobre a comunicação do sinal de miocardite/pericardite durante a campanha de vacinação em Israel.

O corpo do texto da peça é **razoavelmente fiel** ao artigo — inclusive ao afirmar que o estudo é observacional, que não demonstra causalidade e que miocardite e pericardite já são reconhecidas como efeito adverso raro de vacinas de RNA mensageiro. **A manchete é que não se sustenta**: "ESTUDO INDICOU QUE A VACINA PFIZER CONTRA A COVID-19 AFETAVA DIRETAMENTE O CORAÇÃO" afirma exatamente o que os autores dizem não poder afirmar.

Os números citados (531 hospitalizações e 67 mortes) **conferem**: reproduzi todos eles do zero no arquivo suplementar aberto pelos autores, 15 de 15 conferências batendo com a própria tabela de verificação do artigo.

O achado central do estudo é sobre **comunicação de risco** — o intervalo de aproximadamente três a quatro meses entre o alerta interno israelense e a comunicação pública —, e não sobre a vacina "afetar o coração". Como o tema não apareceu no fluxo monitorado nos últimos 90 dias, a recomendação é **preposicionamento (prebunking)**, não resposta reativa.

---

## 2. Classificação

| Dimensão | Achado |
|---|---|
| A fonte primária existe? | Sim — artigo real, com DOI, PMCID e dado bruto aberto |
| O dado bruto confere? | Sim — 15/15 verificações reproduzidas independentemente |
| A conclusão da manchete procede? | **Não** — contraria a seção de Limitações do próprio artigo |
| O corpo do texto da peça é fiel? | Em sua maior parte, sim |
| Tipo de problema | Fonte real citada fora de contexto + manchete que inverte a conclusão |
| Veredito de triagem | **ENGANOSO** (não classificar como "falso") |

**Por que não classificar como "falso":** classificar como falso erraria duas vezes — desqualificaria um estudo legítimo e daria ao propagador a resposta fácil ("é censura, o estudo existe"). O problema é preciso e localizável: uma frase, no topo, que contradiz o artigo que a peça diz resumir.

---

## 3. A peça × a fonte

| Afirmação da peça | Verificação na fonte primária | Situação |
|---|---|---|
| "A vacina Pfizer afetava diretamente o coração" | Os autores, nas Limitações: o conjunto "cannot establish causal relationships between vaccination and reported outcomes" | **NÃO SUSTENTADA** |
| "531 hospitalizações e 67 mortes" | 532 linhas de origem; 531 registros analíticos; 67 óbitos únicos | **CONFERE** |
| "reportadas ao Ministério da Saúde de Israel e à Pfizer" | O Ministério de Israel é o **emissor** da notificação; a Pfizer é a destinatária | **DISTORCIDA** (direção do fluxo invertida) |
| "atraso de vários meses entre os primeiros alertas internos e a comunicação pública" | "communicated to clinicians and the public only after approximately three to four months" | **CONFERE** |
| "não demonstra que a vacina tenha causado as mortes" | Idêntico às Limitações | **CONFERE** |
| "miocardite e pericardite já são reconhecidas... efeitos adversos pouco frequentes... maior incidência em homens jovens" | Consistente com Anvisa e com a NT nº 139/2022-CGPNI/SVS/MS | **CONFERE** |
| Apresentação dos 531/67 como se fossem eventos cardíacos | O conjunto abrange eventos cardíacos, neurológicos, alérgicos, inflamatórios, hematológicos e outros; miocardite/pericardite = 250 de 531 (47,1%) | **DISTORCIDA** |

---

## 4. Verificação independente no dado bruto

Baixei o suplemento EXCLI-25-1437-s-001.xlsx (via Europe PMC), li a planilha com leitor próprio e recomputei, sem usar código dos autores, os números do artigo. Comparei com a tabela **"Reproduction checks"** que o próprio codebook dos autores publica.

| Conferência | Minha contagem | Codebook |
|---|---|---|
| Registros de origem (Hospitalizations) | 532 | 532 |
| Registros analíticos (após excluir o caso 343) | 531 | 531 |
| myocarditis_pericarditis = 0 | 281 | 281 |
| myocarditis_pericarditis = 1 | 248 | 248 |
| myocarditis_pericarditis = 2 | 2 | 2 |
| Miocardite/pericardite (códigos 1 ou 2) | 250 | 250 |
| patient_status alta / internado / óbito / indefinido | 502 / 14 / 6 / 9 | 502 / 14 / 6 / 9 |
| Registros com idade válida (< 120 anos) | 530 | 530 |
| Pacientes < 30 anos | 211 | 211 |
| < 30 com miocardite/pericardite | 151 | 151 |
| < 30 sem histórico médico relevante | 134 | 134 |
| Miocardite/pericardite nesse subgrupo | 99 | 99 |
| Homens nesse subgrupo | 90 | 90 |
| Valores válidos de tempo vacinação→evento | 529 | 529 |

**Resultado: 15/15 conferências batem.**

Verificações adicionais, calculadas por mim:

- Mediana do intervalo vacinação→evento: **5 dias (IQR 3–15)**, sobre 529 registros — coincide com o artigo.
- Datas de notificação à Pfizer: **36 datas distintas**, janela de **25/03/2021 a 09/05/2022** — exatamente como o artigo declara.
- Óbitos: 62 registros na aba Deaths, dos quais 2 com miocardite registrada; 6 hospitalizações com desfecho óbito; 62 + 6 − 1 (sobreposição) = **67 óbitos únicos**.
- Mediana do intervalo vacinação→óbito: **3 dias**, sobre 62 registros — coincide.
- O valor de idade 665 anos existe na planilha, como o artigo admite, e foi por mim excluído das análises por idade.

**Leitura deste resultado:** a reprodutibilidade é a maior força desta fonte. O problema não está nos números — está no que se faz com eles fora do artigo.

---

## 5. O que o estudo realmente mostra

- Em 28/02/2021, Israel alertou a EMA e o CDC sobre aproximadamente 40 casos de miocardite.
- Em 25/03/2021, Israel já havia notificado à Pfizer 46 óbitos e 157 hospitalizações, incluindo 65 casos de miocardite ou pericardite.
- O reconhecimento público pelo CDC só veio em 06/07/2021, no MMWR; a alteração das fichas da EUA pela FDA, em 25/06/2021.
- A caracterização completa na literatura revisada por pares levou de seis a sete meses.
- No conjunto notificado, miocardite ou pericardite correspondeu a 250 de 531 hospitalizações (47,1%), subindo a 151 de 211 (71,6%) entre menores de 30 anos; destes, 90 de 99 eram homens.

**Tese do artigo:** houve atraso na comunicação e a comunicação, quando veio, enfatizou raridade, curso leve e menor preocupação em relação à COVID-19. O objeto do estudo é a **condução da comunicação de risco** — não a existência de dano cardíaco direto.

---

## 6. Limites da fonte primária

Declarados pelos próprios autores:

- **Sem denominador.** O conjunto "does not contain a defined population denominator or a comparison group". Não permite estimar incidência, risco populacional, efetividade ou causalidade.
- **Sem comparador.** Não permite análise formal de desproporcionalidade (ROR, PRR).
- **Proveniência não estabelecida.** Arquivo obtido de "fonte protegida", sem dicionário de dados nem trilha de auditoria; não se sabe se é exportação completa ou subconjunto curado.
- **Versões divergentes.** Entre outubro e dezembro de 2021, a data de notificação à Pfizer foi alterada de 11/10 para 07/10 em 46 registros; um relato de óbito da versão de outubro desapareceu nas seguintes.
- **Subnotificação reconhecida.** O próprio artigo cita o relatório do State Comptroller de Israel (maio/2024): os sistemas do Ministério "não registraram cerca de 82% da informação de cerca de 354.200 notificações".
- **Sem adjudicação clínica padronizada** dos diagnósticos.

Observações da triagem que não estão no artigo:

- **Circularidade parcial.** Um conjunto compilado para monitorar um sinal tende a conter muito daquele sinal. Os autores identificaram um artefato estrutural relevante: após o caso 221, entra um bloco separado de 34 registros, **todos** de miocardite/perimiocardite, com numeração não consecutiva, na mesma data de notificação (10/06/2021), sem indicação da origem no arquivo. A proporção de 47,1% deve ser lida com isso em vista.
- **Indexação.** Não estabeleci se o artigo está indexado no MEDLINE — a Europe PMC devolveu o registro com fonte "PMC", diferente dos registros "MED". Não afirmo nem a favor nem contra. O EXCLI Journal publicou outros trabalhos heterodoxos sobre COVID-19, incluindo um de 2024 sobre mortalidade de jovens na Inglaterra.
- **Governança.** O uso de dado oriundo de um ministério da saúde foi aprovado por comitê de ética universitário (Ariel University, AU-SOC-YO-20251113).

---

## 7. Situação no Brasil

O reconhecimento oficial brasileiro do evento adverso é anterior e documentado:

- **09/07/2021** — Anvisa publica alerta sobre risco de miocardite e pericardite pós-vacinação com imunizantes de RNAm, orienta notificação pelo VigiMed, Notivisa e e-SUS Notifica, e **mantém a recomendação de continuidade da vacinação**.
- **15/09/2021** — Nota Técnica nº 1057/2021-CGPNI/DEIDT/SVS/MS, sobre identificação e investigação dos eventos.
- **Maio/2022** — Nota Técnica nº 139/2022-CGPNI/DEIDT/SVS/MS, vigente, com os dados de incidência brasileiros: 222 eventos identificados entre 18/01/2021 e 12/03/2022, dos quais 87 com diagnóstico sindrômico pelos níveis 1 a 3 de Brighton (66 após Pfizer/Comirnaty); incidência total de **0,02 por 100.000 doses** e **0,05 por 100.000 doses** após Pfizer, sobre 126.770.933 doses aplicadas; **2 óbitos** no período (1 após Pfizer, causalidade B2 — dados conflitantes; 1 após AstraZeneca, causalidade D — inclassificável).
- A mesma nota mantém a recomendação de vacinação sem restrições.

**Ponto de leitura para a resposta:** a nota brasileira e o artigo israelense não se contradizem no que medem. O Brasil mede incidência por dose (0,05/100.000 após Pfizer) — que é exatamente a métrica que o conjunto israelense **não permite** calcular, como os próprios autores reconhecem. O artigo mede outra coisa: o intervalo entre o alerta interno e a comunicação pública. Confundir as duas métricas é o erro central da peça.

---

## 8. Risco de propagação e dano comunicacional

| Elemento | Avaliação |
|---|---|
| Alcance atual no fluxo monitorado | Indetectado no Acre no período de 90 dias |
| Potencial de circulação | **Alto** — a peça é reaproveitável: tem manchete forte, número específico, revista com nome próprio e um bloco de ressalvas que dá aparência de equilíbrio |
| Tipo de dano | Erosão de confiança e hesitação vacinal, com alvo preferencial em **homens jovens e seus responsáveis** — justamente o grupo em que miocardite/pericardite é mais incidente e onde a hesitação tem custo epidemiológico |
| Dano secundário | Uso da peça para atacar a credibilidade dos estudos israelenses de farmacovigilância, que são a base de boa parte do que se sabe sobre o tema |
| Mitigação pelo próprio conteúdo | As ressalvas do corpo reduzem o dano para quem lê o texto inteiro; o risco concentra-se na **reprodução da manchete isolada**, formato típico de compartilhamento em imagem |

---

## 9. Resposta pronta (comunicação de risco)

Estrutura "o que se sabe / o que não se sabe / o que está sendo feito":

**O que se sabe.** Miocardite e pericardite são eventos adversos raros, reconhecidos oficialmente, associados às vacinas de RNA mensageiro contra a COVID-19, com maior incidência em homens jovens e adolescentes após a segunda dose. Não são um achado novo nem um achado oculto: a Anvisa alertou a população brasileira sobre isso em julho de 2021, o Ministério da Saúde publicou nota técnica sobre o manejo em setembro de 2021 e a atualizou em 2022, e a bula do produto passou a trazer a informação. O evento adverso existe, é vigiado e é notificável.

**O que não se sabe — e o que a peça erra.** A peça em circulação afirma que um estudo "indicou que a vacina afetava diretamente o coração". O estudo citado não conclui isso e diz expressamente o contrário: por ser um conjunto de notificações de casos, sem denominador populacional e sem grupo de comparação, **não permite estabelecer causalidade nem calcular risco**. O que ele examina é outra coisa — quanto tempo Israel levou para comunicar ao público um sinal de segurança que já tinha em mãos. Manchete e estudo tratam de assuntos distintos.

**O que está sendo feito.** O Brasil mantém vigilância de eventos adversos pós-vacinação pelo e-SUS Notifica, VigiMed e Notivisa, com investigação padronizada pelos critérios de Brighton e discussão de causalidade pelo Cifavi. A recomendação vigente de vacinação contra a COVID-19 permanece, e os dados brasileiros de incidência estão publicados na Nota Técnica nº 139/2022.

**Regra de ouro para a resposta:** não negar o evento adverso. Negá-lo destrói a credibilidade da resposta e valida a peça. O caminho é afirmá-lo com o número oficial em mãos (0,05 por 100.000 doses após Pfizer, no Brasil) e mostrar onde a peça troca o assunto.

---

## 10. Recomendações ao SVI-AC

1. **Pré-posicionar, não esperar o pico.** O tema está indetectado agora. Preparar a resposta como prebunking — incluída no módulo de aula já existente sobre reconhecimento de desinformação — em vez de guardá-la para uso reativo.
2. **Adicionar um boato à base.** Nenhum dos 10 boatos semeados cobre corretamente este padrão. vacina_mata ("alegações de mortes em larga escala") distorce o caso: aqui não se alega escala, alega-se uma conclusão que a fonte não tem. Proposta: incluir o boato **estudo_distorcido** — "estudo real citado ao contrário", com táticas falsa causalidade e fonte real fora de contexto. É o padrão mais frequente e o único que a base atual não captura.
3. **Alerta de monitoramento para o termo.** Incluir "miocardite" e "pericardite" entre os termos monitorados, que hoje não existem na configuração.
4. **Rotular a peça por padrão, não por assunto.** Para este caso, o rótulo útil não é "peça antivacina", e sim "estudo real com conclusão invertida na manchete" — categoria que orienta a resposta correta e evita o desgaste de desmentir o que é verdadeiro.

---

## Anexo A — Rastreabilidade da triagem

**Data da verificação:** 13/10/2026.

**Peça analisada:** imagem recebida por Telegram, arquivo img_43904d2c6a82.jpg. Texto em português, fundo preto. **Sem veículo, sem assinatura e sem data** — a ausência desses elementos impede atribuir autoria e datar a primeira publicação. Órgão de verificação: ainda pendente (Anexo B).

**Fonte primária localizada por:** busca na Europe PMC, consulta JOURNAL:"EXCLI Journal" AND myocarditis.

**Fonte primária:**
- Ophir Y, Shir-Raz Y. Real-time pharmacovigilance and cardiac risk communication during the COVID-19 vaccination campaign in Israel. **EXCLI J.** 2026;25:1437–1457. DOI 10.17179/excli2026-9596. PMCID PMC13639178. PMID 42840454. Recebido em 08/06/2026, aceito em 09/08/2026, publicado em 03/09/2026. Licença CC-BY.
- Texto completo e material suplementar obtidos via Europe PMC.
- Dado bruto verificado: EXCLI-25-1437-s-001.xlsx (532 linhas de origem em Hospitalizations, 62 em Deaths, mais o codebook).

**Fontes oficiais brasileiras consultadas:**
- Anvisa. Anvisa alerta sobre risco de miocardite e pericardite pós-vacinação. Publicado em 09/07/2021.
- Ministério da Saúde. **Nota Técnica nº 139/2022-CGPNI/DEIDT/SVS/MS.** Assinada eletronicamente em 13/05/2022. Processo SEI nº 25000.128409/2021-53.
- Ministério da Saúde. Nota Técnica nº 1057/2021-CGPNI/DEIDT/SVS/MS, de 15/09/2021 (referenciada na anterior).

**Base interna consultada:** infodemia.db do SVI-AC, 257 menções, período de 13/07/2026 a 12/10/2026. Busca por "miocard", "pericard", "excli", "israel", "coração" e "cora" retornou **zero** menções.

**O que NÃO foi encontrado:**
- Veículo, autor, data ou primeira publicação da peça.
- Descartei a hipótese de que o texto da peça seja de veículo identificável: a imagem não traz elementos de origem.
- Não confirmei se o artigo está indexado no MEDLINE.
- Não localizei o PDF do Comunicado 007/2021 da Anvisa para conferência direta (citado a partir da página da Anvisa que o referencia).

---

## Anexo B — Pendências para validação

- [ ] Identificar o veículo ou perfil que originou a peça (busca por imagem reversa e monitoramento de grupos no Acre).
- [ ] Confirmar se a peça circulou em canais fechados (WhatsApp e grupos locais não são cobertos pela coleta atual).
- [ ] Decidir sobre a inclusão do boato estudo_distorcido na base do SVI — requer alteração em scripts/boatos.py.
- [ ] Decidir sobre a inclusão de "miocardite" e "pericardite" em scripts/config.json.
- [ ] Baixar e arquivar o Comunicado 007/2021 da Anvisa como peça de referência da resposta pronta.
- [ ] Validar a resposta pronta com a área técnica responsável pela imunização antes de qualquer uso em comunicação externa.
