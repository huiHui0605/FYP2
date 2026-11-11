PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('resident','fixer','admin')),
 area TEXT NOT NULL DEFAULT 'Petaling Jaya', skills TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
 created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE IF NOT EXISTS tickets (
 id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id), fixer_id INTEGER REFERENCES users(id),
 title TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, area TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','assigned','in_progress','repaired','unrepairable','cancelled')),
 priority TEXT NOT NULL DEFAULT 'normal', safety TEXT NOT NULL, weight REAL NOT NULL CHECK(weight>0 AND weight<=500),
 public_code TEXT NOT NULL UNIQUE, created TEXT NOT NULL, updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES tickets(id), user_id INTEGER NOT NULL REFERENCES users(id),
 body TEXT NOT NULL, created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
 id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES tickets(id), user_id INTEGER NOT NULL REFERENCES users(id),
 status TEXT NOT NULL, note TEXT NOT NULL, created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tools (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, area TEXT NOT NULL,
 total INTEGER NOT NULL CHECK(total>=1 AND total<=100), active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS loans (
 id INTEGER PRIMARY KEY, tool_id INTEGER NOT NULL REFERENCES tools(id), user_id INTEGER NOT NULL REFERENCES users(id),
 start TEXT NOT NULL, end TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'reserved' CHECK(status IN ('reserved','collected','returned','cancelled')),
 created TEXT NOT NULL, CHECK(end>=start)
);
CREATE TABLE IF NOT EXISTS clinics (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, location TEXT NOT NULL,
 starts TEXT NOT NULL, capacity INTEGER NOT NULL CHECK(capacity>=1 AND capacity<=500), host_id INTEGER NOT NULL REFERENCES users(id),
 cancelled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS signups (
 clinic_id INTEGER NOT NULL REFERENCES clinics(id), user_id INTEGER NOT NULL REFERENCES users(id),
 PRIMARY KEY(clinic_id,user_id)
);
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), body TEXT NOT NULL, link TEXT NOT NULL,
 seen INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, actor_id INTEGER REFERENCES users(id), action TEXT NOT NULL, detail TEXT NOT NULL, created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_attempts (ip TEXT NOT NULL, happened INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS tickets_owner ON tickets(owner_id);
CREATE INDEX IF NOT EXISTS loans_dates ON loans(tool_id,start,end,status);
CREATE INDEX IF NOT EXISTS notifications_user ON notifications(user_id,seen);
CREATE INDEX IF NOT EXISTS login_attempt_time ON login_attempts(happened);
