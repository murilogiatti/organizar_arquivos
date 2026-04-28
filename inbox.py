#!/usr/bin/env python3
"""
inbox.py
Distribui tudo que estiver em ~/inbox/ para as pastas corretas,
organizando por categoria e ano (baseado na data de modificação).

Estrutura de destino:
    ~/
    ├── imagens/    YYYY/  arquivo
    ├── videos/     YYYY/  arquivo
    ├── musica/     YYYY/  arquivo
    ├── documentos/ YYYY/  arquivo
    ├── dev/        YYYY/  arquivo
    └── documentos/ YYYY/Outros/  (extensões não reconhecidas)

Performance:
  • Fase 1: os.scandir() paralelo para coletar todos os arquivos
  • Fase 2: stat() paralelo para calcular ano+categoria de cada arquivo
  • Fase 3: exibe plano agrupado por destino
  • Fase 4: shutil.move() paralelo para mover todos os arquivos
  • Fase 5: limpeza sequencial de pastas vazias (obrigatório)

Uso:
    python3 inbox.py             # simulação (não move nada)
    python3 inbox.py --executar  # executa de verdade
"""

import os
import sys
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from collections import defaultdict

# ── Configuração ─────────────────────────────────────────────
# Ajuste BASE e INBOX para o seu ambiente
BASE   = Path.home()
INBOX  = BASE / "inbox"
WORKERS = 32

DESTINOS = {
    "Imagens":    BASE / "imagens",
    "Videos":     BASE / "videos",
    "Musica":     BASE / "musica",
    "Documentos": BASE / "documentos",
    "Dev":        BASE / "dev",
}

# ── Extensões ────────────────────────────────────────────────
EXT: dict[str, set[str]] = {
    "Imagens":    {".jpg",".jpeg",".png",".gif",".bmp",".webp",".tiff",".tif",
                   ".ico",".heic",".heif",".raw",".cr2",".nef",".arw",".svg"},
    "Videos":     {".mp4",".mkv",".avi",".mov",".wmv",".flv",".webm",".m4v",
                   ".mpg",".mpeg",".3gp",".ts",".vob"},
    "Musica":     {".mp3",".wav",".flac",".aac",".ogg",".wma",".m4a",".opus",
                   ".aiff",".mid",".midi"},
    "Dev":        {".py",".js",".ts",".html",".htm",".css",".json",".xml",
                   ".yaml",".yml",".toml",".sql",".sh",".bash",
                   ".bat",".ps1",".psm1"},
    "Documentos": {".pdf",".doc",".docx",".xls",".xlsx",".ppt",".pptx",
                   ".txt",".odt",".ods",".odp",".csv",".rtf",".md",".text",
                   ".ffs_batch",".ffs_gui",".ffs_real",".reg",".ini",".cfg",
                   ".conf",".bak",".log",
                   ".eml",".msg",".mbox",
                   ".exe",".msi",".iso",".dmg",".deb",".rpm",".appimage",
                   ".apk",".pkg",
                   ".zip",".rar",".7z",".tar",".gz",".bz2",".xz",
                   ".zst",".cab",".ace"},
}
EXT_DUPLAS = {".tar.gz", ".tar.bz2", ".tar.xz"}

# Lookup reverso: extensão → categoria (O(1))
EXT_MAP: dict[str, str] = {}
for _cat, _exts in EXT.items():
    for _e in _exts:
        EXT_MAP[_e] = _cat

# ── Cores ANSI ───────────────────────────────────────────────
V  = "\033[0;32m"
A  = "\033[1;33m"
AZ = "\033[0;34m"
R  = "\033[0;31m"
CZ = "\033[0;37m"
N  = "\033[0m"

# ── Helpers ──────────────────────────────────────────────────

def classificar(arquivo: Path) -> tuple[str, str]:
    nome = arquivo.name.lower()
    for ext_dupla in EXT_DUPLAS:
        if nome.endswith(ext_dupla):
            return ("Documentos", "")
    cat = EXT_MAP.get(arquivo.suffix.lower())
    if cat:
        return (cat, "")
    return ("Documentos", "Outros")

