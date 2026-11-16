//! Monomorfización B2: recolecta instancias alcanzables de funciones genéricas.

use std::collections::{HashMap, HashSet, VecDeque};

use pengu_diag::Diagnostic;
use pengu_hir::{BodyId, DefId, HirCrate, Res};
use pengu_span::Span;
use pengu_syntax::ast::{Block, Expr, ExprKind, MatchArm, Stmt, StmtKind, TypeKind};
use pengu_types::{CheckResult, Ty};

type Queue = VecDeque<(DefId, Vec<Ty>, Option<HashMap<DefId, Ty>>)>;

/// Una instancia monomórfica de una función genérica.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MonoInstance {
    /// Definición original.
    pub def: DefId,
    /// Argumentos de tipo.
    pub type_args: Vec<Ty>,
    /// Nombre generado.
    pub name: String,
}

/// Resultado del plan de monomorfización.
#[derive(Clone, Debug, Default)]
pub struct MonoPlan {
    /// Instancias alcanzables.
    pub instances: Vec<MonoInstance>,
    /// Diagnósticos.
    pub diagnostics: Vec<Diagnostic>,
}

/// Calcula las instancias alcanzables desde cuerpos no genéricos.
#[must_use]
pub fn plan_monomorphization(krate: &HirCrate, _types: &CheckResult) -> MonoPlan {
    let mut planner = Planner {
        krate,
        types: _types,
        instances: Vec::new(),
        seen: HashSet::new(),
        diagnostics: Vec::new(),
    };
    planner.run(_types);
    planner.instances.sort_by(|a, b| a.name.cmp(&b.name));
    MonoPlan {
        instances: planner.instances,
        diagnostics: planner.diagnostics,
    }
}

struct Planner<'a> {
    krate: &'a HirCrate,
    types: &'a CheckResult,
    instances: Vec<MonoInstance>,
    seen: HashSet<(DefId, Vec<Ty>)>,
    diagnostics: Vec<Diagnostic>,
}

