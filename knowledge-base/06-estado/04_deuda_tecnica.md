# Deuda Técnica

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

## Estado Actual

**El proyecto está en etapa de inicio (greenfield).** No hay deuda técnica inicial documentada. Este documento se puebla a medida que:

1. Se toman decisiones de implementación sabiendo que hay una solución mejor que no se implementa por restricciones de tiempo.
2. Se descubren problemas en code reviews que no bloquean el merge pero deberían corregirse después.
3. Se identifica código que funciona pero no sigue las convenciones del proyecto.
4. Se omiten tests por presión de tiempo.

---

## Categorías de Deuda Técnica

### Arquitectura
Decisiones estructurales que limitan la escalabilidad o mantenibilidad. Ejemplos: módulos con responsabilidades mezcladas, acoplamiento fuerte entre capas, abstracciones incorrectas.

### Testing
Cobertura insuficiente, tests que testean implementación en lugar de comportamiento, fixtures duplicadas, tests frágiles.

### Seguridad
Vulnerabilidades conocidas pero no críticas, validaciones insuficientes, permisos muy amplios temporalmente.

### Performance
Queries sin índices, N+1 queries conocidas, cálculos síncronos que deberían ser async, cachés faltantes.

### Documentación
Código no documentado, convenciones no seguidas, ADRs faltantes.

### Dependencias
Versiones de paquetes desactualizadas, dependencias con vulnerabilidades conocidas, dependencias innecesarias.

---

## Niveles de Severidad

| Nivel | Descripción | Tiempo máximo sin resolver |
|---|---|---|
| **Crítico** | Bloquea funcionalidad importante o es una vulnerabilidad de seguridad activa | 1 semana |
| **Alto** | Impacta significativamente la calidad o mantenibilidad. Dificulta el trabajo del equipo | 1 sprint (2 semanas) |
| **Medio** | Subóptimo pero manejable. Aumenta el riesgo gradualmente si no se resuelve | 1 mes |
| **Bajo** | Mejora cosmética o de conveniencia. Puede esperar hasta que haya tiempo libre | Backlog |

---

## Registro de Deuda Técnica

*Este registro se puebla durante el desarrollo. Al inicio del proyecto está vacío.*

### Items Críticos

*Ninguno — proyecto no iniciado.*

---

### Items Altos

*Ninguno — proyecto no iniciado.*

---

### Items Medios

*Ninguno — proyecto no iniciado.*

---

### Items Bajos

*Ninguno — proyecto no iniciado.*

---

## Plantilla para Agregar un Nuevo Item

Copiar el siguiente bloque al agregar un item de deuda técnica:

```markdown
### TD-XXX: [Título descriptivo]

**Categoría**: Arquitectura | Testing | Seguridad | Performance | Documentación | Dependencias
**Severidad**: Crítico | Alto | Medio | Bajo
**Fecha descubierto**: YYYY-MM-DD
**Descubierto por**: @username
**Fase relacionada**: Fase 0 | Fase 1 | Fase 2 | Fase 3 | Fase 4 | General

**Descripción**:
Qué está mal y por qué es un problema.

**Impacto actual**:
Qué pasa si no se resuelve. Cuán rápido empeora.

**Solución propuesta**:
Cómo se debería resolver. Estimación de esfuerzo.

**Razón por la que no se resolvió ahora**:
Presión de tiempo / complejidad / dependencia externa / etc.

**Issue de GitHub**: #NNN (crear la issue y linkearla aquí)

**Estado**: Abierto | En progreso | Resuelto
**Fecha de resolución**: — (rellenar cuando se cierre)
```

---

## Ejemplo de Item Completado

Para ilustrar cómo se usa el formato:

*(Este es un ejemplo hipotético para ilustrar el formato)*

```markdown
### TD-001: Hash chain verification job no tiene retry logic

**Categoría**: Arquitectura
**Severidad**: Medio
**Fecha descubierto**: 2026-04-01
**Descubierto por**: @dev3
**Fase relacionada**: Fase 3

**Descripción**:
El job programado que verifica la integridad del hash chain no tiene lógica de
reintentos si falla. Si falla por un problema transitorio (DB temporalmente no
disponible), el job simplemente no corre y no se genera alerta.

**Impacto actual**:
Bajo mientras el sistema es pequeño. Si el job falla silenciosamente, una ruptura
del hash chain puede no detectarse hasta la próxima ejecución del job.

**Solución propuesta**:
Agregar retry con backoff exponencial usando Celery o un simple loop de reintentos.
Estimación: 2-4 horas.

**Razón por la que no se resolvió ahora**:
La semana de integración tenía prioridades más altas. Se pospuso a post-integración.

**Issue de GitHub**: #87

**Estado**: Abierto
**Fecha de resolución**: —
```

---

## Proceso para Gestionar la Deuda Técnica

1. **Descubrir**: cualquier desarrollador puede agregar un item a este documento + crear la issue en GitHub.

2. **Categorizar y priorizar**: el tech lead revisa los items nuevos semanalmente y asigna severidad.

3. **Asignar**: los items críticos y altos se agregan al sprint siguiente. Medios y bajos van al backlog.

4. **Resolver**: el desarrollador resuelve el item, actualiza el estado en este documento y cierra la issue.

5. **Revisar**: en la retrospectiva de cada sprint, revisar si la deuda acumulada está creciendo o decreciendo.

---

## Métricas de Deuda Técnica

*Actualizar mensualmente.*

| Fecha | Críticos | Altos | Medios | Bajos | Total | Resueltos (mes) |
|---|---|---|---|---|---|---|
| 2026-04-10 | 0 | 0 | 0 | 0 | 0 | — |

---

## Política de Deuda Técnica

### Cuándo está permitido crear deuda intencionalmente

La deuda técnica no es siempre mala. Está justificada cuando:
- Hay una deadline real que no puede moverse (piloto, demo para la tesis).
- La solución correcta requiere refactoring de múltiples módulos y bloquearía a otros devs.
- Es un prototipo exploratorio que puede descartarse.

En todos estos casos, **documentar en este registro antes de mergearlo**.

### Cuándo no está permitido crear deuda

- No se documenta aquí (deuda oculta es lo peor).
- El item es de severidad crítica o seguridad.
- Hay tiempo disponible para hacerlo bien.
- Afecta al hash chain o la integridad de los CTRs (esas áreas son zero-debt).
