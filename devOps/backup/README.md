# Backup y Restauración — Plataforma AI-Native

Documentación de la estrategia de backup para la base de datos PostgreSQL.

---

## Estrategia de backup

| Parámetro | Valor |
|---|---|
| Tipo | `pg_dump` en formato custom (binario, comprimido) |
| Frecuencia | Diario automático (ver cron) |
| Retención | 7 días de backups diarios |
| Compresión | gzip nivel 9 (post-dump) |
| Destino | `devOps/backup/backups/` (local) |
| Naming | `ainative_YYYYMMDD_HHMMSS.dump.gz` |

> Para entornos de producción reales, los backups deben copiarse a almacenamiento externo (S3, Google Cloud Storage, etc.) además del almacenamiento local.

---

## Backup manual

```bash
# Desde la raíz del proyecto
./devOps/backup/backup.sh

# O con variables de entorno personalizadas
POSTGRES_HOST=localhost \
POSTGRES_PORT=5432 \
POSTGRES_USER=ainative \
POSTGRES_PASSWORD=ainative \
POSTGRES_DB=ainative \
./devOps/backup/backup.sh
```

El backup se guarda en `devOps/backup/backups/` con el timestamp en el nombre.

---

## Restaurar desde backup

```bash
# Restaurar el backup más reciente
./devOps/backup/restore.sh devOps/backup/backups/ainative_20260410_120000.dump.gz

# El script pide confirmación antes de proceder
# Escribir 'SI' (en mayúsculas) para confirmar
```

El script de restauración:
1. Valida que el archivo de backup existe
2. Solicita confirmación explícita
3. Descomprime el archivo (si es `.gz`)
4. Termina conexiones activas a la DB
5. Ejecuta `pg_restore --clean` (reemplaza los datos existentes)
6. Ejecuta `alembic upgrade head` para asegurar consistencia del schema

---

## Verificar integridad de un backup

```bash
# Verificar que el archivo no está corrupto
gunzip -t devOps/backup/backups/ainative_20260410_120000.dump.gz
echo "Archivo OK (exit code: $?)"

# Listar el contenido del backup sin restaurar
PGPASSWORD=ainative pg_restore \
    --list \
    <(gunzip -c devOps/backup/backups/ainative_20260410_120000.dump.gz)

# Restaurar en una DB de prueba para verificar
createdb ainative_verify
PGPASSWORD=ainative pg_restore \
    --host=localhost \
    --username=ainative \
    --dbname=ainative_verify \
    --no-owner \
    <(gunzip -c devOps/backup/backups/ainative_20260410_120000.dump.gz)
psql -U ainative -d ainative_verify -c "\dt operational.*"
dropdb ainative_verify
```

---

## Automatización con cron

Agregar al crontab del servidor para ejecutar el backup diariamente a las 2:00 AM:

```bash
# Editar crontab
crontab -e

# Agregar esta línea (ajustar la ruta al proyecto):
0 2 * * * /home/juani/ProyectosFacultad/AI-Native/devOps/backup/backup.sh >> /var/log/ainative-backup.log 2>&1
```

Para verificar que el cron está configurado:

```bash
crontab -l | grep ainative
```

Para ver el log de backups automáticos:

```bash
tail -50 /var/log/ainative-backup.log
```

---

## Notas importantes

- Los backups locales NO protegen contra falla del disco. En producción, configurar copia a S3 o similar.
- El script elimina automáticamente backups con más de 7 días para no llenar el disco.
- La restauración interrumpe el servicio brevemente mientras se terminan las conexiones activas.
- Siempre verificar la integridad del backup antes de una restauración en producción.
