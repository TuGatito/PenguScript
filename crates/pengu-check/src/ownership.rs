//! Análisis de ownership, moves y préstamos (C4).

use std::collections::{HashMap, HashSet};

use pengu_diag::Diagnostic;
use pengu_hir::{BodyId, HirCrate, LocalId, Res, Signature};
use pengu_span::Span;
use pengu_syntax::ast::{Block, Expr, ExprKind, Pattern, PatternKind, Receiver, Stmt, StmtKind};
use pengu_types::{CheckResult, Ty, check_crate};

/// Resultado de la comprobación de ownership.
#[derive(Clone, Debug, Default)]
pub struct OwnershipResult {
    /// Diagnósticos de ownership.
    pub diagnostics: Vec<Diagnostic>,
}

impl OwnershipResult {
    /// `true` si no hay errores.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        !self.diagnostics.iter().any(Diagnostic::is_error)
    }
}

/// Comprueba tipos y después ownership.
#[must_use]
pub fn check_ownership(krate: &HirCrate) -> OwnershipResult {
    let types = check_crate(krate);
    check_ownership_with(krate, &types)
}

/// Comprueba ownership usando tipos ya calculados.
#[must_use]
pub fn check_ownership_with(krate: &HirCrate, types: &CheckResult) -> OwnershipResult {
    let mut checker = OwnershipChecker::new(krate, types);
    checker.run();
    OwnershipResult {
        diagnostics: checker.diagnostics,
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Hash)]
enum Projection {
    Field(String),
    Index,
}

#[derive(Clone, Debug, Eq, PartialEq, Hash)]
struct Place {
    local: LocalId,
    projections: Vec<Projection>,
}

impl Place {
    const fn new(local: LocalId) -> Self {
        Self {
            local,
            projections: Vec::new(),
        }
    }

    fn field(&self, name: &str) -> Self {
        let mut projections = self.projections.clone();
        projections.push(Projection::Field(name.to_owned()));
        Self {
            local: self.local,
            projections,
        }
    }

    fn index(&self) -> Self {
        let mut projections = self.projections.clone();
        projections.push(Projection::Index);
        Self {
            local: self.local,
            projections,
        }
    }

    fn overlaps(&self, other: &Self) -> bool {
        self.local == other.local
            && (prefix(&self.projections, &other.projections)
                || prefix(&other.projections, &self.projections))
    }

    fn is_prefix_of(&self, other: &Self) -> bool {
        self.local == other.local && prefix(&self.projections, &other.projections)
    }
}

fn prefix(left: &[Projection], right: &[Projection]) -> bool {
    left.len() <= right.len() && left.iter().zip(right).all(|(a, b)| a == b)
}

#[derive(Clone, Debug)]
struct Loan {
    place: Place,
    mutable: bool,
    owner: Option<LocalId>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct LocalState {
    initialized: bool,
}

#[derive(Clone, Debug, Default)]
struct State {
    locals: HashMap<LocalId, LocalState>,
    moved: HashSet<Place>,
    loans: Vec<Loan>,
    refs: HashMap<LocalId, Place>,
}

impl State {
    fn is_moved(&self, place: &Place) -> bool {
        self.moved.iter().any(|moved| {
            moved.is_prefix_of(place) || (place.projections.is_empty() && place.is_prefix_of(moved))
        })
    }

    fn mark_moved(&mut self, place: Place) {
        self.moved.insert(place);
    }

    fn clear_moved(&mut self, place: &Place) {
        self.moved.retain(|moved| !place.overlaps(moved));
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Mode {
    Read,
    Move,
}

struct OwnershipChecker<'a> {
    krate: &'a HirCrate,
    types: &'a CheckResult,
    diagnostics: Vec<Diagnostic>,
    body_id: Option<BodyId>,
    body: Option<&'a pengu_hir::Body>,
    type_by_span: HashMap<Span, Ty>,
    local_mut: HashMap<LocalId, bool>,
    local_ty: HashMap<LocalId, Ty>,
    resolutions: HashMap<Span, Res>,
    state: State,
    is_method: bool,
}

impl<'a> OwnershipChecker<'a> {
    fn new(krate: &'a HirCrate, types: &'a CheckResult) -> Self {
        let mut type_by_span = HashMap::new();
        for (span, ty) in &types.types {
            type_by_span.insert(*span, ty.clone());
        }
        Self {
            krate,
            types,
            diagnostics: Vec::new(),
            body_id: None,
            body: None,
            type_by_span,
            local_mut: HashMap::new(),
            local_ty: HashMap::new(),
            resolutions: HashMap::new(),
            state: State::default(),
            is_method: false,
        }
    }

    fn run(&mut self) {
        for body in &self.krate.bodies {
            let Some(ast) = &body.ast else {
                continue;
            };
            let Some(signature) = self.krate.signature(body.owner) else {
                continue;
            };
            self.body_id = Some(body.id);
            self.body = Some(body);
            self.is_method = body.self_ty.is_some();
            self.local_mut.clear();
            self.local_ty.clear();
            self.resolutions.clear();
            for local in &body.locals {
                self.local_mut.insert(local.id, local.mutable);
            }
            if let Some(locals) = self.types.locals.get(&body.id) {
                self.local_ty.clone_from(locals);
            }
            for resolution in &body.resolutions {
                self.resolutions.insert(resolution.span, resolution.res);
            }
            self.state = State::default();
            for local in &body.locals {
                self.state
                    .locals
                    .insert(local.id, LocalState { initialized: false });
            }
            if let Some(self_local) = body.self_local {
                if let Some(state) = self.state.locals.get_mut(&self_local) {
                    state.initialized = true;
                }
            }
            for param in &body.params {
                if let Some(state) = self.state.locals.get_mut(param) {
                    state.initialized = true;
                }
            }
            self.check_signature(signature, body.owner);
            self.check_imports(body);
            self.block(ast);
        }
    }