def calcular_arquivo(arq: Path) -> tuple[Path, str, str, int | None]:
    """Retorna (arquivo, cat, sub, ano) — chamado em paralelo."""
    try:
        ano = datetime.fromtimestamp(arq.stat().st_mtime).year
    except Exception:
        ano = None
    cat, sub = classificar(arq)
    return (arq, cat, sub, ano)

def destino_seguro(destino_dir: Path, nome: str) -> Path:
    destino = destino_dir / nome
    if not destino.exists():
        return destino
    stem = Path(nome).stem
    ext  = Path(nome).suffix
    contador = 1
    while (destino_dir / f"{stem}_({contador}){ext}").exists():
        contador += 1
    return destino_dir / f"{stem}_({contador}){ext}"

def barra(atual, total, largura=40):
    pct  = atual / total if total else 0
    fill = int(largura * pct)
    return f"\r  [{'█'*fill}{'░'*(largura-fill)}] {atual}/{total} ({pct*100:.0f}%)"

def clean(text):
    """Sanitiza texto para exibição segura no terminal, escapando caracteres não imprimíveis."""
    if not isinstance(text, str):
        text = str(text)
    return "".join(c if c.isprintable() else c.encode("unicode_escape").decode("ascii") for c in text)

def separador(titulo):
    print(f"\n{AZ}━━━ {titulo} {'━' * max(1, 52 - len(titulo))}{N}")

# ── Coleta recursiva com os.scandir paralelo ─────────────────

def coletar_arquivos(raiz: Path) -> list[Path]:
    arquivos: list[Path] = []
    pastas:   list[Path] = [raiz]

    while pastas:
        lote   = pastas[:WORKERS]
        pastas = pastas[WORKERS:]

        def escanear(d: Path):
            arqs, dirs = [], []
            try:
                for entry in os.scandir(d):
                    if entry.is_file(follow_symlinks=False):
                        arqs.append(Path(entry.path))
                    elif entry.is_dir(follow_symlinks=False):
                        dirs.append(Path(entry.path))
            except PermissionError:
                pass
            return arqs, dirs

        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for arqs, dirs in ex.map(escanear, lote):
                arquivos.extend(arqs)
                pastas.extend(dirs)

    return arquivos

# ── Main ─────────────────────────────────────────────────────

