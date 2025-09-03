const express = require("express");
const mysql = require("mysql2/promise");

const PORT = process.env.PORT || 3000;

// credenciais criadas no provisionamento do Vagrantfile
const DB = {
  host: "database",
  user: "app_user",
  password: "app_pass",
  database: "app_db",
  waitForConnections: true,
  connectionLimit: 10
};

async function makePool() {
  const pool = await mysql.createPool(DB);
  // garante tabela
  await pool.execute(`
    CREATE TABLE IF NOT EXISTS todos (
      id INT AUTO_INCREMENT PRIMARY KEY,
      title VARCHAR(100) NOT NULL,
      done TINYINT DEFAULT 0
    )
  `);
  // se vazia, insere exemplo
  const [rows] = await pool.query("SELECT COUNT(*) AS c FROM todos");
  if (rows[0].c === 0) {
    await pool.query("INSERT INTO todos (title, done) VALUES ('Primeira tarefa', 0), ('Estudar Vagrant', 1)");
  }
  return pool;
}

(async () => {
  const app = express();
  app.use(express.json());

  const pool = await makePool();

  app.get("/health", (req, res) => {
    res.json({ status: "ok", service: "node-app" });
  });

  app.get("/api/todos", async (req, res) => {
    const [rows] = await pool.query("SELECT id, title, done FROM todos ORDER BY id");
    res.json(rows.map(r => ({ id: r.id, title: r.title, done: !!r.done })));
  });

  app.post("/api/todos", async (req, res) => {
    const { title } = req.body || {};
    if (!title) return res.status(400).json({ error: "title é obrigatório" });
    const [r] = await pool.query("INSERT INTO todos (title, done) VALUES (?, 0)", [title]);
    res.status(201).json({ id: r.insertId, title, done: false });
  });

  app.put("/api/todos/:id", async (req, res) => {
    const id = Number(req.params.id);
    const { title, done } = req.body || {};
    if (!Number.isInteger(id)) return res.status(400).json({ error: "id inválido" });
    const [r] = await pool.query(
      "UPDATE todos SET title = COALESCE(?, title), done = COALESCE(?, done) WHERE id = ?",
      [title ?? null, typeof done === "boolean" ? (done ? 1 : 0) : null, id]
    );
    if (r.affectedRows === 0) return res.status(404).json({ error: "não encontrado" });
    res.json({ id, title, done });
  });

  app.delete("/api/todos/:id", async (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) return res.status(400).json({ error: "id inválido" });
    const [r] = await pool.query("DELETE FROM todos WHERE id = ?", [id]);
    if (r.affectedRows === 0) return res.status(404).json({ error: "não encontrado" });
    res.status(204).send();
  });

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Node app ouvindo em http://0.0.0.0:${PORT}`);
  });
})().catch(err => {
  console.error("Falha ao iniciar servidor:", err);
  process.exit(1);
});
