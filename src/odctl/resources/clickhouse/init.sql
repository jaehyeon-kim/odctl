CREATE DATABASE IF NOT EXISTS feature_store;
CREATE DATABASE IF NOT EXISTS odctl;
-- Langfuse's ClickHouse migrations connect to this database and do not create it.
CREATE DATABASE IF NOT EXISTS langfuse;
