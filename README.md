# halref — Hallucinated Reference Finder (adaptação para BRACIS e anais da SBC)

Fork do projeto [**hallucinated-reference-finder**](https://github.com/davidjurgens/hallucinated-reference-finder) (David Jurgens) focado em **PDFs de artigos** com bibliografia no estilo **SBC** (Sociedade Brasileira de Computação) e **BRACIS** (formato numerado tipo LNCS/Springer, usado nas submissões da conferência BRACIS).

O objetivo é **extrair referências** do PDF (local), **consultar bases académicas** (metadados apenas), **atribuir um score de risco** de alucinação ou inconsistência face ao que existe nas APIs e **gerar saídas** (JSON, BibTeX, relatórios) para o **revisor** priorizar verificação manual das entradas com maior score.

----

### Aviso legal e limitação de uso

**Disclaimer:** os autores e mantenedores deste fork **não assumem qualquer responsabilidade** pelo uso da ferramenta, pelas suas saídas nem por decisões tomadas com base nos relatórios ou scores. Os resultados dependem de extração de PDF, heurísticas, limitações das APIs públicas e de dados bibliográficos que podem estar incompletos ou desatualizados.

Esta ferramenta **não** deve ser utilizada, por si só, para **aceitar ou rejeitar** submissões científicas, nem como prova ou acusação de que um artigo contém «referências alucinadas» ou conduta inadequada. Os scores são **indicadores heurísticos** sujeitos a falsos positivos e falsos negativos.

Utilize o **halref** apenas como **apoio à revisão e à filtragem manual**: priorizar entradas a verificar, cruzar com fontes primárias. Confirme sempre os resultados com verificação manual e análise crítica humana, bem como as políticas da sua conferência, instituição ou revisão por pares.

---
## Alterações deste fork (changelog)

### Extração e estilos

- **Secção de referências**: cabeçalhos em **português** (`Referências`, `Bibliografia`, …) e variante **`Referˆencias`** (encoding comum em PDFs); fim de secção com termos PT (**Apêndice**, **Agradecimentos**, …).
- **Divisão em referências individuais**: estratégias para **`[N]`**, **`N. Autor:`** (BRACIS/LNCS/Springer), anos **`(AAAA)`**, linhas numeradas, etc.; escolha do melhor extractor por **qualidade** do lote (inclui comparação com **pypdf** mesmo quando não está na lista, para mitigar intercalação de colunas).
- **BRACIS — artigos de revista / capítulos sem `In:`**: parsing de linhas no formato `Autores. Título. Revista, vol:páginas, ano.` (e variantes com vários segmentos, p.ex. conferência + `IJCNN, 2025`); **não** partir iniciais `B. C.` como fim de frase; ano final com `, YYYY` ou ` … YYYY.`; evitar `split(':')` no primeiro `:` de `volume:páginas`.
- **Título sem colar a revista**: após o parsing, `truncate_title_at_journal_boundary` corta o sufixo quando o segmento seguinte a um `. ` parece cabeçalho de venue (`Journal of …`, `Advances in neural …`, `IEEE …`, volume `(AAAA)`, etc.), sem partir iniciais `X.` em nomes. No *merge* de candidatos do ensemble, entre confianças semelhantes passa a preferir-se o **título mais curto** (evita escolher «título + revista» em vez do título só).
- **Parsing SBC (natbib)**: títulos sem artefacto **`).`** após `(ano)`; listas de autores `Sobrenome, X., …`; **ano de publicação** com heurística para não confundir com ano dentro de **DOI** (`year_context`); ordem de parsers no ensemble favorece **BRACIS** quando o estilo é desconhecido (evita SBC “ganhar” indevidamente).
- **Estilos**: deteção automática **SBC** vs **BRACIS**; parsers dedicados (`SBCFieldParser`, `BRACISFieldParser`). A pasta `new-styles/` contém **documentação** e `.bst` de referência (não lidos em runtime).
- **Extractores**: `config.fast-apis.toml` exemplifica **pdfminer** como padrão estável para blocos de referências; **Marker** / **Docling** opcionais com `prefer_gpu` em `[extraction]` (quando PyTorch/GPU existir).
- **Filtro pós-parse**: por defeito **não** se removem referências só por heurística de “fragmento” (`drop_fragment_refs_after_parse = false`), para **todas** as entradas segmentadas serem enviadas à verificação (adequado a auditoria de alucinações). Quem quiser o comportamento antigo pode pôr `drop_fragment_refs_after_parse = true` no TOML.

### Verificação, BibTeX e relatórios

- **Score de alucinação (título + consenso)**: a similaridade de título usada no `scorer` é **conservadora** (`min` de ratio / token_sort / token_set), para não tratar dois artigos só porque partilham expressões genéricas (ex.: «digital transformation») como quase iguais. O sinal de **consenso entre APIs** conta apenas fontes que, além de um título estrito vs. o PDF, apontam para o **mesmo trabalho** que o melhor match (DOI igual ou título muito parecido entre hits), evitando que vários falsos positivos anulem a penalização.
- **Autores (primeiro autor mais rigoroso)**: sobrenomes no overlap usam fuzzy **0,90** (antes 0,85 implícito); o **primeiro autor** exige fuzzy **0,93** no apelido e, quando há string completa/iniciais usável, **min**(token_sort, ratio) ≥ **0,72** entre as duas formas. Se o primeiro autor **não** coincide com o melhor match, o mismatch de autores tem **piso 0,52** (evita que overlap noutros nomes disfarce referência inventada).
- **Verificação**: mantém-se o fluxo por APIs (**Semantic Scholar**, **Crossref**, **DBLP**, **OpenAlex**, ACL Anthology opcional); reparação opcional de truncados (`repair`) com checagem ao texto do PDF.
- **`.bib` após `check`**: após as APIs, os ficheiros `bib/<stem>.bib` são **reescritos**; quando o match é **confiável**, os campos BibTeX passam a refletir **metadados canónicos** do melhor resultado da API (fusão conservadora — **sem LLM obrigatório**). O primeiro `.bib` (logo após extração) ainda reflete só o parse do PDF.
- **`report_annotated.bib`**: com `--format all` ou `bib`, inclui comentários de score e indica quando o corpo BibTeX veio do match verificado.
- **`--risk-reports`**: `risk_summary.md` / `.csv` e `reports/detail_<id>.md` por artigo (componentes do score).
- **`timing_report.md`**: tempos de extração por PDF, verificação e totais após `halref check`.

### CLI

- Comandos: **`halref check`**, **`halref extract`**, **`halref check-bib`** — ver `python -m halref.cli --help`.
- Opções úteis: `--config`/`-c` (TOML), `--risk-reports`, `--format` (`terminal` | `json` | `bib` | `all`), `--threshold`, `--show-ok`. LLM (`--llm`, `--llm-extract`, `--llm-batch`) permanecem **opcionais** (`pip install -e ".[llm]"` + servidor OpenAI-compatível).

---

## Tutorial: executar o fluxo completo

### 1. Pré-requisitos

- **Python 3.11+**
- **Rede** para `check` e `check-bib` (as APIs são remotas).
- Recomendado: chave **OpenAlex** e email **Crossref** (`mailto`) — ver secção [Configuração e APIs](#configuração-e-apis).

### 2. Instalação

Na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .
```

Opcional (só se for usar LLM na extração/verificação):

```bash
pip install -e ".[llm]"
```

Copie `config.example.toml` para `config.toml` (ou use `-c` apontando para um ficheiro, p.ex. `config.fast-apis.toml`).

### 3. Colocar os PDFs

Crie uma pasta com os PDFs, por exemplo **`pdf-inputs/`** na raiz (convénio local; os PDFs podem estar no `.gitignore`).

### 4. Verificação completa com relatórios (recomendado)

Processa **todos** os `*.pdf` da pasta, grava resultados em `halref_experiment_out/` e sobrescreve saídas anteriores com o mesmo `-d`:

```bash
source .venv/bin/activate
python -m halref.cli check pdf-inputs/ \
  -d halref_experiment_out \
  -c config.fast-apis.toml \
  --risk-reports \
  --format all
```

**O que obtém:**

| Saída | Descrição |
|--------|-----------|
| `bib/<nome>.bib` | BibTeX por PDF (segunda escrita com campos canónicos da API quando o score o permite) |
| `report.json` | Resultados completos (`BatchReport`) |
| `report_annotated.bib` | BibTeX global com scores e notas |
| `risk_summary.md` / `risk_summary.csv` | Resumo de risco por ficheiro |
| `reports/detail_<id>.md` | Detalhe por referência (título, sinais, match) |
| `timing_report.md` | Tempos de execução |

**Interpretação para revisão:** priorizar referências com **hallucination_score** alto (por defeito ≥ **0.5** no resumo de risco); o programa é uma **indicação** — a decisão final é manual.

### 5. Variantes úteis

```bash
# Só JSON + relatórios de risco (menos saída no terminal)
python -m halref.cli check pdf-inputs/ -d ./out --risk-reports --format json -c config.fast-apis.toml

# Listar também referências com baixo risco no terminal
python -m halref.cli check pdf-inputs/ -d ./out --show-ok --format all

# Só extrair .bib do PDF, sem rede
python -m halref.cli extract pdf-inputs/ -d ./saida_bib -c config.fast-apis.toml

# Já tem .bib? Verificar sem PDF
python -m halref.cli check-bib pasta_com_bib/ -d ./out --risk-reports --format all
```

### 6. Diagnóstico só de extração (sem APIs)

Útil para validar segmentação/parsing sem esperar pela rede:

```bash
PYTHONPATH=src python diagnose_extraction.py
```

(Espera `pdf-inputs/` com PDFs; ajuste caminhos dentro do script se necessário.)

---

## Pipeline (fim a fim)

1. **Entrada** — Um ou mais `.pdf` (ou pasta), ou `.bib` com `check-bib`.
2. **Texto** — Extractores (`pdfminer`, …) leem o PDF; localiza-se o bloco **Referências / Bibliografia**.
3. **Segmentação** — Uma string por referência (marcadores, autor–ano, etc.).
4. **Estilo** — Heurística **SBC** vs **BRACIS**.
5. **Parsing** — Parsers de estilo + `regex` / `heuristic` (e opcionalmente LLM / API Crossref na extração).
6. **Filtro mínimo** — Por defeito só se filtram entradas com **confiança de parse** muito baixa; fragmentos “óbvios” só são removidos se `drop_fragment_refs_after_parse = true`.
7. **Verificação** — Consultas assíncronas às APIs; retries; reparação opcional de truncados.
8. **Pontuação** — Combinação de título, autores, ordem, ano, consenso, DOI → **hallucination_score** ∈ [0, 1] sobre o **`Reference`** em memória (não sobre o ficheiro `.bib` bruto).
9. **Saída** — JSON, `.bib` por PDF, opcionalmente BibTeX anotado, relatórios de risco, terminal, `timing_report.md`.

Tempos típicos: extração **≪ 1 s** por PDF; verificação **minutos** para dezenas/centenas de referências, conforme limites das APIs.

---

## Requisitos

- **Python 3.11+**
- **Rede** para `check` / `check-bib`.

---

## Instalação (resumo)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Opcional: `pip install -e ".[dev]"` para testes com pytest.

---

## Onde colocar os PDFs

- Convenção: **`pdf-inputs/`** na raiz (criar localmente).
- `check` aceita ficheiros ou diretório; em lote há **deduplicação** de referências idênticas entre PDFs.
- Qualquer caminho serve, por exemplo `./meus_artigos/`.

---

## Configuração e APIs

Variáveis de ambiente (ou equivalentes em `config.toml`):

| Variável | Efeito |
|----------|--------|
| `SEMANTIC_SCHOLAR_API_KEY` | Taxa mais estável na Semantic Scholar |
| `OPENALEX_API_KEY` | Recomendado (OpenAlex desde fev. 2026) |
| `CROSSREF_MAILTO` | Email na pool “polite” do Crossref |

Ver **`config.example.toml`** e **`config.fast-apis.toml`** (`text_extractors`, `field_parsers`, `[matching.weights]`, `drop_fragment_refs_after_parse`, `prefer_gpu`, etc.).

---

## Estilos SBC e BRACIS

| Estilo | Uso típico | Deteção / parser |
|--------|------------|------------------|
| **SBC** | Autor–ano, `In:` / `In ` | `SBCFieldParser` (natbib alargado) |
| **BRACIS** | `[N] …`, `N. …`, `In: … (AAAA)`, revista `…, vol:páginas, ano.` | `BRACISFieldParser` + segmentação |

A pasta **`new-styles/`** documenta formatos e `.bst`; o código **não** lê esses ficheiros em runtime.

---

## Testes

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v --ignore=tests/fixtures
```

Alguns testes esperam PDFs em `tests/fixtures/`:

```bash
python tests/fixtures/generate_test_pdf.py   # requer pdflatex
```

---

## Estrutura do repositório (essencial)

```
src/halref/           # Pacote principal
  cli.py              # Interface de linha de comandos
  pipeline.py         # Orquestração extração + verificação em lote
  config.py           # Modelo de configuração (Pydantic)
  hardware.py         # Preferência GPU para extractores opcionais
  extract/            # PDF → texto → segmentação → parsers
  matching/           # Score de alucinação
  apis/               # Clientes HTTP assíncronos
  output/             # JSON, BibTeX anotado, relatórios de risco
new-styles/           # Documentação SBC / BRACIS (LNCS)
pdf-inputs/           # PDFs de entrada (local; convenção)
tests/                # Testes automatizados
config.example.toml
config.fast-apis.toml # Exemplo: pdfminer, Crossref+OpenAlex
diagnose_extraction.py  # Diagnóstico opcional só de extração
```

---

## Privacidade

- **Extração**: o PDF processa-se **localmente**; o PDF integral **não** é enviado às APIs.
- **Verificação**: apenas **metadados** extraídos (título, autores, ano, …) são enviados aos serviços configurados.

---

## Licença

**MIT**, em linha com o projeto original:  
https://github.com/davidjurgens/hallucinated-reference-finder

---

## Créditos
- **Implementação e adaptação**: Renan Andrades e Mateus Balda, do INF-UFRGS, foram responsáveis pela adaptação do código ao contexto dos proceedings do BRACIS e de eventos da SBC, e pelas implementações envolvidas no processo.
- **Supervisão**: Profa. Dra. Mariana Recamonde Mendoza (INF-UFRGS) supervisionou o trabalho, orientou quanto ao uso e às decisões metodológicas, esclareceu dúvidas e contribuiu na definição das soluções.
- **Agradecimento** à Profa. Dra. Viviane Moreira (INF-UFRGS), pela indicação da solução original que embasou este projeto. 