def main():
    executar = "--executar" in sys.argv

    if not executar:
        print(f"{A}⚠  MODO SIMULAÇÃO — nenhum arquivo será movido.")
        print(f"   Use: python3 inbox.py --executar{N}\n")
    else:
        print(f"{V}▶  MODO EXECUÇÃO{N}\n")

    if not INBOX.exists():
        print(f"{R}Erro: pasta não encontrada: {clean(INBOX)}{N}")
        sys.exit(1)

    print(f"{AZ}📥 Inbox  : {clean(INBOX)}{N}")
    print(f"{AZ}⚡ Workers: {WORKERS}{N}\n")

    # ══════════════════════════════════════════════════════════
    # FASE 1 — Coleta todos os arquivos recursivamente
    # ══════════════════════════════════════════════════════════
    separador("FASE 1: COLETANDO ARQUIVOS")
    print(f"  {CZ}Varrendo inbox/...{N}", end="", flush=True)

    arquivos = coletar_arquivos(INBOX)

    if not arquivos:
        print(f"\r  {CZ}inbox/ está vazio. Nada a fazer.{N}          ")
        sys.exit(0)

    print(f"\r  {V}✓{N} {len(arquivos)} arquivo(s) encontrado(s).          ")

    # ══════════════════════════════════════════════════════════
    # FASE 2 — Calcula ano + categoria em paralelo
    # ══════════════════════════════════════════════════════════
    separador("FASE 2: CALCULANDO DESTINOS")

    resultados: list[tuple[Path, str, str, int | None]] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futuros = {ex.submit(calcular_arquivo, arq): arq for arq in arquivos}
        for idx, fut in enumerate(as_completed(futuros), 1):
            print(barra(idx, len(arquivos)), end="", flush=True)
            resultados.append(fut.result())
    print()

    erros = sum(1 for _, _, _, ano in resultados if not ano)
    print(f"  {V}✓{N} Calculados. {erros} sem data." if erros else f"  {V}✓{N} Todos com data detectada.")

    # ══════════════════════════════════════════════════════════
    # FASE 3 — Exibe plano agrupado por destino
    # ══════════════════════════════════════════════════════════
    separador("FASE 3: PLANO DE DISTRIBUIÇÃO")

    por_destino: dict[str, list[str]] = defaultdict(list)
    plano_mover: list[tuple[Path, Path]] = []
    sem_ano:     list[Path]             = []

    for arq, cat, sub, ano in sorted(resultados, key=lambda x: (x[1], x[3] or 0, x[0].name)):
        if not ano:
            sem_ano.append(arq)
            continue
        dest_dir = DESTINOS[cat] / str(ano)
        if sub:
            dest_dir = dest_dir / sub
        destino  = destino_seguro(dest_dir, arq.name)
        chave    = f"{cat}/{ano}{'/' + sub if sub else ''}"
        conflito = f" {A}⚠ → {clean(destino.name)}{N}" if destino.name != arq.name else ""
        por_destino[chave].append(f"{clean(arq.name)}{conflito}")
        plano_mover.append((arq, dest_dir, destino))

    for chave, nomes in por_destino.items():
        print(f"\n  {AZ}→ {chave}/ ({len(nomes)} arquivo(s)){N}")
        for nome in nomes[:5]:
            print(f"    {V}+{N} {nome}")
        if len(nomes) > 5:
            print(f"    {CZ}... e mais {len(nomes) - 5} arquivo(s){N}")

    if sem_ano:
        print(f"\n  {R}Sem data ({len(sem_ano)} arquivo(s)):{N}")
        for arq in sem_ano[:5]:
            print(f"    {R}✗{N} {clean(arq.name)}")

    # ══════════════════════════════════════════════════════════
    # FASE 4 — Move arquivos em paralelo
    # ══════════════════════════════════════════════════════════
    movidos = 0
    erros   = len(sem_ano)

    if executar:
        separador("FASE 4: MOVENDO ARQUIVOS")

        destinos_unicos = {dest_dir for _, dest_dir, _ in plano_mover}
        for d in destinos_unicos:
            d.mkdir(parents=True, exist_ok=True)

        def mover_arquivo(par):
            arq, dest_dir, destino = par
            try:
                shutil.move(str(arq), str(destino))
                return ("ok", arq)
            except Exception as e:
                return ("erro", arq, str(e))

        total = len(plano_mover)
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futuros = {ex.submit(mover_arquivo, par): par for par in plano_mover}
            for idx, fut in enumerate(as_completed(futuros), 1):
                print(barra(idx, total), end="", flush=True)
                res = fut.result()
                if res[0] == "ok":
                    movidos += 1
                else:
                    print(f"\n  {R}✗ {clean(res[1].name)}: {clean(res[2])}{N}")
                    erros += 1
        print()
    else:
        movidos = len(plano_mover)

    # ══════════════════════════════════════════════════════════
    # FASE 5 — Limpa pastas vazias do inbox/
    # ══════════════════════════════════════════════════════════
    separador("FASE 5: LIMPANDO INBOX/")
    vazias = 0

    if executar:
        todas_pastas = sorted(
            [Path(d) for d, _, _ in os.walk(INBOX)],
            key=lambda p: len(p.parts),
            reverse=True
        )
        for pasta in todas_pastas:
            if pasta == INBOX:
                continue
            try:
                pasta.rmdir()
                print(f"  {A}🗑  {clean(pasta.relative_to(INBOX))}/{N}")
                vazias += 1
            except OSError:
                pass

        restantes = list(INBOX.iterdir())
        if restantes:
            print(f"  {A}⚠  {len(restantes)} item(ns) restante(s) — verifique manualmente.{N}")
        else:
            print(f"  {V}✓ inbox/ limpo.{N}")
    else:
        print(f"  {A}(simulação — inbox/ não será limpo){N}")

    # ── Resumo ───────────────────────────────────────────────
    separador("RESUMO")
    print(f"  🗂  Arquivos movidos  : {movidos}")
    print(f"  🗑  Pastas removidas  : {vazias}")
    print(f"  ❌ Erros             : {erros}")

    if not executar:
        print(f"\n{A}Simulação concluída. Para executar:{N}")
        print(f"  {V}python3 inbox.py --executar{N}")
    print()

if __name__ == "__main__":
    main()
