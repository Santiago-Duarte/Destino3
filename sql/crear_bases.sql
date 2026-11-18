-- Crea roles y bases de los tres entornos y aplica schema.sql en cada una.
-- Uso: set -a; source .env; set +a
--      psql -h "$DB_HOST" -p "$DB_PORT" -d postgres -f sql/crear_bases.sql

\set ON_ERROR_STOP on

\getenv production_password DB_PRODUCTION_PASSWORD
\getenv demo_password DB_DEMO_PASSWORD
\getenv testing_password DB_TEST_PASSWORD

SELECT format('CREATE ROLE %I LOGIN', 'destino3_production')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'destino3_production')\gexec
ALTER ROLE destino3_production WITH LOGIN PASSWORD :'production_password';

SELECT format('CREATE ROLE %I LOGIN', 'destino3_demo')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'destino3_demo')\gexec
ALTER ROLE destino3_demo WITH LOGIN PASSWORD :'demo_password';

SELECT format('CREATE ROLE %I LOGIN', 'destino3_testing')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'destino3_testing')\gexec
ALTER ROLE destino3_testing WITH LOGIN PASSWORD :'testing_password';

SELECT format('CREATE DATABASE %I OWNER %I', 'destino3_db', 'destino3_production')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'destino3_db')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', 'demo_db', 'destino3_demo')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'demo_db')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', 'destino3_test_db', 'destino3_testing')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'destino3_test_db')\gexec

\connect destino3_db destino3_production
\ir schema.sql

\connect demo_db destino3_demo
\ir schema.sql

\connect destino3_test_db destino3_testing
\ir schema.sql
