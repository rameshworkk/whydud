DO $$
BEGIN
IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replicator') THEN
  CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'qBAQncFuLVNVedlMmiBDXJO8-VmXoCFV';
  RAISE NOTICE 'Created replication user: replicator';
END IF;
END
$$;