    fn check_imports(&mut self, body: &pengu_hir::Body) {
        let has_rc = self.has_import("Rc");
        let has_arc = self.has_import("Arc");
        for local in &body.locals {
            let Some(ty) = self.local_ty.get(&local.id).cloned() else {
                continue;
            };
            if matches!(ty, Ty::Rc(_)) && !has_rc {
                self.error(
                    "PGS-E4107",
                    "`Rc` se usa sin importar; añade `summon std::rc::Rc`",
                    local.span,
                );
            }
            if matches!(ty, Ty::Arc(_)) && !has_arc {
                self.error(
                    "PGS-E4107",
                    "`Arc` se usa sin importar; añade `summon std::sync::Arc`",
                    local.span,
                );
            }
        }
    }

    fn has_import(&self, name: &str) -> bool {
        self.krate
            .modules
            .iter()
            .any(|module| self.krate.scope(module.scope).values.contains_key(name))
    }

    fn check_signature(&mut self, signature: &Signature, owner: pengu_hir::DefId) {
        if self.is_method {
            return;
        }
        if contains_ref(&signature.ret) {
            let span = self.krate.def(owner).span;
            self.error(
                "PGS-E4109",
                "no se puede inferir la vida de la referencia devuelta",
                span,
            );
        }
    }

    fn error(&mut self, code: &'static str, message: &str, span: Span) {
        // Un mismo error puede detectarse en dos pasadas (lectura y movimiento); para
        // el usuario y para el LSP es ruido repetirlo.
        if self.diagnostics.iter().any(|existing| {
            existing.code == code && existing.message == message && existing.primary == span
        }) {
            return;
        }
        self.diagnostics
            .push(Diagnostic::error(code, message, span));
    }

    fn res_at(&self, span: Span) -> Option<Res> {
        self.resolutions.get(&span).copied()
    }

    fn local_at(&self, span: Span) -> Option<LocalId> {
        match self.res_at(span)? {
            Res::Local(local) => Some(local),
            _ => None,
        }
    }

    fn place_of(&self, expr: &Expr) -> Option<Place> {
        match &expr.kind {
            ExprKind::Path(path) if path.len() == 1 => self.local_at(expr.span).map(Place::new),
            ExprKind::SelfValue => self.body.and_then(|body| body.self_local).map(Place::new),
            ExprKind::Field { base, name } => Some(self.place_of(base)?.field(name)),
            ExprKind::Index { base, .. } => Some(self.place_of(base)?.index()),
            _ => None,
        }
    }

    fn ty_of(&self, expr: &Expr) -> Ty {
        if let Some(place) = self.place_of(expr) {
            if place.projections.is_empty() {
                if let Some(ty) = self.local_ty.get(&place.local) {
                    return ty.clone();
                }
            }
        }
        self.type_by_span
            .get(&expr.span)
            .cloned()
            .unwrap_or(Ty::Error)
    }

    fn ty_of_place(&self, place: &Place) -> Ty {
        if place.projections.is_empty() {
            return self
                .local_ty
                .get(&place.local)
                .cloned()
                .unwrap_or(Ty::Error);
        }
        Ty::Error
    }

    fn is_copy(&self, ty: &Ty) -> bool {
        match ty {
            Ty::Bool
            | Ty::Int
            | Ty::I8
            | Ty::I16
            | Ty::I32
            | Ty::I64
            | Ty::Isize
            | Ty::U8
            | Ty::U16
            | Ty::U32
            | Ty::U64
            | Ty::Usize
            | Ty::Float
            | Ty::F32
            | Ty::F64
            | Ty::Char
            | Ty::Str
            | Ty::Unit
            | Ty::Never
            | Ty::CStr
            | Ty::Ordering
            | Ty::Error
            | Ty::Infer(_)
            | Ty::IntVar(_)
            | Ty::FloatVar(_) => true,
            Ty::Tuple(items) => items.iter().all(|item| self.is_copy(item)),
            Ty::Array(item, _) | Ty::Slice(item, _) | Ty::Ref(item, _) | Ty::Ptr(item) => {
                self.is_copy(item)
            }
            Ty::Option(item) => self.is_copy(item),
            Ty::Result(ok, err) => self.is_copy(ok) && self.is_copy(err),
            Ty::Range(item) => self.is_copy(item),
            Ty::Fn(..) => true,
            Ty::Adt(def, _) => self.krate.adt(*def).is_some_and(|adt| adt.is_copy),
            Ty::String
            | Ty::Vec(_)
            | Ty::Map(..)
            | Ty::Set(_)
            | Ty::Box(_)
            | Ty::Rc(_)
            | Ty::Arc(_)
            | Ty::CString
            | Ty::Iterator(_)
            | Ty::Generic(_) => false,
        }
    }

    fn read_local(&mut self, local: LocalId, span: Span) {
        if self
            .state
            .locals
            .get(&local)
            .is_none_or(|state| !state.initialized)
        {
            self.error("PGS-E4101", "uso de un valor no inicializado", span);
        }
        let place = Place::new(local);
        if self.state.is_moved(&place) {
            self.error("PGS-E4101", "uso de un valor movido", span);
        }
    }

