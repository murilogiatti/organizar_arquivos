# inbox.py

Script Python para distribuir automaticamente arquivos de uma pasta de entrada (`~/inbox/`) para pastas organizadas por **categoria** e **ano**, usando paralelismo para máxima performance.

## Estrutura de destino

```
~/
├── inbox/          ← pasta de entrada (arquivos a distribuir)
├── imagens/
│   └── 2024/
├── videos/
│   └── 2024/
├── musica/
│   └── 2024/
├── documentos/
│   └── 2024/
│       └── Outros/   ← extensões não reconhecidas
└── dev/
    └── 2024/
```

O ano é detectado automaticamente pela **data de modificação** de cada arquivo.

## Uso

```bash
# Simulação — mostra o que seria feito, sem mover nada
python3 inbox.py

# Execução real
python3 inbox.py --executar
```

Sempre rode a simulação primeiro para revisar o plano antes de executar.

## Categorias e extensões

| Categoria    | Extensões                                                                 |
|--------------|---------------------------------------------------------------------------|
| `imagens`    | jpg, jpeg, png, gif, bmp, webp, tiff, heic, raw, cr2, nef, arw, svg, … |
| `videos`     | mp4, mkv, avi, mov, wmv, flv, webm, m4v, mpg, 3gp, ts, …               |
| `musica`     | mp3, wav, flac, aac, ogg, wma, m4a, opus, aiff, mid, …                  |
| `dev`        | py, js, ts, html, css, json, yaml, sql, sh, bat, ps1, …                 |
| `documentos` | pdf, docx, xlsx, pptx, txt, csv, zip, rar, exe, iso, eml, …             |

Arquivos com extensão não reconhecida vão para `documentos/YYYY/Outros/`.  
Conflitos de nome são resolvidos automaticamente com sufixo `_(1)`, `_(2)`, etc.

## Configuração

Edite as variáveis no topo do script para adaptar ao seu ambiente:

```python
BASE    = Path.home()          # raiz das pastas de destino
INBOX   = BASE / "inbox"       # pasta de entrada
WORKERS = 32                   # threads paralelas
```

Para usar uma estrutura diferente de destino, edite o dicionário `DESTINOS`.

## Como funciona

O script opera em 5 fases:

1. **Coleta** — varre `inbox/` recursivamente com `os.scandir()` em paralelo
2. **Classificação** — calcula categoria e ano de cada arquivo em paralelo (`stat()`)
3. **Plano** — exibe um resumo agrupado do que será movido
4. **Movimentação** — move todos os arquivos em paralelo com `shutil.move()`
5. **Limpeza** — remove subpastas vazias deixadas em `inbox/`

## Requisitos

- Python 3.10+
- Sem dependências externas (só biblioteca padrão)
