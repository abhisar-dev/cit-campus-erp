const readline = require('readline');
const fs = require('fs');
const path = require('path');

// Resolve @neondatabase/serverless from local or sibling codeclash node_modules
let neonModule = null;
const possiblePaths = [
  path.join(__dirname, '..', 'node_modules', '@neondatabase', 'serverless'),
  'C:/Users/hp/.gemini/antigravity/scratch/codeclash/node_modules/@neondatabase/serverless'
];

for (const p of possiblePaths) {
  try {
    neonModule = require(p);
    if (neonModule) break;
  } catch {}
}

if (!neonModule) {
  try {
    neonModule = require('@neondatabase/serverless');
  } catch {}
}

const { Pool, neon } = neonModule || {};

// Read .env if present
try {
  const envPath = path.join(__dirname, '..', '.env');
  if (fs.existsSync(envPath)) {
    const lines = fs.readFileSync(envPath, 'utf8').split('\n');
    for (const line of lines) {
      const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
      if (match) {
        const key = match[1];
        let val = (match[2] || '').trim();
        if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
        if (!process.env[key]) process.env[key] = val;
      }
    }
  }
} catch {}

const DEFAULT_URL =
  'postgresql://neondb_owner:npg_sDPO09gHkrVM@ep-bitter-tree-b4va883u-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require';

let activeUrl = process.env.DATABASE_URL || process.env.NEON_DATABASE_URL || DEFAULT_URL;

const G = '\x1b[32m'; // Green
const C = '\x1b[36m'; // Cyan
const Y = '\x1b[33m'; // Yellow
const R = '\x1b[31m'; // Red
const B = '\x1b[1m';  // Bold
const D = '\x1b[2m';  // Dim
const RST = '\x1b[0m'; // Reset

let pool = null;
let httpSql = null;
let activeHost = 'neon.tech';
let activeDb = 'neondb';