    fn read_place(&mut self, place: &Place, span: Span) {
        if self.state.is_moved(place) {
            self.error("PGS-E4101", "uso de un valor movido", span);
        }
        if place.projections.is_empty()
            && self
                .state
                .locals
                .get(&place.local)
                .is_none_or(|state| !state.initialized)
        {
            self.error("PGS-E4101", "uso de un valor no inicializado", span);
        }
    }

    fn move_place(&mut self, place: Place, span: Span) {
        if self.state.is_moved(&place) {
            self.error("PGS-E4101", "uso de un valor movido", span);
        }
        if self
            .state
            .loans
            .iter()
            .any(|loan| loan.place.overlaps(&place))
        {
            self.error(
                "PGS-E4106",
                "no se puede mover un valor mientras está prestado",
                span,
            );
            return;
        }
        self.state.mark_moved(place);
    }

    fn is_place_mutable(&self, place: &Place) -> bool {
        self.local_mut.get(&place.local).copied().unwrap_or(false)
    }

    fn assign_place(&mut self, place: &Place, span: Span) {
        if !self.is_place_mutable(place) {
            self.error(
                "PGS-E4103",
                "no se puede asignar a un binding inmutable",
                span,
            );
        }
        if self
            .state
            .loans
            .iter()
            .any(|loan| loan.place.overlaps(place))
        {
            self.error("PGS-E4108", "no se puede asignar a un valor prestado", span);
            return;
        }
        self.state.clear_moved(place);
        if let Some(state) = self.state.locals.get_mut(&place.local) {
            state.initialized = true;
        }
    }

    fn borrow(&mut self, place: Place, mutable: bool, span: Span) {
        if mutable && !self.is_place_mutable(&place) {
            self.error(
                "PGS-E4103",
                "no se puede tomar `&mut` de un binding inmutable",
                span,
            );
            return;
        }
        if self
            .state
            .loans
            .iter()
            .any(|loan| loan.place.overlaps(&place) && (mutable || loan.mutable))
        {
            self.error(
                "PGS-E4102",
                "préstamo inmutable y mutable simultáneos",
                span,
            );
            return;
        }
        self.state.loans.push(Loan {
            place,
            mutable,
            owner: None,
        });
    }

    fn method_def(&self, base: &Expr, name: &str) -> Option<pengu_hir::DefId> {
        let ty = self.ty_of(base);
        let type_name = match ty {
            Ty::Adt(def, _) => self.krate.defs[def.index()].name.clone(),
            Ty::Bool => "Bool".to_owned(),
            Ty::Int | Ty::I32 => "Int".to_owned(),
            Ty::I8 => "I8".to_owned(),
            Ty::I16 => "I16".to_owned(),
            Ty::I64 => "I64".to_owned(),
            Ty::Isize => "Isize".to_owned(),
            Ty::U8 => "U8".to_owned(),
            Ty::U16 => "U16".to_owned(),
            Ty::U32 => "U32".to_owned(),
            Ty::U64 => "U64".to_owned(),
            Ty::Usize => "Usize".to_owned(),
            Ty::Float | Ty::F64 => "Float".to_owned(),
            Ty::F32 => "F32".to_owned(),
            Ty::Char => "Char".to_owned(),
            Ty::String | Ty::Str => "Str".to_owned(),
            Ty::Vec(_) => "Vec".to_owned(),
            Ty::Map(..) => "Map".to_owned(),
            Ty::Set(_) => "Set".to_owned(),
            Ty::Option(_) => "Option".to_owned(),
            Ty::Result(..) => "Result".to_owned(),
            _ => return None,
        };
        self.krate
            .methods
            .get(&type_name)?
            .iter()
            .copied()
            .find(|def| self.krate.defs[def.index()].name == name)
    }

    fn is_mutating_method(name: &str) -> bool {
        matches!(
            name,
            "push"
                | "pop"
                | "insert"
                | "remove"
                | "clear"
                | "sort"
                | "sort_by"
                | "sort_unstable"
                | "reverse"
                | "retain"
                | "drain"
                | "truncate"
                | "resize"
                | "extend"
                | "splice"
                | "swap"
                | "append"
                | "push_str"
                | "make_ascii_uppercase"
                | "make_ascii_lowercase"
                | "reserve"
                | "shrink_to_fit"
        )
    }

    fn is_builtin_reader(name: &str) -> bool {
        matches!(name, "print" | "format")
    }

