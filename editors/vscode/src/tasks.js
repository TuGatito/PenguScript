// Tareas de VS Code para `pengu build` y `pengu run`: Ctrl+Shift+B, «Run Task»
// y `tasks.json` con `"type": "pengu"`.

const path = require("node:path");
const { ShellExecution, Task, TaskGroup, TaskScope, tasks } = require("vscode");
const { executable_command } = require("./executable");
const { project_cwd, quote } = require("./terminal");
const { extra_args } = require("./settings");

const TASK_TYPE = "pengu";

function shell_command(kind, file) {
  const executable = executable_command();
  const args = extra_args(kind === "build" ? "build.args" : "run.args");
  const parts = [quote(executable), kind, ...args.map(quote)];
  if (file !== undefined) parts.push(quote(file));
  return parts.join(" ");
}

function make_task(definition) {
  const kind = definition.command;
  const file = typeof definition.file === "string" ? path.resolve(definition.file) : undefined;
  const task = new Task(
    definition,
    TaskScope.Workspace,
    `pengu: ${kind === "build" ? "compilar" : "ejecutar"}`,
    TASK_TYPE,
    new ShellExecution(shell_command(kind, file), { cwd: project_cwd(file) }),
    ["$pengu"],
  );
  task.group = kind === "build" ? TaskGroup.Build : undefined;
  return task;
}

// Fábrica del proveedor (sin clases, igual que el resto del proyecto).
function create_provider() {
  return {
    provideTasks() {
      return [make_task({ type: TASK_TYPE, command: "build" }), make_task({ type: TASK_TYPE, command: "run" })];
    },
    resolveTask(task) {
      const definition = task.definition ?? {};
      if (definition.type !== TASK_TYPE) return undefined;
      if (definition.command !== "build" && definition.command !== "run") return undefined;
      return make_task(definition);
    },
  };
}

function register() {
  return tasks.registerTaskProvider(TASK_TYPE, create_provider());
}

module.exports = { register, make_task, TASK_TYPE };
