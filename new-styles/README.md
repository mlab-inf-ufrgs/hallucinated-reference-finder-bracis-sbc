# Estilos de bibliografia (referência)

Documentação e ficheiros **`.bst`** de referência para os formatos usados nas submissões:

- **SBC** — `SBC_STYLE.md`, `sbc.bst`
- **BRACIS** (formato numerado tipo LNCS/Springer) — `SPLNCS_STYLE.md`, `splncs04.bst`

O código em **`src/halref/extract/field_parsers/`** implementa a lógica (`SBCFieldParser`, `BRACISFieldParser`, deteção automática). Estes ficheiros **não** são carregados em runtime; servem para alinhar autores/editores com o comportamento esperado.

Instruções completas de instalação, pipeline e CLI: **`../README.md`** (raiz do repositório).