    fn expr(&mut self, expr: &Expr, mode: Mode) {
        match &expr.kind {
            ExprKind::Unit
            | ExprKind::Bool(_)
            | ExprKind::None
            | ExprKind::Int(_)
            | ExprKind::Float(_)
            | ExprKind::Char(_)
            | ExprKind::ByteChar(_)
            | ExprKind::String(_)
            | ExprKind::SelfValue => {}
            ExprKind::Path(path) => {
                if path.len() == 1 {
                    if let Some(local) = self.local_at(expr.span) {
                        self.read_local(local, expr.span);
                        if mode == Mode::Move
                            && !self.is_copy(&self.ty_of(expr))
                            && !self.state.is_moved(&Place::new(local))
                        {
                            self.move_place(Place::new(local), expr.span);
                        }
                    }
                }
            }
            ExprKind::Record { fields, base, .. } => {
                for (_, value) in fields {
                    self.expr(value, Mode::Move);
                }
                if let Some(base) = base {
                    self.expr(base, Mode::Move);
                }
            }
            ExprKind::Tuple(items)
            | ExprKind::Array(items)
            | ExprKind::Vector(items)
            | ExprKind::Set(items) => {
                for item in items {
                    self.expr(item, Mode::Move);
                }
            }
            ExprKind::ArrayRepeat { value, count } => {
                self.expr(value, Mode::Move);
                self.expr(count, Mode::Read);
            }
            ExprKind::Map(entries) => {
                for (key, value) in entries {
                    self.expr(key, Mode::Move);
                    self.expr(value, Mode::Move);
                }
            }
            ExprKind::Field { base, .. } => {
                if let Some(place) = self.place_of(expr) {
                    self.read_place(&place, expr.span);
                    if mode == Mode::Move
                        && !self.is_copy(&self.ty_of(expr))
                        && !self.state.is_moved(&place)
                    {
                        self.move_place(place, expr.span);
                    }
                } else {
                    self.expr(base, Mode::Read);
                }
            }
            ExprKind::Index { base, index } => {
                self.expr(base, Mode::Read);
                self.expr(index, Mode::Read);
                if let Some(place) = self.place_of(base) {
                    self.read_place(&place, base.span);
                }
            }
            ExprKind::Ref {
                mutable,
                expr: inner,
            } => {
                if let Some(place) = self.place_of(inner) {
                    self.read_place(&place, inner.span);
                    self.borrow(place, *mutable, expr.span);
                } else {
                    self.expr(inner, Mode::Read);
                }
            }
            ExprKind::Call { callee, args } => self.call(callee, args, expr.span),
            ExprKind::Unary { expr, .. } | ExprKind::Cast { expr, .. } | ExprKind::Try(expr) => {
                self.expr(expr, Mode::Read)
            }
            ExprKind::Binary { lhs, rhs, .. } => {
                self.expr(lhs, Mode::Read);
                self.expr(rhs, Mode::Read);
            }
            ExprKind::Range { start, end, .. } => {
                self.expr(start, Mode::Read);
                if let Some(end) = end {
                    self.expr(end, Mode::Read);
                }
            }
            ExprKind::If {
                cond,
                then_branch,
                else_branch,
                ..
            } => {
                self.expr(cond, Mode::Read);
                self.branches(then_branch, else_branch.as_ref());
            }
            ExprKind::Match { scrutinee, arms } => {
                self.expr(scrutinee, Mode::Read);
                let base = self.place_of(scrutinee);
                let before = self.state.clone();
                let mut merged: Option<State> = None;
                for arm in arms {
                    self.state = before.clone();
                    if let Some(pattern) = &arm.pattern {
                        self.pattern_locals(pattern);
                    }
                    if let Some(guard) = &arm.guard {
                        self.expr(guard, Mode::Read);
                    }
                    if let Some(base) = base.clone() {
                        let mut moves = Vec::new();
                        let base_ty = self.ty_of_place(&base);
                        if let Some(pattern) = &arm.pattern {
                            self.pattern_moves(pattern, &base, &base_ty, &mut moves);
                        }
                        for moved in moves {
                            self.move_place(moved, arm.body.span);
                        }
                    }
                    self.block(&arm.body);
                    merged = Some(match merged {
                        Some(previous) => merge_states(previous, self.state.clone()),
                        None => self.state.clone(),
                    });
                }
                if let Some(merged) = merged {
                    self.state = merged;
                } else {
                    self.state = before;
                }
            }
            ExprKind::Do(block) | ExprKind::Loop(block) | ExprKind::Curse(block) => {
                self.block(block);
            }
            ExprKind::Lambda { params, body } => self.lambda(params, body),
        }
    }

    fn lambda(&mut self, params: &[pengu_syntax::ast::Param], body: &Block) {
        let param_locals: HashSet<LocalId> = params
            .iter()
            .filter_map(|param| self.local_at(param.span))
            .collect();
        let mut captures = HashSet::new();
        if let Some(hir_body) = self.body {
            for resolution in &hir_body.resolutions {
                if resolution.span.file != body.span.file
                    || resolution.span.start < body.span.start
                    || resolution.span.end > body.span.end
                {
                    continue;
                }
                if let Res::Local(local) = resolution.res {
                    if param_locals.contains(&local) {
                        continue;
                    }
                    let declared_inside = hir_body
                        .locals
                        .iter()
                        .find(|decl| decl.id == local)
                        .is_some_and(|decl| {
                            decl.span.file == body.span.file
                                && decl.span.start >= body.span.start
                                && decl.span.end <= body.span.end
                        });
                    if !declared_inside {
                        captures.insert(local);
                    }
                }
            }
        }
        for local in &captures {
            let place = Place::new(*local);
            if !self.is_copy(&self.ty_of_place(&place)) {
                self.borrow(place, false, body.span);
            }
        }
        let mut consuming = false;
        let mut returning = false;
        for stmt in &body.stmts {
            self.scan_lambda_stmt(stmt, &captures, &mut consuming, &mut returning);
        }
        if returning {
            self.error(
                "PGS-E7004",
                "una closure no puede usar `return` ni `?`",
                body.span,
            );
        } else if consuming {
            self.error(
                "PGS-E7004",
                "una closure no puede consumir una captura",
                body.span,
            );
        }
    }