impl Planner<'_> {
    fn run(&mut self, types: &CheckResult) {
        let mut queue: Queue = VecDeque::new();
        for body in &self.krate.bodies {
            let Some(sig) = self.krate.signatures.get(&body.owner) else {
                continue;
            };
            if sig.generics.is_empty() {
                if let Some(ast) = &body.ast {
                    queue.push_back((body.owner, Vec::new(), Some(HashMap::new())));
                    self.walk(ast, body.id, &HashMap::new(), &mut queue);
                }
            }
        }
        self.collect_impl_instances(types, &mut queue);
        while let Some((def, args, _env)) = queue.pop_front() {
            let Some(sig) = self.krate.signatures.get(&def).cloned() else {
                continue;
            };
            if !sig.generics.is_empty() {
                let key = (def, args.clone());
                if !self.seen.insert(key) {
                    continue;
                }
                let name = instance_name(self.krate, def, &args);
                self.instances.push(MonoInstance {
                    def,
                    type_args: args.clone(),
                    name,
                });
                let mut env = HashMap::new();
                for (generic, ty) in sig.generics.iter().zip(args.iter()) {
                    env.insert(generic.def, ty.clone());
                }
                let body_ast = self
                    .body_for(def)
                    .and_then(|body| body.ast.clone().map(|ast| (body.id, ast)));
                if let Some((body_id, ast)) = body_ast {
                    self.walk(&ast, body_id, &env, &mut queue);
                }
            }
        }
    }

    fn collect_impl_instances(&mut self, types: &CheckResult, queue: &mut Queue) {
        let mut candidates: Vec<Ty> = types
            .types
            .iter()
            .map(|(_, ty)| ty.clone())
            .chain(
                types
                    .locals
                    .values()
                    .flat_map(|locals| locals.values().cloned()),
            )
            .collect();
        candidates.sort_by_key(|ty| format!("{ty:?}"));
        candidates.dedup();
        for imp in &self.krate.impls {
            if imp.generics.is_empty() {
                continue;
            }
            let Some(target) = self.impl_target_def(imp) else {
                continue;
            };
            for ty in &candidates {
                let Ty::Adt(def, args) = ty else {
                    continue;
                };
                if *def != target || args.len() != imp.generics.len() {
                    continue;
                }
                let env: HashMap<DefId, Ty> = imp
                    .generics
                    .iter()
                    .zip(args.iter())
                    .map(|(generic, ty)| (generic.def, ty.clone()))
                    .collect();
                for method in &imp.methods {
                    if !self.seen.insert((*method, args.clone())) {
                        continue;
                    }
                    let name = method_instance_name(self.krate, *method, args);
                    self.instances.push(MonoInstance {
                        def: *method,
                        type_args: args.clone(),
                        name,
                    });
                    if let Some((body_id, ast)) = self
                        .body_for(*method)
                        .and_then(|body| body.ast.clone().map(|ast| (body.id, ast)))
                    {
                        self.walk(&ast, body_id, &env, queue);
                    }
                }
            }
        }
    }

    fn impl_target_def(&self, imp: &pengu_hir::hir::ImplDef) -> Option<DefId> {
        let TypeKind::Path { segments, .. } = &imp.ty.kind else {
            return None;
        };
        let name = segments.last()?;
        self.krate
            .defs
            .iter()
            .find(|def| def.kind == pengu_hir::DefKind::Type && def.name == *name)
            .map(|def| def.id)
    }

    fn body_for(&self, def: DefId) -> Option<&pengu_hir::Body> {
        self.krate.bodies.iter().find(|body| body.owner == def)
    }

    fn walk(&mut self, block: &Block, body: BodyId, env: &HashMap<DefId, Ty>, queue: &mut Queue) {
        for stmt in &block.stmts {
            self.walk_stmt(stmt, body, env, queue);
        }
    }

    fn walk_stmt(
        &mut self,
        stmt: &Stmt,
        body: BodyId,
        env: &HashMap<DefId, Ty>,
        queue: &mut Queue,
    ) {
        match &stmt.kind {
            StmtKind::Bind { value, .. } => self.walk_expr(value, body, env, queue),
            StmtKind::Assign { target, value } => {
                self.walk_expr(target, body, env, queue);
                self.walk_expr(value, body, env, queue);
            }
            StmtKind::Expr(expr) => self.walk_expr(expr, body, env, queue),
            StmtKind::While { cond, body: inner } => {
                self.walk_expr(cond, body, env, queue);
                self.walk(inner, body, env, queue);
            }
            StmtKind::For {
                iter, body: inner, ..
            } => {
                self.walk_expr(iter, body, env, queue);
                self.walk(inner, body, env, queue);
            }
            StmtKind::Return(Some(expr)) | StmtKind::Break(Some(expr)) => {
                self.walk_expr(expr, body, env, queue);
            }
            StmtKind::Return(None) | StmtKind::Break(None) | StmtKind::Continue => {}
        }
    }

    fn walk_expr(
        &mut self,
        expr: &Expr,
        body: BodyId,
        env: &HashMap<DefId, Ty>,
        queue: &mut Queue,
    ) {
        match &expr.kind {
            ExprKind::Call { callee, args } => {
                for arg in args {
                    self.walk_expr(arg, body, env, queue);
                }
                let (base, type_expr) = match &callee.kind {
                    ExprKind::Index { base, index } => (base.as_ref(), Some(index.as_ref())),
                    _ => (callee.as_ref(), None),
                };
                let Some(Res::Def(def)) = self.resolution(body, base.span) else {
                    return;
                };
                let Some(sig) = self.krate.signatures.get(&def).cloned() else {
                    return;
                };
                if sig.generics.is_empty() {
                    if self.body_for(def).is_some_and(|body| body.ast.is_some()) {
                        queue.push_back((def, Vec::new(), Some(HashMap::new())));
                    }
                    return;
                }
                let args = type_expr
                    .and_then(|expr| self.type_arg(expr, env))
                    .or_else(|| {
                        self.types
                            .instantiations
                            .get(&expr.span)
                            .or_else(|| self.types.instantiations.get(&base.span))
                            .cloned()
                    })
                    .unwrap_or_else(|| vec![Ty::Error; sig.generics.len()]);
                if args.contains(&Ty::Error) {
                    self.diagnostics.push(Diagnostic::error(
                        "PGS-E1305",
                        format!(
                            "no se puede inferir la instancia de `{}`",
                            self.krate.defs[def.index()].name
                        ),
                        callee.span,
                    ));
                    return;
                }
                queue.push_back((def, args, None));
            }
            ExprKind::Unary { expr, .. } => self.walk_expr(expr, body, env, queue),
            ExprKind::Binary { lhs, rhs, .. } => {
                self.walk_expr(lhs, body, env, queue);
                self.walk_expr(rhs, body, env, queue);
            }
            ExprKind::Tuple(items) | ExprKind::Array(items) | ExprKind::Vector(items) => {
                for item in items {
                    self.walk_expr(item, body, env, queue);
                }
            }
            ExprKind::If {
                cond,
                then_branch,
                else_branch,
                ..
            } => {
                self.walk_expr(cond, body, env, queue);
                self.walk(then_branch, body, env, queue);
                if let Some(branch) = else_branch {
                    self.walk(branch, body, env, queue);
                }
            }
            ExprKind::Match { scrutinee, arms } => {
                self.walk_expr(scrutinee, body, env, queue);
                for MatchArm { body: block, .. } in arms {
                    self.walk(block, body, env, queue);
                }
            }
            ExprKind::Do(block) | ExprKind::Loop(block) | ExprKind::Curse(block) => {
                self.walk(block, body, env, queue);
            }
            ExprKind::Lambda { body: block, .. } => self.walk(block, body, env, queue),
            ExprKind::Record { fields, base, .. } => {
                for (_, value) in fields {
                    self.walk_expr(value, body, env, queue);
                }
                if let Some(base) = base {
                    self.walk_expr(base, body, env, queue);
                }
            }
            ExprKind::Index { base, index } => {
                self.walk_expr(base, body, env, queue);
                self.walk_expr(index, body, env, queue);
            }
            ExprKind::Field { base, .. }
            | ExprKind::Try(base)
            | ExprKind::Cast { expr: base, .. } => {
                self.walk_expr(base, body, env, queue);
            }
            _ => {}
        }
    }

    fn resolution(&self, body: BodyId, span: Span) -> Option<Res> {
        self.krate.bodies.get(body.index()).and_then(|body| {
            body.resolutions
                .iter()
                .find(|r| r.span == span)
                .map(|r| r.res)
        })
    }

    fn type_arg(&self, expr: &Expr, env: &HashMap<DefId, Ty>) -> Option<Vec<Ty>> {
        let ExprKind::Path(segments) = &expr.kind else {
            return None;
        };
        if segments.len() != 1 {
            return None;
        }
        let name = &segments[0];
        for (def, ty) in env {
            if self.krate.defs[def.index()].name == *name {
                return Some(vec![ty.clone()]);
            }
        }
        Some(vec![primitive(name)?])
    }
}

