# Resumen Consolidado — 07-anexos

> 3 archivos. Última actualización: 2026-04-13

---

## 01_referencia_skills.md
- Referencia de skills disponibles para Claude Code en este proyecto
- Triggers, cuándo usar cada uno

## 02_estructura_de_codigo.md
- Árbol completo de archivos backend y frontend con descripciones
- Descripción de cada archivo clave (main.py, config.py, hash_chain, session, etc.)

### FIXES APLICADOS
- hash_chain.py movido de `app/core/` a `app/features/cognitive/` en el árbol
- Descripción actualizada: HashChainService (clase) en vez de funciones sueltas
- Columna `hash` → `event_hash`
- Agregado event_bus.py en core/

## 03_glosario.md
- Definiciones de términos del dominio: CTR, N4, Qe, hash chain, etc.
- Referencias a código para cada concepto

### FIXES APLICADOS
- hash_chain path corregido a `app/features/cognitive/hash_chain.py`
- Columna `hash` → `event_hash`
- `ctr_service.py` → `CognitiveService`

---

## INCONSISTENCIAS ENCONTRADAS Y RESUELTAS: 3