    fn scan_lambda_stmt(
        &self,
        stmt: &Stmt,
        captures: &HashSet<LocalId>,
        consuming: &mut bool,
        returning: &mut bool,
    ) {
        match &stmt.kind {
            StmtKind::Bind { value, .. } => {
                if let Some(local) = self.local_at(value.span) {
                    if captures.contains(&local) {
                        *consuming = true;
                    }
                }
                self.scan_lambda_expr(value, captures, consuming, returning);
            }
            StmtKind::Expr(value) => {
                self.scan_lambda_expr(value, captures, consuming, returning);
            }
            StmtKind::Assign { target, value } => {
                self.scan_lambda_expr(target, captures, consuming, returning);
                self.scan_lambda_expr(value, captures, consuming, returning);
            }
            StmtKind::While { cond, body } => {
                self.scan_lambda_expr(cond, captures, consuming, returning);
                for stmt in &body.stmts {
                    self.scan_lambda_stmt(stmt, captures, consuming, returning);
                }
            }
            StmtKind::For { iter, body, .. } => {
                self.scan_lambda_expr(iter, captures, consuming, returning);
                for stmt in &body.stmts {
                    self.scan_lambda_stmt(stmt, captures, consuming, returning);
                }
            }
            StmtKind::Return(value) => {
                *returning = true;
                if let Some(value) = value {
                    self.scan_lambda_expr(value, captures, consuming, returning);
                }
            }
            StmtKind::Break(value) => {
                if let Some(value) = value {
                    self.scan_lambda_expr(value, captures, consuming, returning);
                }
            }
            StmtKind::Continue => {}
        }
    }

    fn scan_lambda_expr(
        &self,
        expr: &Expr,
        captures: &HashSet<LocalId>,
        consuming: &mut bool,
        returning: &mut bool,
    ) {
        if let Some(local) = self.local_at(expr.span) {
            if captures.contains(&local) {
                return;
            }
        }
        match &expr.kind {
            ExprKind::Path(_) | ExprKind::SelfValue => {}
            ExprKind::Try(inner) => {
                *returning = true;
                self.scan_lambda_expr(inner, captures, consuming, returning);
            }
            ExprKind::Call { callee, args } => {
                let builtin = matches!(&callee.kind, ExprKind::Path(path) if path.last().is_some_and(|name| matches!(name.as_str(), "print" | "format")));
                if !builtin {
                    for arg in args {
                        if let Some(local) = self.local_at(arg.span) {
                            if captures.contains(&local) {
                                *consuming = true;
                            }
                        }
                        self.scan_lambda_expr(arg, captures, consuming, returning);
                    }
                }
                self.scan_lambda_expr(callee, captures, consuming, returning);
            }
            ExprKind::Lambda { body, .. } => {
                for stmt in &body.stmts {
                    self.scan_lambda_stmt(stmt, captures, consuming, returning);
                }
            }
            _ => self.scan_lambda_children(expr, captures, consuming, returning),
        }
    }

    fn scan_lambda_children(
        &self,
        expr: &Expr,
        captures: &HashSet<LocalId>,
        consuming: &mut bool,
        returning: &mut bool,
    ) {
        match &expr.kind {
            ExprKind::Record { fields, base, .. } => {
                for (_, value) in fields {
                    self.scan_lambda_expr(value, captures, consuming, returning);
                }
                if let Some(base) = base {
                    self.scan_lambda_expr(base, captures, consuming, returning);
                }
            }
            ExprKind::Tuple(items)
            | ExprKind::Array(items)
            | ExprKind::Vector(items)
            | ExprKind::Set(items) => {
                for item in items {
                    self.scan_lambda_expr(item, captures, consuming, returning);
                }
            }
            ExprKind::ArrayRepeat { value, count } => {
                self.scan_lambda_expr(value, captures, consuming, returning);
                self.scan_lambda_expr(count, captures, consuming, returning);
            }
            ExprKind::Map(entries) => {
                for (key, value) in entries {
                    self.scan_lambda_expr(key, captures, consuming, returning);
                    self.scan_lambda_expr(value, captures, consuming, returning);
                }
            }
            ExprKind::Field { base, .. }
            | ExprKind::Unary { expr: base, .. }
            | ExprKind::Cast { expr: base, .. } => {
                self.scan_lambda_expr(base, captures, consuming, returning);
            }
            ExprKind::Index { base, index } => {
                self.scan_lambda_expr(base, captures, consuming, returning);
                self.scan_lambda_expr(index, captures, consuming, returning);
            }
            ExprKind::Ref { expr, .. } => {
                self.scan_lambda_expr(expr, captures, consuming, returning);
            }
            ExprKind::Binary { lhs, rhs, .. } => {
                self.scan_lambda_expr(lhs, captures, consuming, returning);
                self.scan_lambda_expr(rhs, captures, consuming, returning);
            }
            ExprKind::Range { start, end, .. } => {
                self.scan_lambda_expr(start, captures, consuming, returning);
                if let Some(end) = end {
                    self.scan_lambda_expr(end, captures, consuming, returning);
                }
            }
            ExprKind::If {
                cond,
                then_branch,
                else_branch,
                ..
            } => {
                self.scan_lambda_expr(cond, captures, consuming, returning);
                for stmt in &then_branch.stmts {
                    self.scan_lambda_stmt(stmt, captures, consuming, returning);
                }
                if let Some(else_branch) = else_branch {
                    for stmt in &else_branch.stmts {
                        self.scan_lambda_stmt(stmt, captures, consuming, returning);
                    }
                }
            }
            ExprKind::Match { scrutinee, arms } => {
                self.scan_lambda_expr(scrutinee, captures, consuming, returning);
                for arm in arms {
                    if let Some(guard) = &arm.guard {
                        self.scan_lambda_expr(guard, captures, consuming, returning);
                    }
                    for stmt in &arm.body.stmts {
                        self.scan_lambda_stmt(stmt, captures, consuming, returning);
                    }
                }
            }
            ExprKind::Do(block) | ExprKind::Loop(block) | ExprKind::Curse(block) => {
                for stmt in &block.stmts {
                    self.scan_lambda_stmt(stmt, captures, consuming, returning);
                }
            }
            _ => {}
        }
    }