function parseDbInfo(url) {
  try {
    const u = new URL(url);
    activeHost = u.hostname || activeHost;
    activeDb = u.pathname.replace(/^\//, '') || activeDb;
  } catch {}
}

async function connectToNeon(url) {
  parseDbInfo(url);
  if (!neonModule) {
    throw new Error('@neondatabase/serverless module could not be loaded.');
  }
  if (pool) {
    try { await pool.end(); } catch {}
  }

  // Primary: Neon Serverless WebSocket Pool (Port 443 WSS)
  try {
    pool = new Pool({ connectionString: url });
    const res = await pool.query('SELECT 1 as num, current_database() as db');
    httpSql = neon(url);
    return { method: 'WebSocket Pool (WSS :443)', db: res.rows[0]?.db || activeDb };
  } catch (errWs) {
    // Fallback: Neon Serverless HTTP Driver (Port 443 HTTPS)
    try {
      httpSql = neon(url);
      const resHttp = await httpSql.query('SELECT 1 as num, current_database() as db');
      pool = null;
      return { method: 'Serverless HTTP Driver (HTTPS :443)', db: resHttp[0]?.db || activeDb };
    } catch (errHttp) {
      throw new Error(`WSS & HTTPS connection failed: ${errWs.message}`);
    }
  }
}

async function executeSql(sql) {
  if (pool) {
    const res = await pool.query(sql);
    return res.rows;
  } else if (httpSql) {
    return await httpSql.query(sql);
  }
  throw new Error('No active database connection.');
}

async function initializeCitSchema() {
  console.log(`${D}Creating cit_system_store, cit_users, cit_bookings, cit_audit_logs...${RST}`);
  await executeSql(`
    CREATE TABLE IF NOT EXISTS cit_system_store (
      store_key VARCHAR(64) PRIMARY KEY,
      payload JSONB NOT NULL,
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
  `);
  await executeSql(`
    CREATE TABLE IF NOT EXISTS cit_users (
      id VARCHAR(32) PRIMARY KEY,
      email VARCHAR(255) UNIQUE NOT NULL,
      name VARCHAR(255),
      role VARCHAR(32) DEFAULT 'student',
      cohort VARCHAR(64),
      status VARCHAR(32) DEFAULT 'Active',
      password_hash VARCHAR(255),
      last_active VARCHAR(64),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
  `);
  await executeSql(`
    CREATE TABLE IF NOT EXISTS cit_bookings (
      id VARCHAR(64) PRIMARY KEY,
      room_id VARCHAR(64) NOT NULL,
      user_email VARCHAR(255) NOT NULL,
      user_name VARCHAR(255),
      purpose TEXT,
      event_name VARCHAR(255),
      date VARCHAR(32),
      periods VARCHAR(64),
      status VARCHAR(32) DEFAULT 'Under Review',
      reason TEXT,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
  `);
  await executeSql(`
    CREATE TABLE IF NOT EXISTS cit_audit_logs (
      id VARCHAR(64) PRIMARY KEY,
      action VARCHAR(128) NOT NULL,
      actor VARCHAR(255),
      details TEXT,
      ip VARCHAR(64),
      status VARCHAR(32) DEFAULT 'Logged',
      timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
  `);
  console.log(`${G}✓ Schema initialized successfully in Neon Cloud.${RST}`);
}

async function syncLocalStateToNeon() {
  const storePath = path.join(__dirname, '..', 'users_store.json');
  if (!fs.existsSync(storePath)) {
    console.log(`${R}Local users_store.json not found.${RST}`);
    return;
  }
  const store = JSON.parse(fs.readFileSync(storePath, 'utf8'));

  // Ensure tables exist
  await initializeCitSchema();

  console.log(`${D}Uploading full system payload to cit_system_store...${RST}`);
  const payloadStr = JSON.stringify(store).replace(/'/g, "''");
  await executeSql(`
    INSERT INTO cit_system_store (store_key, payload, updated_at)
    VALUES ('main_state', '${payloadStr}', CURRENT_TIMESTAMP)
    ON CONFLICT (store_key) DO UPDATE SET
      payload = EXCLUDED.payload,
      updated_at = CURRENT_TIMESTAMP;
  `);

  console.log(`${D}Syncing ${store.users?.length || 0} users to cit_users...${RST}`);
  for (const u of (store.users || [])) {
    const id = (u.id || '').replace(/'/g, "''");
    const email = (u.email || '').replace(/'/g, "''");
    const name = (u.name || '').replace(/'/g, "''");
    const role = (u.role || 'student').replace(/'/g, "''");
    const cohort = (u.cohort || '').replace(/'/g, "''");
    const status = (u.status || 'Active').replace(/'/g, "''");
    const hash = (u.password_hash || '').replace(/'/g, "''");
    const lastActive = (u.last_active || '').replace(/'/g, "''");
    await executeSql(`
      INSERT INTO cit_users (id, email, name, role, cohort, status, password_hash, last_active)
      VALUES ('${id}', '${email}', '${name}', '${role}', '${cohort}', '${status}', '${hash}', '${lastActive}')
      ON CONFLICT (email) DO UPDATE SET
        name = EXCLUDED.name,
        role = EXCLUDED.role,
        cohort = EXCLUDED.cohort,
        status = EXCLUDED.status,
        password_hash = EXCLUDED.password_hash,
        last_active = EXCLUDED.last_active;
    `);
  }

  // Sync audit logs
  if (Array.isArray(store.audit_logs)) {
    for (const log of store.audit_logs) {
      const lid = (log.id || ('LOG-' + Date.now())).replace(/'/g, "''");
      const act = (log.action || '').replace(/'/g, "''");
      const actor = (log.actor || 'System').replace(/'/g, "''");
      const det = (log.details || '').replace(/'/g, "''");
      const ip = (log.ip || '127.0.0.1').replace(/'/g, "''");
      await executeSql(`
        INSERT INTO cit_audit_logs (id, action, actor, details, ip, timestamp)
        VALUES ('${lid}', '${act}', '${actor}', '${det}', '${ip}', CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING;
      `);
    }
  }

  console.log(`${G}✓ Full sync completed! Local state is live in Neon Serverless Cloud.${RST}`);
}

async function startTerminal() {
  console.clear();
  parseDbInfo(activeUrl);

  console.log(`${G}${B}`);
  console.log('╔════════════════════════════════════════════════════════════════════════════════╗');
  console.log('║               CIT CAMPUS ERP · NEON DATABASE TERMINAL v1.0                     ║');
  console.log('║  Chilika Institute of Technology · TLS Port 443 (Firewall-Immune)              ║');
  console.log('╚════════════════════════════════════════════════════════════════════════════════╝');
  console.log(`${RST}`);
  console.log(`${D}Host: ${activeHost} | Database: ${activeDb}${RST}`);
  console.log(`${D}Connecting to Neon Cloud Database...${RST}`);

  let connInfo;
  try {
    const t0 = Date.now();
    connInfo = await connectToNeon(activeUrl);
    const ms = Date.now() - t0;
    console.log(`${G}✓ Connected successfully via ${connInfo.method} in ${ms}ms!${RST}\n`);
    // Ensure cit_* schema exists
    await initializeCitSchema();
  } catch (err) {
    console.error(`${R}✗ Connection failed: ${err.message}${RST}\n`);
    console.log(`${Y}Type: \\switch <neon_connection_string> to connect.${RST}\n`);
  }

  console.log(`${Y}${B}Quick ERP Commands:${RST}`);
  console.log(`  ${C}\\dt${RST}             - List all database tables with row counts`);
  console.log(`  ${C}\\users${RST}          - View institutional users (students, faculty, admins)`);
  console.log(`  ${C}\\bookings${RST}       - View venue & festival reservation requests`);
  console.log(`  ${C}\\pending${RST}        - View only requests awaiting admin approval`);
  console.log(`  ${C}\\approve <id>${RST}   - Instantly approve a venue booking request`);
  console.log(`  ${C}\\reject <id>${RST}    - Reject a booking request`);
  console.log(`  ${C}\\audit${RST}          - View recent security & admin audit trail`);
  console.log(`  ${C}\\stats${RST}          - Telemetry summary (users, bookings, audit records)`);
  console.log(`  ${C}\\sync${RST}           - Push local users_store.json state to Neon`);
  console.log(`  ${C}\\ping${RST}           - Measure live round-trip latency to Neon`);
  console.log(`  ${C}\\switch <url>${RST}   - Switch database connection`);
  console.log(`  ${C}clear${RST}           - Clear screen`);
  console.log(`  ${C}exit${RST}            - Quit terminal\n`);
  console.log(`${D}Type any custom SQL (e.g. SELECT * FROM cit_users;) and press Enter:${RST}\n`);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: `${G}cit_erp${RST}${C}#${RST} `,
  });

  rl.prompt();

  let isExecuting = false;

  rl.on('line', async (line) => {
    if (isExecuting) return;
    const cmd = line.trim();

    if (!cmd) {
      rl.prompt();
      return;
    }

    if (cmd === 'exit' || cmd === '\\q' || cmd === 'quit') {
      console.log(`${D}Closing connection to Neon Cloud...${RST}`);
      if (pool) {
        try { await pool.end(); } catch {}
      }
      process.exit(0);
    }

    if (cmd === 'clear' || cmd === 'cls') {
      console.clear();
      rl.prompt();
      return;
    }

    if (cmd === '\\help' || cmd === 'help') {
      console.log(`\n${Y}CIT ERP Terminal Commands:${RST}`);
      console.log(`  \\dt, \\tables     - List all tables`);
      console.log(`  \\users           - Show registered institutional accounts`);
      console.log(`  \\bookings        - Show all venue bookings`);
      console.log(`  \\pending         - Show pending booking requests`);
      console.log(`  \\approve <id>    - Approve a pending booking`);
      console.log(`  \\reject <id>     - Reject a booking`);
      console.log(`  \\audit, \\logs    - Show recent security audit trail`);
      console.log(`  \\stats           - Show counts for users, bookings, audit events`);
      console.log(`  \\sync            - Push local JSON state to Neon Cloud`);
      console.log(`  \\ping            - Check connection latency`);
      console.log(`  \\switch <url>    - Switch to another Neon connection string`);
      console.log(`  clear, cls       - Clear terminal screen`);
      console.log(`  exit, \\q         - Exit terminal\n`);
      rl.prompt();
      return;
    }

    if (cmd === '\\sync') {
      isExecuting = true;
      try {
        await syncLocalStateToNeon();
      } catch (e) {
        console.log(`${R}✗ Sync error: ${e.message}${RST}\n`);
      } finally {
        isExecuting = false;
        rl.prompt();
      }
      return;
    }

    if (cmd === '\\ping') {
      try {
        const t0 = Date.now();
        await executeSql('SELECT 1');
        console.log(`${G}✓ Neon Latency: ${Date.now() - t0}ms${RST}\n`);
      } catch (e) {
        console.log(`${R}✗ Ping failed: ${e.message}${RST}\n`);
      }
      rl.prompt();
      return;
    }

    if (cmd.startsWith('\\switch')) {
      const parts = cmd.split(/\s+/);
      const newUrl = parts[1];
      if (!newUrl) {
        console.log(`${R}Usage: \\switch <postgresql://...>${RST}\n`);
      } else {
        console.log(`${D}Switching database...${RST}`);
        try {
          const t0 = Date.now();
          const info = await connectToNeon(newUrl);
          activeUrl = newUrl;
          console.log(`${G}✓ Switched via ${info.method} in ${Date.now() - t0}ms!${RST}\n`);
          await initializeCitSchema();
        } catch (e) {
          console.log(`${R}✗ Switch failed: ${e.message}${RST}\n`);
        }
      }
      rl.prompt();
      return;
    }

    if (cmd.startsWith('\\approve')) {
      const parts = cmd.split(/\s+/);
      const reqId = parts[1];
      if (!reqId) {
        console.log(`${R}Usage: \\approve <booking_id>${RST}\n`);
      } else {
        try {
          await executeSql(`UPDATE cit_bookings SET status = 'Approved' WHERE id = '${reqId.replace(/'/g, "''")}';`);
          await executeSql(`
            INSERT INTO cit_audit_logs (id, action, actor, details)
            VALUES ('LOG-${Date.now()}', 'Approve Booking', 'Admin Terminal', 'Approved ${reqId}');
          `);
          console.log(`${G}✓ Booking ${reqId} Approved!${RST}\n`);
        } catch (e) {
          console.log(`${R}✗ Error: ${e.message}${RST}\n`);
        }
      }
      rl.prompt();
      return;
    }

    if (cmd.startsWith('\\reject')) {
      const parts = cmd.split(/\s+/);
      const reqId = parts[1];
      if (!reqId) {
        console.log(`${R}Usage: \\reject <booking_id>${RST}\n`);
      } else {
        try {
          await executeSql(`UPDATE cit_bookings SET status = 'Rejected' WHERE id = '${reqId.replace(/'/g, "''")}';`);
          await executeSql(`
            INSERT INTO cit_audit_logs (id, action, actor, details)
            VALUES ('LOG-${Date.now()}', 'Reject Booking', 'Admin Terminal', 'Rejected ${reqId}');
          `);
          console.log(`${Y}✓ Booking ${reqId} marked as Rejected.${RST}\n`);
        } catch (e) {
          console.log(`${R}✗ Error: ${e.message}${RST}\n`);
        }
      }
      rl.prompt();
      return;
    }

    let sql = cmd;

    if (cmd === '\\dt' || cmd === '\\tables') {
      sql = `SELECT tablename as "Table Name", tableowner as "Owner" FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;`;
    } else if (cmd === '\\users') {
      sql = `SELECT id, name, email, role, cohort, status FROM cit_users ORDER BY role, id;`;
    } else if (cmd === '\\bookings') {
      sql = `SELECT id, room_id, user_email, event_name, date, periods, status FROM cit_bookings ORDER BY created_at DESC LIMIT 20;`;
    } else if (cmd === '\\pending') {
      sql = `SELECT id, room_id, user_email, purpose, date, periods, status FROM cit_bookings WHERE LOWER(status) LIKE '%review%' OR LOWER(status) LIKE '%pending%' ORDER BY created_at DESC;`;
    } else if (cmd === '\\audit' || cmd === '\\logs') {
      sql = `SELECT id, action, actor, details, timestamp FROM cit_audit_logs ORDER BY timestamp DESC LIMIT 15;`;
    } else if (cmd === '\\stats') {
      sql = `
        SELECT 
          (SELECT COUNT(*) FROM cit_users) as "CIT Users",
          (SELECT COUNT(*) FROM cit_bookings) as "Total Bookings",
          (SELECT COUNT(*) FROM cit_bookings WHERE LOWER(status) LIKE '%approved%') as "Approved",
          (SELECT COUNT(*) FROM cit_bookings WHERE LOWER(status) LIKE '%review%' OR LOWER(status) LIKE '%pending%') as "Pending",
          (SELECT COUNT(*) FROM cit_audit_logs) as "Audit Events";
      `;
    }

    isExecuting = true;
    try {
      const start = Date.now();
      const rows = await executeSql(sql);
      const elapsed = Date.now() - start;

      if (rows && rows.length > 0) {
        console.table(rows);
        console.log(`${G}✓ ${rows.length} row(s) returned (${elapsed}ms)${RST}\n`);
      } else {
        console.log(`${G}✓ Query executed successfully, 0 rows returned (${elapsed}ms)${RST}\n`);
      }
    } catch (err) {
      console.log(`${R}✗ Error: ${err.message}${RST}\n`);
    } finally {
      isExecuting = false;
      rl.prompt();
    }
  });

  rl.on('close', async () => {
    if (pool) {
      try { await pool.end(); } catch {}
    }
    console.log(`\n${D}Disconnected from CIT Neon Cloud Database.${RST}`);
    process.exit(0);
  });
}

startTerminal();
