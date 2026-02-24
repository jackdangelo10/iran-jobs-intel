import postgres from "postgres";

let _sql: ReturnType<typeof postgres> | null = null;

export function getDb() {
  if (_sql) return _sql;
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL environment variable is not set");
  }
  _sql = postgres(connectionString, {
    max: 10,
    idle_timeout: 20,
    connect_timeout: 10,
    ssl: "require",
  });
  return _sql;
}