    fn call(&mut self, callee: &Expr, args: &[Expr], span: Span) {
        if let ExprKind::Field { base, name } = &callee.kind {
            self.expr(base, Mode::Read);
            if let Some(def) = self.method_def(base, name) {
                if let Some(signature) = self.krate.signature(def) {
                    if let Some(receiver) = signature.receiver {
                        if let Some(place) = self.place_of(base) {
                            match receiver {
                                Receiver::Ref => self.borrow(place, false, span),
                                Receiver::Mut => {
                                    // Los métodos de colección sobre un binding
                                    // inmutable tienen código propio (`E3106`);
                                    // el resto es un `&mut` normal (`E4103`).
                                    let is_collection = {
                                        let mut ty = self.ty_of(base);
                                        while let pengu_types::Ty::Ref(inner, _) = ty {
                                            ty = *inner;
                                        }
                                        matches!(
                                            ty,
                                            pengu_types::Ty::Vec(..)
                                                | pengu_types::Ty::Map(..)
                                                | pengu_types::Ty::Set(..)
                                        )
                                    };
                                    if is_collection && !self.is_place_mutable(&place) {
                                        self.error(
                                            "PGS-E3106",
                                            "no se puede mutar una colección inmutable",
                                            base.span,
                                        );
                                    } else {
                                        self.borrow(place, true, span);
                                    }
                                }
                                Receiver::Own => {
                                    if !self.is_copy(&self.ty_of(base)) {
                                        self.move_place(place, span);
                                    }
                                }
                            }
                        }
                    }
                }
            } else if Self::is_mutating_method(name) {
                if let Some(place) = self.place_of(base) {
                    if self
                        .state
                        .loans
                        .iter()
                        .any(|loan| loan.place.overlaps(&place))
                    {
                        self.error(
                            "PGS-E4102",
                            "préstamo inmutable y mutable simultáneos",
                            span,
                        );
                    } else if !self.is_place_mutable(&place) {
                        self.error(
                            "PGS-E3106",
                            "no se puede mutar una colección inmutable",
                            base.span,
                        );
                    }
                }
            }
        } else {
            self.expr(callee, Mode::Read);
        }
        let reader = Self::is_builtin_reader(match &callee.kind {
            ExprKind::Path(path) => path.last().map_or("", String::as_str),
            _ => "",
        });
        for arg in args {
            self.expr(arg, if reader { Mode::Read } else { Mode::Move });
        }
    }

    fn branches(&mut self, then_branch: &Block, else_branch: Option<&Block>) {
        let before = self.state.clone();
        self.block(then_branch);
        let then_state = self.state.clone();
        self.state = before.clone();
        if let Some(else_branch) = else_branch {
            self.block(else_branch);
        }
        self.state = merge_states(then_state, self.state.clone());
    }

    fn block(&mut self, block: &Block) {
        let loans = self.state.loans.len();
        let last_uses = self.last_uses(block);
        for (index, stmt) in block.stmts.iter().enumerate() {
            self.stmt(stmt);
            let mut kept = Vec::new();
            for loan in self.state.loans.drain(loans..) {
                if loan
                    .owner
                    .is_some_and(|owner| last_uses.get(&owner).is_some_and(|last| *last > index))
                {
                    kept.push(loan);
                }
            }
            self.state.loans.extend(kept);
        }
        self.state.loans.truncate(loans);
    }

    fn last_uses(&self, block: &Block) -> HashMap<LocalId, usize> {
        let Some(body) = self.body else {
            return HashMap::new();
        };
        let mut uses = HashMap::new();
        for (index, stmt) in block.stmts.iter().enumerate() {
            for resolution in &body.resolutions {
                if resolution.span.file != stmt.span.file
                    || resolution.span.start < stmt.span.start
                    || resolution.span.end > stmt.span.end
                {
                    continue;
                }
                if let Res::Local(local) = resolution.res {
                    uses.insert(local, index);
                }
            }
        }
        uses
    }

    fn stmt(&mut self, stmt: &Stmt) {
        match &stmt.kind {
            StmtKind::Bind {
                pattern,
                value,
                else_block,
                ..
            } => {
                if let Some(else_block) = else_block {
                    let before = self.state.clone();
                    self.block(else_block);
                    self.state = before;
                }
                self.expr(value, Mode::Move);
                self.pattern_locals(pattern);
                if let ExprKind::Ref { expr: borrowed, .. } = &value.kind {
                    if let Some(place) = self.place_of(borrowed) {
                        for local in pattern_local_ids(self, pattern) {
                            self.state.refs.insert(local, place.clone());
                            for loan in self.state.loans.iter_mut().rev() {
                                if loan.owner.is_none() && loan.place == place {
                                    loan.owner = Some(local);
                                }
                            }
                        }
                    }
                } else if matches!(value.kind, ExprKind::Lambda { .. }) {
                    let locals = pattern_local_ids(self, pattern);
                    for loan in self.state.loans.iter_mut().rev() {
                        if loan.owner.is_none() {
                            if let Some(local) = locals.first() {
                                loan.owner = Some(*local);
                            }
                        }
                    }
                }
            }
            StmtKind::Assign { target, value } => {
                self.expr(value, Mode::Move);
                if let Some(place) = self.place_of(target) {
                    self.assign_place(&place, target.span);
                }
            }
            StmtKind::Expr(expr) => self.expr(expr, Mode::Read),
            StmtKind::While { cond, body } => {
                self.expr(cond, Mode::Read);
                self.block(body);
            }
            StmtKind::For {
                pattern,
                iter,
                body,
            } => {
                self.expr(iter, Mode::Move);
                self.pattern_locals(pattern);
                self.block(body);
            }
            StmtKind::Return(value) => {
                if let Some(value) = value {
                    self.expr(value, Mode::Move);
                    self.check_escape(value);
                }
            }
            StmtKind::Break(value) => {
                if let Some(value) = value {
                    self.expr(value, Mode::Move);
                }
            }
            StmtKind::Continue => {}
        }
    }