fn primitive(name: &str) -> Option<Ty> {
    Some(match name {
        "Bool" => Ty::Bool,
        "Int" | "I32" => Ty::Int,
        "I8" => Ty::I8,
        "I16" => Ty::I16,
        "I64" => Ty::I64,
        "Isize" => Ty::Isize,
        "U8" => Ty::U8,
        "U16" => Ty::U16,
        "U32" => Ty::U32,
        "U64" => Ty::U64,
        "Usize" => Ty::Usize,
        "Float" | "F64" => Ty::Float,
        "F32" => Ty::F32,
        "Char" => Ty::Char,
        "String" => Ty::String,
        "Str" => Ty::Str,
        _ => return None,
    })
}

fn instance_name(krate: &HirCrate, def: DefId, args: &[Ty]) -> String {
    let mut name = krate.defs[def.index()].name.clone();
    for ty in args {
        name.push_str("__");
        name.push_str(&ty.to_string().replace(['[', ']', ' ', ',', '&'], "_"));
    }
    name
}

fn method_instance_name(krate: &HirCrate, def: DefId, args: &[Ty]) -> String {
    let mut name = krate.defs[def.index()].name.clone();
    for ty in args {
        name.push_str("__");
        name.push_str(&format!("{ty:?}"));
    }
    name
}
