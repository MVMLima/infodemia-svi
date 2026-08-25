#!/usr/bin/env python3
"""
boatos.py — Base de conhecimento de desinformação em saúde (SVI-AC).

Contém os boatos recorrentes sobre vacinas/pandemia, suas táticas de
desinformação, keywords de detecção e narrativas substitutas prontas
para resposta (prebunking/debunking).

Uso:
    from boatos import match_boato, listar_boatos, seed_boatos
"""
import json
import sqlite3
import unicodedata
from typing import Dict, List, Optional

from paths import db_path

DB_PATH = db_path()

# ---------------------------------------------------------------------------
# Boatos (seed)
# slug: identificador único usado no banco e no matching
# taticas: técnicas de desinformação usadas (prebunking)
# keywords: termos de detecção (normalizados)
# narrativa_substituta: resposta pronta, objetiva, com fontes oficiais
# ---------------------------------------------------------------------------
BOATOS_SEED: List[Dict] = [
    {
        "slug": "pandemia_fabricada",
        "nome": "Pandemia fabricada",
        "descricao": "Alegação de que a pandemia de COVID-19 foi inventada ou planejada.",
        "taticas": ["teoria da conspiração", "falsa autoridade"],
        "keywords": ["fabricada", "invencao", "farsa", "nao existiu", "criada em laboratorio", "plandemia", "armacao"],
        "narrativa_substituta": "A pandemia de COVID-19 foi reconhecida pela Organização Mundial da Saúde (OMS) e confirmada por sistemas de saúde do mundo inteiro: hospitais lotados, óbitos registrados e profissionais de saúde sobrecarregados. Foi um fenômeno real e documentado. Questionar os números é legítimo, mas a negação total contraria o consenso científico e as evidências observadas no mundo real.",
        "fontes_oficiais": ["https://www.who.int", "https://www.gov.br/saude/pt-br", "https://www.paho.org/pt"],
    },
    {
        "slug": "chip_vacina",
        "nome": "Chip ou microchip na vacina",
        "descricao": "Alegação de que vacinas contêm microchips para rastreamento.",
        "taticas": ["impossibilidade", "teoria da conspiração"],
        "keywords": ["chip", "microchip", "rastreamento", "controle mental", "implantado"],
        "narrativa_substituta": "Não existe microchip em vacina: as vacinas contêm apenas os componentes descritos na bula e nos estudos de registro, aprovados por agências reguladoras (Anvisa no Brasil). A alegação do chip nasceu de uma interpretação equivocada de uma declaração sobre identificação digital de frascos, não sobre pessoas. Verifique a bula e o registro do imunobiológico em fontes oficiais.",
        "fontes_oficiais": ["https://www.gov.br/anvisa/pt-br", "https://www.gov.br/saude/pt-br"],
    },
    {
        "slug": "vacina_autismo",
        "nome": "Vacina causa autismo",
        "descricao": "Alegação de ligação entre vacinas e autismo, baseada em estudo retratado.",
        "taticas": ["falsa autoridade", "cherry-picking"],
        "keywords": ["autismo", "autista"],
        "narrativa_substituta": "A suposta ligação entre vacina e autismo vem de um estudo de 1998 que foi retratado pela revista científica que o publicou, e seu autor perdeu o registro médico por fraude. Estudos com milhões de crianças em vários países não encontraram nenhuma relação entre vacinas e autismo. O consenso científico é claro: vacinas não causam autismo.",
        "fontes_oficiais": ["https://www.who.int", "https://www.gov.br/saude/pt-br"],
    },
    {
        "slug": "vacina_mata",
        "nome": "Vacina mata",
        "descricao": "Alegação de que vacinas causam mortes em larga escala.",
        "taticas": ["apelo à emoção", "falsa causalidade"],
        "keywords": ["mata", "morreu por causa da vacina", "reacao fatal", "mortes pela vacina"],
        "narrativa_substituta": "Qualquer medicamento pode ter reações adversas, e vacinas não são exceção — por isso existe vigilância de eventos adversos (como o e-SUS Notifica no Brasil). Mas a esmagadora maioria das reações é leve e temporária. Comparar o risco raríssimo de reação grave com o risco real e alto de doença grave sem vacina é a base da decisão de saúde pública.",
        "fontes_oficiais": ["https://www.gov.br/saude/pt-br", "https://www.who.int"],
    },
    {
        "slug": "covid_gripezinha",
        "nome": "Covid é gripezinha",
        "descricao": "Minimização da gravidade da COVID-19.",
        "taticas": ["falsa dicotomia", "minimização"],
        "keywords": ["gripezinha", "resfriado", "exagero", "e so uma gripe"],
        "narrativa_substituta": "A COVID-19 matou milhões de pessoas no mundo e deixou sequelas documentadas (fadiga, problemas respiratórios, neurológicos). Dizer que é uma gripezinha contraria os dados de internações e óbitos. Toda doença respiratória merece cuidado, mas tratar riscos diferentes como iguais não ajuda a população.",
        "fontes_oficiais": ["https://www.who.int", "https://www.gov.br/saude/pt-br"],
    },
    {
        "slug": "vacina_alterar_dna",
        "nome": "Vacina altera o DNA",
        "descricao": "Alegação de que vacinas de mRNA alteram o material genético.",
        "taticas": ["impossibilidade", "falsa causalidade"],
        "keywords": ["altera o dna", "modifica o dna", "mutacao", "genetica", "edicao genetica"],
        "narrativa_substituta": "As vacinas de RNA mensageiro (mRNA) não entram no núcleo da célula, onde fica o DNA — elas ensinam a célula a produzir uma proteína e são degradadas em seguida. Não há mecanismo biológico para alterar o DNA, e os estudos de acompanhamento confirmam isso. É biologia básica, verificável em qualquer livro-texto e em fontes oficiais de saúde.",
        "fontes_oficiais": ["https://www.gov.br/saude/pt-br", "https://www.cdc.gov"],
    },
    {
        "slug": "cura_escondida",
        "nome": "Cura escondida",
        "descricao": "Alegação de que existe cura para a COVID-19 escondida pela indústria.",
        "taticas": ["teoria da conspiração", "bode expiatório"],
        "keywords": ["cura escondida", "escondem a cura", "remedio escondido", "big pharma", "ivermectina", "cloroquina", "hidroxicloroquina"],
        "narrativa_substituta": "Não existe cura escondida para a COVID-19: medicamentos testados em estudos rigorosos (como ivermectina e cloroquina) não mostraram eficácia contra a doença. Uma cura real não pode ser escondida — o mercado farmacêutico lucraria muito mais vendendo uma cura comprovada do que escondendo. Tratamentos comprovados (oxigênio, antivirais, vacinação) estão disponíveis nos serviços de saúde.",
        "fontes_oficiais": ["https://www.gov.br/saude/pt-br", "https://www.who.int"],
    },
    {
        "slug": "numeros_inflados",
        "nome": "Números de óbitos inflados",
        "descricao": "Alegação de que os números de casos e óbitos foram inflados.",
        "taticas": ["teoria da conspiração", "falsa causalidade"],
        "keywords": ["inflados", "numeros falsos", "obitos falsos", "mortes falsas", "superfaturados"],
        "narrativa_substituta": "Os sistemas de vigilância (como o e-SUS e o SIVEP-Gripe no Brasil) registraram casos e óbitos com critérios definidos e auditados. Subnotificação é um problema real em qualquer sistema — mas ela aponta para números menores que a realidade, não inventados. Revisões e auditorias públicas dos dados são bem-vindas e já acontecem.",
        "fontes_oficiais": ["https://www.gov.br/saude/pt-br", "https://www.paho.org/pt"],
    },
    {
        "slug": "vacina_experimental",
        "nome": "Vacina experimental",
        "descricao": "Alegação de que as vacinas foram aplicadas sem testes suficientes.",
        "taticas": ["falsa autoridade", "apelo à emoção"],
        "keywords": ["experimental", "teste em humanos", "sem teste", "apressada", "cobaia", "cobaias"],
        "narrativa_substituta": "As vacinas contra a COVID-19 passaram por todas as fases de estudo exigidas, com milhares de voluntários, antes da aprovação emergencial — e depois foram acompanhadas por sistemas de vigilância de eventos adversos. A rapidez veio de investimento e tecnologia (mRNA já era estudada há décadas), não de cortar etapas. A aprovação pela Anvisa foi pública e documentada.",
        "fontes_oficiais": ["https://www.gov.br/anvisa/pt-br", "https://www.gov.br/saude/pt-br"],
    },
    {
        "slug": "vacina_infertilidade",
        "nome": "Vacina causa infertilidade",
        "descricao": "Alegação de que vacinas afetam a fertilidade ou a gestação.",
        "taticas": ["impossibilidade", "apelo à emoção"],
        "keywords": ["infertilidade", "esterilidade", "gravidez", "aborto", "nao engravida"],
        "narrativa_substituta": "Não há evidência de que vacinas afetem a fertilidade — estudos de acompanhamento não encontraram diferença nas taxas de gravidez entre vacinadas e não vacinadas. Pelo contrário: a vacinação é recomendada para gestantes justamente porque a COVID-19 grave é um risco maior para elas e para o bebê. Consulte seu médico e as orientações oficiais.",
        "fontes_oficiais": ["https://www.gov.br/saude/pt-br", "https://www.who.int"],
    },
]