    fn check_escape(&mut self, value: &Expr) {
        if let ExprKind::Ref { expr, .. } = &value.kind {
            if let Some(place) = self.place_of(expr) {
                let code = if self.is_method {
                    "PGS-E4104"
                } else {
                    "PGS-E4105"
                };
                self.error(
                    code,
                    "una referencia a un local no puede escapar del scope",
                    value.span,
                );
                let _ = place;
                return;
            }
        }
        if let Some(place) = self.place_of(value) {
            if self.state.refs.contains_key(&place.local) {
                self.error(
                    "PGS-E4105",
                    "una referencia no puede salir como valor de retorno",
                    value.span,
                );
            }
        }
    }

    fn pattern_locals(&mut self, pattern: &Pattern) {
        match &pattern.kind {
            PatternKind::Path(path) if path.len() == 1 => {
                if let Some(local) = self.local_at(pattern.span) {
                    self.state
                        .locals
                        .insert(local, LocalState { initialized: true });
                }
            }
            PatternKind::Bind { pattern, .. } => {
                if let Some(local) = self.local_at(pattern.span) {
                    self.state
                        .locals
                        .insert(local, LocalState { initialized: true });
                }
                self.pattern_locals(pattern);
            }
            PatternKind::Tuple(items) | PatternKind::Slice(items) | PatternKind::Or(items) => {
                for item in items {
                    self.pattern_locals(item);
                }
            }
            PatternKind::Variant { args, named, .. } => {
                for arg in args {
                    self.pattern_locals(arg);
                }
                for (_, pattern) in named {
                    self.pattern_locals(pattern);
                }
            }
            PatternKind::Wildcard
            | PatternKind::Literal(_)
            | PatternKind::Range { .. }
            | PatternKind::Rest
            | PatternKind::Path(_) => {}
        }
    }

    fn is_copy_ast(&self, ty: &pengu_syntax::ast::Type) -> bool {
        use pengu_syntax::ast::TypeKind;
        match &ty.kind {
            TypeKind::Unit => true,
            TypeKind::Option(inner) => self.is_copy_ast(inner),
            TypeKind::Ref { .. } | TypeKind::Slice(_) | TypeKind::Ptr(_) => true,
            TypeKind::Array { elem, .. } => self.is_copy_ast(elem),
            TypeKind::Tuple(items) => items.iter().all(|item| self.is_copy_ast(item)),
            TypeKind::Path { segments, args } => {
                if let Some(name) = segments.last() {
                    match name.as_str() {
                        "Bool" | "Int" | "I8" | "I16" | "I32" | "I64" | "Isize" | "U8" | "U16"
                        | "U32" | "U64" | "Usize" | "Float" | "F32" | "F64" | "Char" | "Str"
                        | "Unit" | "Never" | "CStr" | "Ordering" => return true,
                        "String" | "Vec" | "Map" | "Set" | "Box" | "Rc" | "Arc" | "CString" => {
                            return false;
                        }
                        _ => {}
                    }
                }
                if let Some(Res::Def(def)) = self.res_at(ty.span) {
                    if let Some(adt) = self.krate.adt(def) {
                        return adt.is_copy && args.iter().all(|arg| self.is_copy_ast(arg));
                    }
                }
                false
            }
            TypeKind::Fn { .. } | TypeKind::SelfType => true,
        }
    }

    fn pattern_moves_ast(
        &self,
        pattern: &Pattern,
        base: &Place,
        base_ty: &pengu_syntax::ast::Type,
        out: &mut Vec<Place>,
    ) {
        if self.is_copy_ast(base_ty) {
            return;
        }
        match &pattern.kind {
            PatternKind::Path(path) if path.len() == 1 => {
                if self.local_at(pattern.span).is_some() {
                    out.push(base.clone());
                }
            }
            PatternKind::Bind { .. } => out.push(base.clone()),
            PatternKind::Or(items) => {
                for item in items {
                    self.pattern_moves_ast(item, base, base_ty, out);
                }
            }
            PatternKind::Tuple(items) => {
                if let pengu_syntax::ast::TypeKind::Tuple(tys) = &base_ty.kind {
                    for (index, (item, ty)) in items.iter().zip(tys).enumerate() {
                        let place = base.field(&index.to_string());
                        self.pattern_moves_ast(item, &place, ty, out);
                    }
                }
            }
            PatternKind::Variant { args, named, .. } => {
                if let Some((fields, _is_record, tuple)) = self.variant_fields(pattern) {
                    if tuple {
                        for (index, (arg, field)) in args.iter().zip(&fields).enumerate() {
                            let place = base.field(&index.to_string());
                            self.pattern_moves_ast(arg, &place, &field.ty, out);
                        }
                    } else {
                        for (arg, field) in args.iter().zip(&fields) {
                            let place = base.field(&field.name);
                            self.pattern_moves_ast(arg, &place, &field.ty, out);
                        }
                        for (name, pattern) in named {
                            if let Some(field) = fields.iter().find(|field| &field.name == name) {
                                let place = base.field(&field.name);
                                self.pattern_moves_ast(pattern, &place, &field.ty, out);
                            }
                        }
                    }
                } else {
                    out.push(base.clone());
                }
            }
            PatternKind::Wildcard
            | PatternKind::Literal(_)
            | PatternKind::Range { .. }
            | PatternKind::Rest
            | PatternKind::Slice(_)
            | PatternKind::Path(_) => {}
        }
    }

