-- =============================================================================
-- ADVERTENCIA: Este script destruye TODOS los datos de la base de datos.
-- Usar SOLO en entornos de desarrollo/testing.
-- NUNCA ejecutar en producción.
--
-- Después de ejecutar este script, correr:
--   alembic upgrade head        (para re-aplicar migraciones)
--   python scripts/seed.py      (para cargar datos semilla)
-- =============================================================================

-- Asegurarse de estar en la DB correcta
\c ainative

-- ─── Schema: operational ──────────────────────────────────────────────────
-- Tablas del dominio operativo: usuarios, comisiones, ejercicios, entregas

TRUNCATE TABLE
    operational.submissions,
    operational.exercises,
    operational.class_sessions,
    operational.enrollments,
    operational.commissions,
    operational.users
CASCADE;

-- Resetear secuencias del schema operational
DO $$
DECLARE
    seq RECORD;
BEGIN
    FOR seq IN
        SELECT sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = 'operational'
    LOOP
        EXECUTE format('ALTER SEQUENCE operational.%I RESTART WITH 1', seq.sequence_name);
    END LOOP;
END $$;

-- ─── Schema: cognitive ────────────────────────────────────────────────────
-- Tablas del tutor IA: sesiones de chat, mensajes, contexto del tutor

TRUNCATE TABLE
    cognitive.tutor_messages,
    cognitive.tutor_sessions,
    cognitive.student_profiles,
    cognitive.learning_traces
CASCADE;

DO $$
DECLARE
    seq RECORD;
BEGIN
    FOR seq IN
        SELECT sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = 'cognitive'
    LOOP
        EXECUTE format('ALTER SEQUENCE cognitive.%I RESTART WITH 1', seq.sequence_name);
    END LOOP;
END $$;

-- ─── Schema: governance ───────────────────────────────────────────────────
-- Tablas de auditoría: logs de acciones, trazas de seguridad, integridad CTR

TRUNCATE TABLE
    governance.audit_logs,
    governance.integrity_checks,
    governance.sandbox_events,
    governance.jwt_blacklist
CASCADE;

DO $$
DECLARE
    seq RECORD;
BEGIN
    FOR seq IN
        SELECT sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = 'governance'
    LOOP
        EXECUTE format('ALTER SEQUENCE governance.%I RESTART WITH 1', seq.sequence_name);
    END LOOP;
END $$;

-- ─── Schema: analytics ────────────────────────────────────────────────────
-- Tablas de métricas: estadísticas de uso, performance de ejercicios, reportes

TRUNCATE TABLE
    analytics.exercise_metrics,
    analytics.session_metrics,
    analytics.tutor_interaction_metrics,
    analytics.daily_snapshots
CASCADE;

DO $$
DECLARE
    seq RECORD;
BEGIN
    FOR seq IN
        SELECT sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = 'analytics'
    LOOP
        EXECUTE format('ALTER SEQUENCE analytics.%I RESTART WITH 1', seq.sequence_name);
    END LOOP;
END $$;

-- =============================================================================
-- Reset completado. Próximos pasos:
--   1. alembic upgrade head
--   2. python scripts/seed.py
-- =============================================================================
SELECT 'Reset completado exitosamente.' AS resultado;