def normalizar(texto: str) -> str:
    """Lowercase + remove acentos + colapsa espaços."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())


# Contexto mínimo de saúde/vacina exigido para evitar falsos positivos
# (ex: 'mata-mata da copa' não deve disparar 'vacina mata')
CONTEXTO_SAUDE = [
    "vacina", "vacinacao", "imuniza", "covid", "pandemia", "coronavirus",
    "dose", "imunizante", "campanha de vacin", "cobertura vacin",
    "sivep", "srag", "doenca", "epidemia",
]


def seed_boatos(conn: sqlite3.Connection) -> int:
    """Insere os boatos padrão se a tabela estiver vazia. Retorna nº inseridos."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM boatos")
    if cursor.fetchone()[0] > 0:
        return 0
    for b in BOATOS_SEED:
        cursor.execute(
            """
            INSERT OR IGNORE INTO boatos
            (slug, nome, descricao, taticas, keywords, narrativa_substituta, fontes_oficiais, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ativo')
            """,
            (
                b["slug"], b["nome"], b["descricao"],
                json.dumps(b["taticas"], ensure_ascii=False),
                json.dumps(b["keywords"], ensure_ascii=False),
                b["narrativa_substituta"],
                json.dumps(b["fontes_oficiais"], ensure_ascii=False),
            ),
        )
    conn.commit()
    return len(BOATOS_SEED)