    fn pattern_moves(&self, pattern: &Pattern, base: &Place, base_ty: &Ty, out: &mut Vec<Place>) {
        match &pattern.kind {
            PatternKind::Path(path) if path.len() == 1 => {
                if self.local_at(pattern.span).is_some() {
                    out.push(base.clone());
                }
            }
            PatternKind::Bind { .. } => out.push(base.clone()),
            PatternKind::Tuple(items) => {
                if let Ty::Tuple(tys) = base_ty {
                    for (index, (item, ty)) in items.iter().zip(tys).enumerate() {
                        let place = base.field(&index.to_string());
                        if !self.is_copy(ty) {
                            self.pattern_moves(item, &place, ty, out);
                        }
                    }
                }
            }
            PatternKind::Variant { args, named, .. } => {
                if let Some((fields, _is_record, tuple)) = self.variant_fields(pattern) {
                    if tuple {
                        for (index, (arg, field)) in args.iter().zip(&fields).enumerate() {
                            let place = base.field(&index.to_string());
                            if !self.is_copy_ast(&field.ty) {
                                self.pattern_moves_ast(arg, &place, &field.ty, out);
                            }
                        }
                    } else {
                        for (arg, field) in args.iter().zip(&fields) {
                            let place = base.field(&field.name);
                            if !self.is_copy_ast(&field.ty) {
                                self.pattern_moves_ast(arg, &place, &field.ty, out);
                            }
                        }
                        for (name, pattern) in named {
                            if let Some(field) = fields.iter().find(|field| &field.name == name) {
                                let place = base.field(&field.name);
                                if !self.is_copy_ast(&field.ty) {
                                    self.pattern_moves_ast(pattern, &place, &field.ty, out);
                                }
                            }
                        }
                    }
                } else {
                    out.push(base.clone());
                }
            }
            PatternKind::Or(items) => {
                for item in items {
                    self.pattern_moves(item, base, base_ty, out);
                }
            }
            PatternKind::Slice(_) => {
                let item = match base_ty {
                    Ty::Array(item, _) | Ty::Slice(item, _) | Ty::Vec(item) => Some(item),
                    _ => None,
                };
                if item.is_none_or(|item| !self.is_copy(item)) {
                    out.push(base.clone());
                }
            }
            PatternKind::Wildcard
            | PatternKind::Literal(_)
            | PatternKind::Range { .. }
            | PatternKind::Rest
            | PatternKind::Path(_) => {}
        }
    }

    fn variant_fields(&self, pattern: &Pattern) -> Option<(Vec<pengu_hir::AdtField>, bool, bool)> {
        let res = self.res_at(pattern.span)?;
        let Res::Def(def) = res else {
            return None;
        };
        if let Some(adt) = self.krate.adt(def) {
            return Some((adt.fields.clone(), true, false));
        }
        let owner = self.krate.variant_owner(def)?;
        let adt = self.krate.adt(owner)?;
        let variant = adt.variants.iter().find(|variant| variant.def == def)?;
        Some((variant.fields.clone(), false, variant.tuple))
    }
}

fn pattern_local_ids(checker: &OwnershipChecker<'_>, pattern: &Pattern) -> Vec<LocalId> {
    let mut ids = Vec::new();
    collect_pattern_locals(checker, pattern, &mut ids);
    ids
}

fn collect_pattern_locals(
    checker: &OwnershipChecker<'_>,
    pattern: &Pattern,
    ids: &mut Vec<LocalId>,
) {
    match &pattern.kind {
        PatternKind::Path(path) if path.len() == 1 => {
            if let Some(local) = checker.local_at(pattern.span) {
                ids.push(local);
            }
        }
        PatternKind::Bind { pattern, .. } => {
            if let Some(local) = checker.local_at(pattern.span) {
                ids.push(local);
            }
            collect_pattern_locals(checker, pattern, ids);
        }
        PatternKind::Tuple(items) | PatternKind::Slice(items) | PatternKind::Or(items) => {
            for item in items {
                collect_pattern_locals(checker, item, ids);
            }
        }
        PatternKind::Variant { args, named, .. } => {
            for arg in args {
                collect_pattern_locals(checker, arg, ids);
            }
            for (_, pattern) in named {
                collect_pattern_locals(checker, pattern, ids);
            }
        }
        PatternKind::Wildcard
        | PatternKind::Literal(_)
        | PatternKind::Range { .. }
        | PatternKind::Rest
        | PatternKind::Path(_) => {}
    }
}

fn merge_states(left: State, right: State) -> State {
    let mut locals = left.locals.clone();
    for (local, state) in right.locals {
        match locals.get_mut(&local) {
            Some(existing) => existing.initialized &= state.initialized,
            None => {
                locals.insert(local, state);
            }
        }
    }
    let mut moved = left.moved;
    moved.extend(right.moved);
    let mut refs = left.refs;
    refs.extend(right.refs);
    State {
        locals,
        moved,
        loans: left.loans,
        refs,
    }
}

fn contains_ref(ty: &pengu_syntax::ast::Type) -> bool {
    use pengu_syntax::ast::TypeKind;
    match &ty.kind {
        TypeKind::Ref { .. } => true,
        TypeKind::Option(inner) | TypeKind::Array { elem: inner, .. } | TypeKind::Slice(inner) => {
            contains_ref(inner)
        }
        TypeKind::Tuple(items) => items.iter().any(contains_ref),
        TypeKind::Path { args, .. } => args.iter().any(contains_ref),
        _ => false,
    }
}
