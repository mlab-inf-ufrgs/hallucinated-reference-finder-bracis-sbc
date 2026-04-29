# halref — Hallucinated Reference Finder (adaptação BRACIS / SBC)

Fork do projeto [**hallucinated-reference-finder**](https://github.com/davidjurgens/hallucinated-reference-finder) (David Jurgens) focado em **PDFs de artigos** com bibliografia no estilo **SBC** (Sociedade Brasileira de Computação) e **BRACIS** (formato numerado tipo LNCS/Springer, usado nas submissões da conferência BRACIS).

O objetivo é **extrair referências** do PDF (local), **consultar bases académicas** (metadados apenas) e **atribuir um score de risco** de alucinação / inconsistência face ao que existe nas APIs.

---

## Atualizações deste fork (resumo)

- **Secção de referências**: cabeçalhos em **português** (`Referências`, `Bibliografia`, …) e variante **`Referˆencias`** (encoding comum em PDFs); fim de secção com termos PT (**Apêndice**, **Agradecimentos**, …).
- **Divisão em referências individuais**: estratégias para listas **`[1]`, `[2]`** (BRACIS/LNCS), anos **`(AAAA)`**, e melhor escolha entre extractores (`pdfminer`, `pypdf`, `pdfplumber`).
- **Parsing SBC (natbib / Vancouver)**: títulos já **não** começam com artefacto **`).`** após `(ano)`; **vários autores** com listas `Sobrenome, X., Sobrenome2, Y.` e remoção de `et al.`.
- **Estilos**: deteção automática **SBC** vs **BRACIS**; parsers dedicados (`SBCFieldParser`, `BRACISFieldParser`). A pasta `new-styles/` contém **documentação** e ficheiros `.bst` de referência (não são lidos em runtime).
- **Relatórios**: flag `--risk-reports` gera `risk_summary.md` / `.csv` e, por artigo, `reports/detail_<ID>.md` com componentes do score (título, autores, ano, consenso) e nível de risco.
- **CLI**: `halref check`, `halref extract`, `halref check-bib` (ver `python -m halref.cli --help`).

---

## Pipeline de execução (fim a fim)

1. **Entrada** — Um ou mais ficheiros `.pdf` (ou pasta), opcionalmente `.bib` com `check-bib`.
2. **Extração de texto** — Extractores configuráveis lêem o PDF, localizam o bloco **Referências / Bibliografia**, e devolvem só esse texto.
3. **Segmentação** — O texto é partido em **uma string por referência** (linhas em branco, padrão autor–ano, marcadores `[N]`, etc.).
4. **Deteção de estilo** — Heurística conta padrões **SBC** vs **BRACIS** (`[N]` no início da linha, etc.).
5. **Parsing de campos** — Conjunto de parsers (SBC, BRACIS, regex, heuristic, …) preenche `Reference` (título, autores, ano, venue, DOI, …).
6. **Filtros** — Entradas com baixa confiança ou falsos positivos óbvios são descartadas antes da verificação.
7. **Verificação (rede)** — Para cada referência, agente consulta APIs (**Semantic Scholar**, **Crossref**, **DBLP**, **OpenAlex**, opcionalmente ACL Anthology) com limites de taxa e retries.
8. **Pontuação** — `scorer` combina diferenças de título, autores, ordem, ano e consenso entre APIs → **hallucination_score** ∈ [0, 1].
9. **Saída** — `report.json`, `.bib` por PDF, opcionalmente `report_annotated.bib`, relatórios de risco (`--risk-reports`), e relatório no terminal (`--format terminal` ou `all`).

Tempos típicos: extração **< 1 s** por PDF; verificação **vários minutos** por dezenas de referências (limites das APIs sem chaves).

---

## Requisitos

- **Python 3.11+**
- Rede para o comando **`check`** / **`check-bib`** (as APIs são remotas).

---

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Opcional: copiar `config.example.toml` para `config.toml` e preencher chaves / email.

---

## Onde colocar os PDFs

- Coloque os seus PDFs numa pasta à escolha, por exemplo **`pdf-inputs/`** na raiz do repositório (convenção usada nos testes locais).
- O comando **`check`** aceita ficheiros ou **diretório**; todos os `*.pdf` desse diretório são processados em lote (com deduplicação de referências iguais entre artigos).
- **Não** é obrigatório usar `pdf-inputs/` — qualquer caminho serve, por exemplo `./meus_artigos/`.

> Os PDFs de teste não são versionados no Git por omissão; crie `pdf-inputs/` localmente ou ajuste o caminho.

---

## Comandos principais

Na raiz do projeto, com `PYTHONPATH` resolvido pelo `pip install -e .`:

```bash
# Só extrair referências para .bib (sem rede)
python -m halref.cli extract pdf-inputs/ -d ./saida_bib

# Verificar alucinações + JSON + .bib anotado + terminal
python -m halref.cli check pdf-inputs/ -d ./halref_output --format all

# Mesmo fluxo + tabelas de risco (resumo + um .md por artigo)
python -m halref.cli check pdf-inputs/ -d ./halref_output --risk-reports --format all

# Só JSON e relatórios de risco (menos ruído no terminal)
python -m halref.cli check pdf-inputs/ -d ./halref_output --risk-reports --format json

# Ver todas as referências no terminal, não só as acima do limiar
python -m halref.cli check paper.pdf -d ./out --show-ok

# Já tem .bib? Verificar sem extrair PDF
python -m halref.cli check-bib refs/ -d ./out --risk-reports
```

**Diagnóstico rápido** (por extracter, sem verificação completa de APIs):

```bash
PYTHONPATH=src python3 diagnose_extraction.py
```

(Espera a pasta `pdf-inputs/` com PDFs.)

---

## Saída (`--outdir` / `-d`)

| Ficheiro / pasta | Descrição |
|------------------|-----------|
| `bib/<stem>.bib` | BibTeX extraído por PDF |
| `report.json` | Resultados completos (serializado `BatchReport`) |
| `report_annotated.bib` | BibTeX com comentários de score (se `--format` incluir `bib` ou `all`) |
| `risk_summary.md` / `risk_summary.csv` | Se `--risk-reports`: percentagens por nível de risco por **ID de artigo** (prefixo numérico do nome do ficheiro) |
| `reports/detail_<ID>.md` | Se `--risk-reports`: uma tabela por referência + texto explicativo |

---

## Configuração e APIs

Variáveis de ambiente úteis (ou equivalentes em `config.toml`):

| Variável | Efeito |
|----------|--------|
| `SEMANTIC_SCHOLAR_API_KEY` | Mais taxa estável na Semantic Scholar |
| `OPENALEX_API_KEY` | Recomendado (OpenAlex desde fev. 2026) |
| `CROSSREF_MAILTO` | Email na pool “polite” do Crossref |

Ver **`config.example.toml`** para todas as opções (`text_extractors`, `field_parsers`, pesos `[matching.weights]`, etc.).

---

## Estilos SBC e BRACIS

| Estilo | Uso típico | Deteção / parser |
|--------|------------|------------------|
| **SBC** | Autor–ano, `In:` / `In `, venues PT | `SBCFieldParser` (natbib alargado) |
| **BRACIS** | `[N] Autor, I.: … In: … (AAAA): …` | `BRACISFieldParser` + split por `[N]` |

A pasta **`new-styles/`** documenta os formatos e inclui `.bst` de referência; o código **não** lê esses ficheiros em runtime — apenas a lógica em `src/halref/extract/field_parsers/`.

---

## Testes

```bash
pip install -e ".[dev]"   # se existir extra; senão: pip install pytest
python -m pytest tests/ -v --ignore=tests/fixtures
```

Alguns testes esperam PDFs gerados em `tests/fixtures/`:

```bash
python tests/fixtures/generate_test_pdf.py   # requer pdflatex
```

---

## Estrutura do repositório (essencial)

```
src/halref/           # Pacote principal
  cli.py              # Interface de linha de comandos
  pipeline.py         # Orquestração extração + verificação em lote
  extract/            # PDF → texto → segmentação → parsers
  matching/           # Score de alucinação
  apis/               # Clientes HTTP assíncronos
  output/             # JSON, BibTeX anotado, relatórios de risco
new-styles/           # Documentação dos estilos SBC / BRACIS (LNCS)
pdf-inputs/           # PDFs de entrada (convénio local; *.pdf no .gitignore)
tests/                # Testes automatizados
config.example.toml
diagnose_extraction.py  # Diagnóstico opcional de extração
```

---

## Privacidade

- **Extração**: o PDF processa-se **localmente**; o conteúdo integral do PDF **não** é enviado às APIs.
- **Verificação**: apenas **metadados** extraídos (título, autores, ano, …) são enviados aos serviços configurados.

---

## Licença

**MIT**, em linha com o projeto original:  
https://github.com/davidjurgens/hallucinated-reference-finder