def listar_boatos(conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """Retorna todos os boatos ativos do banco (seed se vazio)."""
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(DB_PATH)
        seed_boatos(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, nome, descricao, taticas, keywords, narrativa_substituta, fontes_oficiais, status FROM boatos WHERE status='ativo'")
    rows = cursor.fetchall()
    if own_conn:
        conn.close()
    boatos = []
    for r in rows:
        boatos.append({
            "id": r[0], "slug": r[1], "nome": r[2], "descricao": r[3],
            "taticas": json.loads(r[4]) if r[4] else [],
            "keywords": json.loads(r[5]) if r[5] else [],
            "narrativa_substituta": r[6],
            "fontes_oficiais": json.loads(r[7]) if r[7] else [],
            "status": r[8],
        })
    return boatos


def match_boato(texto: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict]:
    """
    Retorna o boato cuja keyword casa com o texto (ou None).

    Anti-falso-positivo:
    - O texto precisa conter contexto de saúde/vacina (CONTEXTO_SAUDE).
    - Keywords de palavra única casam por word boundary (regex \\b), não substring
      (ex: 'mata' não casa 'mata-mata da copa', 'chip' não casa 'chip de segurança').
    """
    if not texto:
        return None
    texto_norm = normalizar(texto)

    # Sem contexto de saúde/vacina, não é candidato a boato vacinal
    if not any(ctx in texto_norm for ctx in CONTEXTO_SAUDE):
        return None

    import re
    for b in listar_boatos(conn):
        for kw in b["keywords"]:
            kw_norm = normalizar(kw)
            if " " in kw_norm:
                # keyword multi-palavra: substring normal
                if kw_norm in texto_norm:
                    return b
            else:
                # palavra única: word boundary
                if re.search(rf"\b{re.escape(kw_norm)}\b", texto_norm):
                    return b
    return None


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    n = seed_boatos(conn)
    conn.close()
    print(f"Seed concluído: {n} boatos inseridos em {DB_PATH}")
