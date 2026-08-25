#!/bin/bash
# Cron 06:50 — coleta + análise de infodemia (SVI-AC)
# Roda init_db (idempotente), coleta ao vivo e análise. Stdout = resumo.
# Localiza a raiz do projeto independente de onde o script for chamado
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="$PWD/scripts"

python3 scripts/init_db.py >/dev/null 2>&1
python3 scripts/coleta.py >/tmp/infodemia_coleta.json 2>/tmp/infodemia_coleta.err
if [ $? -ne 0 ]; then
    echo "ERRO na coleta de infodemia:"
    tail -5 /tmp/infodemia_coleta.err
    exit 1
fi
python3 scripts/analise.py >/tmp/infodemia_analise.json 2>/tmp/infodemia_analise.err

# Resumo curto para o log local (deliver=local)
python3 - <<'EOF'
import json
try:
    c = json.load(open('/tmp/infodemia_coleta.json'))
    a = json.load(open('/tmp/infodemia_analise.json'))
    print(f"[{c.get('data')}] mencoes={c.get('mencoes')} picos={len(a.get('picos', []))} boatos_detectados={a.get('boatos_detectados', 0)}")
except Exception as e:
    print(f"resumo indisponível: {e}")
EOF
