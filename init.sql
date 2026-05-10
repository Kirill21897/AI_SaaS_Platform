DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'ai_user') THEN
      CREATE ROLE ai_user LOGIN PASSWORD 'ai_password';
   END IF;
END
$do$;

ALTER DATABASE ai_saas_db OWNER TO ai_user;
GRANT ALL PRIVILEGES ON DATABASE ai_saas_db TO ai_user;
