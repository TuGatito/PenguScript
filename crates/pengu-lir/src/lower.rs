//! Bajada de HIR a LIR explícito (B1: control).

use std::collections::HashMap;

use pengu_diag::Diagnostic;
use pengu_hir::{Body, DefId, DefKind, HirCrate, LocalId, ModuleId, Res};
use pengu_span::Span;
use pengu_syntax::ast::{
    BinOp, Block, Expr, ExprKind, Pattern, PatternKind, Stmt, StmtKind, Type, TypeKind, UnOp,
};
use pengu_types::{CheckResult, Ty};

use crate::lir::{
    BlockId, BuiltinVariant, DestructureTarget, LBinOp, LBlock, LExpr, LFunction, LLocal, LParam,
    LProgram, LStmt, LStringPart, LTerm, LUnOp, LocalIndex, VecAdapterKind,
};

/// Baja todas las funciones con cuerpo del crate.
#[must_use]
pub fn lower_crate(krate: &HirCrate, types: &CheckResult) -> LProgram {
    let mono = crate::mono::plan_monomorphization(krate, types);
    let mut program = LProgram::default();
    program.diagnostics.extend(mono.diagnostics.clone());
    program.instances = mono.instances.clone();
    for body in &krate.bodies {
        let Some(ast) = &body.ast else { continue };
        let def = &krate.defs[body.owner.index()];
        if !matches!(
            def.kind,
            DefKind::Function | DefKind::Impl | DefKind::Module
        ) {
            continue;
        }
        let Some(sig) = krate.signatures.get(&body.owner) else {
            continue;
        };
        if let Some(imp) = krate
            .impls
            .iter()
            .find(|imp| imp.methods.contains(&body.owner) && !imp.generics.is_empty())
        {
            for instance in program.instances.iter().filter(|i| i.def == body.owner) {
                let env = imp
                    .generics
                    .iter()
                    .zip(instance.type_args.iter())
                    .map(|(generic, ty)| (generic.def, ty.clone()))
                    .collect();
                let mut lowerer =
                    FunctionLower::new(krate, types, body, instance.name.clone(), env);
                lowerer.lower(ast);
                if lowerer.diagnostics.is_empty() {
                    program.functions.push(lowerer.finish());
                } else {
                    program.diagnostics.extend(lowerer.diagnostics);
                }
            }
            continue;
        }
        if sig.generics.is_empty() {
            let mut lowerer =
                FunctionLower::new(krate, types, body, def.name.clone(), HashMap::new());
            lowerer.lower(ast);
            if lowerer.diagnostics.is_empty() {
                program.functions.push(lowerer.finish());
            } else {
                program.diagnostics.extend(lowerer.diagnostics);
            }
        } else {
            for instance in program.instances.iter().filter(|i| i.def == body.owner) {
                let env = sig
                    .generics
                    .iter()
                    .zip(instance.type_args.iter())
                    .map(|(generic, ty)| (generic.def, ty.clone()))
                    .collect();
                let mut lowerer =
                    FunctionLower::new(krate, types, body, instance.name.clone(), env);
                lowerer.lower(ast);
                if lowerer.diagnostics.is_empty() {
                    program.functions.push(lowerer.finish());
                } else {
                    program.diagnostics.extend(lowerer.diagnostics);
                }
            }
        }
    }
    program
}

struct LoopCtx {
    break_to: BlockId,
    continue_to: BlockId,
    value: Option<LocalIndex>,
}

struct FunctionLower<'a> {
    krate: &'a HirCrate,
    types: &'a CheckResult,
    body: &'a Body,
    name: String,
    locals: Vec<LLocal>,
    local_map: HashMap<LocalId, LocalIndex>,
    blocks: Vec<LBlock>,
    current: BlockId,
    type_env: HashMap<DefId, Ty>,
    loops: Vec<LoopCtx>,
    diagnostics: Vec<Diagnostic>,
    has_curse: bool,
}

impl<'a> FunctionLower<'a> {
    fn new(
        krate: &'a HirCrate,
        types: &'a CheckResult,
        body: &'a Body,
        name: String,
        type_env: HashMap<DefId, Ty>,
    ) -> Self {
        let mut locals = Vec::new();
        let mut local_map = HashMap::new();
        let body_types = types.locals.get(&body.id);
        for local in &body.locals {
            let index = locals.len();
            local_map.insert(local.id, index);
            locals.push(LLocal {
                id: index,
                name: local.name.clone(),
                mutable: local.mutable,
                ty: body_types
                    .and_then(|map| map.get(&local.id))
                    .cloned()
                    .unwrap_or(Ty::Error),
            });
            if let Some(last) = locals.last_mut() {
                last.ty = subst_ty(&last.ty, &type_env);
            }
        }
        let impl_ty = krate
            .impls
            .iter()
            .find(|imp| imp.methods.contains(&body.owner))
            .map(|imp| {
                ast_type_ty(
                    &imp.ty,
                    &type_env,
                    krate,
                    None,
                    krate.def(body.owner).module,
                )
            });
        let signature = krate.signatures.get(&body.owner);
        if let Some(sig) = signature {
            for (i, param) in body.params.iter().enumerate() {
                let module = krate.def(body.owner).module;
                let ty = sig.params.get(i).map_or(Ty::Error, |ty| {
                    ast_type_ty(ty, &type_env, krate, impl_ty.as_ref(), module)
                });
                if let Some(index) = local_map.get(param).copied() {
                    if let Some(local) = locals.get_mut(index) {
                        local.ty = ty;
                    }
                } else {
                    let index = locals.len();
                    local_map.insert(*param, index);
                    locals.push(LLocal {
                        id: index,
                        name: format!("p{i}"),
                        mutable: false,
                        ty,
                    });
                }
            }
        }
        if let Some(self_local) = body.self_local {
            if let Some(index) = local_map.get(&self_local).copied() {
                if let Some(imp) = krate
                    .impls
                    .iter()
                    .find(|imp| imp.methods.contains(&body.owner))
                {
                    locals[index].ty = ast_type_ty(
                        &imp.ty,
                        &type_env,
                        krate,
                        None,
                        krate.def(body.owner).module,
                    );
                }
            }
        }
        Self {
            krate,
            types,
            body,
            name,
            locals,
            local_map,
            blocks: vec![LBlock {
                id: 0,
                stmts: Vec::new(),
                term: LTerm::Unreachable,
            }],
            current: 0,
            type_env,
            loops: Vec::new(),
            diagnostics: Vec::new(),
            has_curse: false,
        }
    }

    fn lower(&mut self, block: &Block) {
        self.lower_block_to(block, None);
    }

    fn finish(self) -> LFunction {
        let ret = self
            .krate
            .signatures
            .get(&self.body.owner)
            .map_or(Ty::Unit, |sig| self.signature_ret(sig));
        let params = self
            .body
            .params
            .iter()
            .enumerate()
            .map(|(i, local)| {
                let index = self.local_map.get(local).copied().unwrap_or(i);
                LParam {
                    local: index,
                    name: self
                        .locals
                        .get(index)
                        .map_or_else(|| format!("p{i}"), |l| l.name.clone()),
                    ty: self.locals.get(index).map_or(Ty::Error, |l| l.ty.clone()),
                }
            })
            .collect();
        LFunction {
            def: self.body.owner,
            name: self.name,
            params,
            ret,
            locals: self.locals,
            blocks: self.blocks,
            entry: 0,
            has_curse: self.has_curse,
        }
    }

    /// Si el tipo es de usuario y el pacto de operadores existe, devuelve el
    /// pacto y el nombre del método que implementa el operador.
    fn operator_pact(&self, ty: &Ty, pact_name: &str) -> Option<(DefId, String)> {
        if !matches!(ty, Ty::Adt(..)) {
            return None;
        }
        self.krate
            .pacts
            .keys()
            .find(|pact| self.krate.defs[pact.index()].name == pact_name)
            .map(|pact| {
                let method = match pact_name {
                    "Add" => "add",
                    "Sub" => "sub",
                    "Mul" => "mul",
                    "Div" => "div",
                    "Rem" => "rem",
                    _ => "neg",
                };
                (*pact, method.to_owned())
            })
    }

    /// Módulo al que pertenece la función que se está bajando.
    fn module(&self) -> ModuleId {
        self.krate.def(self.body.owner).module
    }

    /// Tipo del `self` del `ritual` al que pertenece esta función, si lo hay.
    fn impl_ty(&self) -> Option<Ty> {
        self.krate
            .impls
            .iter()
            .find(|imp| imp.methods.contains(&self.body.owner))
            .map(|imp| ast_type_ty(&imp.ty, &self.type_env, self.krate, None, self.module()))
    }

    fn signature_ret(&self, sig: &pengu_hir::Signature) -> Ty {
        ast_type_ty(
            &sig.ret,
            &self.type_env,
            self.krate,
            self.impl_ty().as_ref(),
            self.module(),
        )
    }

    fn new_block(&mut self) -> BlockId {
        let id = self.blocks.len();
        self.blocks.push(LBlock {
            id,
            stmts: Vec::new(),
            term: LTerm::Unreachable,
        });
        id
    }

    fn term(&self) -> &LTerm {
        &self.blocks[self.current].term
    }

    fn set_term(&mut self, term: LTerm) {
        self.blocks[self.current].term = term;
    }

    fn lower_block_to(&mut self, block: &Block, target: Option<BlockId>) {
        let ret = self
            .krate
            .signatures
            .get(&self.body.owner)
            .map_or(Ty::Unit, |sig| self.signature_ret(sig));
        if target.is_none() && ret != Ty::Unit && ret != Ty::Never {
            if let Some((last, prefix)) = block.stmts.split_last() {
                if let StmtKind::Expr(expr) = &last.kind {
                    for stmt in prefix {
                        if !matches!(self.term(), LTerm::Unreachable) {
                            break;
                        }
                        self.lower_stmt(stmt);
                    }
                    if matches!(self.term(), LTerm::Unreachable) {
                        // `curse` en posición de cola: el valor del bloque FFI es
                        // el valor de retorno de la función.
                        if let ExprKind::Curse(inner) = &expr.kind {
                            self.has_curse = true;
                            self.lower_block_to(inner, None);
                        } else if let Some(value) = self.lower_expr(expr) {
                            self.set_term(LTerm::Return(Some(value)));
                        }
                    }
                    return;
                }
            }
        }
        for stmt in &block.stmts {
            if !matches!(self.term(), LTerm::Unreachable) {
                break;
            }
            self.lower_stmt(stmt);
        }
        if matches!(self.term(), LTerm::Unreachable) {
            if let Some(target) = target {
                self.set_term(LTerm::Goto(target));
            } else if ret == Ty::Unit || ret == Ty::Never {
                self.set_term(LTerm::Return(None));
            }
        }
    }

    fn lower_stmt(&mut self, stmt: &Stmt) {
        match &stmt.kind {
            StmtKind::Bind { pattern, value, .. } => {
                if let Some(expr) = self.lower_expr(value) {
                    if let Some(local) = self.pattern_local(pattern) {
                        self.blocks[self.current]
                            .stmts
                            .push(LStmt::Let(local, expr, stmt.span));
                    } else if let Some(target) = self.destructure_target(pattern) {
                        self.blocks[self.current]
                            .stmts
                            .push(LStmt::Destructure(expr, target, stmt.span));
                    }
                }
            }
            StmtKind::Assign { target, value } => {
                if let Some(expr) = self.lower_expr(value) {
                    if let Some(local) = self.expr_local(target) {
                        self.blocks[self.current]
                            .stmts
                            .push(LStmt::Assign(local, expr, stmt.span));
                    } else if let ExprKind::Field { base, name } = &target.kind {
                        if let Some(local) = self.expr_local(base) {
                            self.blocks[self.current].stmts.push(LStmt::SetField(
                                local,
                                name.clone(),
                                expr,
                                stmt.span,
                            ));
                        } else {
                            self.error(
                                "PGS-E6007",
                                "destino de asignación no soportado",
                                target.span,
                            );
                        }
                    } else {
                        self.error(
                            "PGS-E6007",
                            "destino de asignación no soportado",
                            target.span,
                        );
                    }
                }
            }
            StmtKind::Expr(expr) => match &expr.kind {
                ExprKind::If {
                    cond,
                    then_branch,
                    else_branch,
                    unless,
                } => self.lower_if(cond, then_branch, else_branch.as_ref(), *unless),
                ExprKind::Loop(body) => self.lower_loop(body, None),
                ExprKind::Do(body) => self.lower_block_to(body, None),
                ExprKind::Curse(body) => {
                    // `curse` como sentencia: su valor se descarta y el flujo
                    // continúa en el bloque siguiente.
                    self.has_curse = true;
                    let after = self.new_block();
                    self.lower_block_to(body, Some(after));
                    self.current = after;
                }
                ExprKind::Match { scrutinee, arms } => self.lower_match(scrutinee, arms, expr.span),
                _ => {
                    if let Some(expr) = self.lower_expr(expr) {
                        self.blocks[self.current]
                            .stmts
                            .push(LStmt::Eval(expr, stmt.span));
                    }
                }
            },
            StmtKind::While { cond, body } => self.lower_while(cond, body),
            StmtKind::For {
                pattern,
                iter,
                body,
            } => self.lower_for(pattern, iter, body, stmt.span),
            StmtKind::Return(value) => {
                let value = value.as_ref().and_then(|e| self.lower_expr(e));
                self.set_term(LTerm::Return(value));
            }
            StmtKind::Break(value) => {
                let Some(ctx) = self.loops.last() else {
                    self.error("PGS-E6005", "`break` fuera de un bucle", stmt.span);
                    return;
                };
                let target = ctx.break_to;
                let value_local = ctx.value;
                if let Some(value) = value {
                    let expr = self.lower_expr(value);
                    if let (Some(local), Some(expr)) = (value_local, expr) {
                        self.blocks[self.current]
                            .stmts
                            .push(LStmt::Assign(local, expr, stmt.span));
                    }
                }
                self.set_term(LTerm::Goto(target));
            }
            StmtKind::Continue => {
                let Some(ctx) = self.loops.last() else {
                    self.error("PGS-E6005", "`continue` fuera de un bucle", stmt.span);
                    return;
                };
                let target = ctx.continue_to;
                self.set_term(LTerm::Goto(target));
            }
        }
    }

    fn lower_if(
        &mut self,
        cond: &Expr,
        then_branch: &Block,
        else_branch: Option<&Block>,
        unless: bool,
    ) {
        let Some(mut condition) = self.lower_expr(cond) else {
            return;
        };
        if unless {
            condition = LExpr::Unary(LUnOp::Not, Box::new(condition));
        }
        let then_id = self.new_block();
        let else_id = self.new_block();
        let join = self.new_block();
        self.set_term(LTerm::If(condition, then_id, else_id));

        self.current = then_id;
        self.lower_block_to(then_branch, Some(join));

        self.current = else_id;
        if let Some(else_branch) = else_branch {
            self.lower_block_to(else_branch, Some(join));
        } else {
            self.set_term(LTerm::Goto(join));
        }
        self.current = join;
    }

    fn lower_while(&mut self, cond: &Expr, body: &Block) {
        let header = self.new_block();
        let body_id = self.new_block();
        let exit = self.new_block();
        self.set_term(LTerm::Goto(header));
        self.current = header;
        if let Some(condition) = self.lower_expr(cond) {
            self.set_term(LTerm::If(condition, body_id, exit));
        } else {
            self.set_term(LTerm::Goto(exit));
        }
        self.current = body_id;
        self.loops.push(LoopCtx {
            break_to: exit,
            continue_to: header,
            value: None,
        });
        self.lower_block_to(body, Some(header));
        self.loops.pop();
        self.current = exit;
    }

    fn lower_loop(&mut self, body: &Block, value: Option<LocalIndex>) {
        let header = self.new_block();
        let body_id = self.new_block();
        let exit = self.new_block();
        self.set_term(LTerm::Goto(header));
        self.current = header;
        self.set_term(LTerm::Goto(body_id));
        self.current = body_id;
        self.loops.push(LoopCtx {
            break_to: exit,
            continue_to: header,
            value,
        });
        self.lower_block_to(body, Some(header));
        self.loops.pop();
        self.current = exit;
    }

    fn new_temp(&mut self, ty: Ty, span: Span) -> LocalIndex {
        let index = self.locals.len();
        self.locals.push(LLocal {
            id: index,
            name: format!("__t{index}"),
            mutable: true,
            ty,
        });
        let _ = span;
        index
    }

    fn expr_ty(&self, span: Span) -> Ty {
        self.types
            .types
            .iter()
            .find(|(candidate, _)| *candidate == span)
            .map_or(Ty::Error, |(_, ty)| subst_ty(ty, &self.type_env))
    }

    fn lower_for(&mut self, pattern: &Pattern, iter: &Expr, body: &Block, span: Span) {
        if !matches!(&iter.kind, ExprKind::Range { end: Some(_), .. }) {
            let Some(value) = self.lower_expr(iter) else {
                return;
            };
            let value = self.clone_place(iter, value);
            let mut iter_ty = self.expr_ty(iter.span);
            // `for x in &values` recorre lo prestado: para clasificar el
            // contenedor se pela el préstamo, pero el temporal conserva el
            // tipo original (en Rust `&[T]` también tiene `len` e índice).
            let borrowed_ty = iter_ty.clone();
            while let Ty::Ref(inner, _) = iter_ty.clone() {
                iter_ty = *inner;
            }
            let mut value = value;
            if let Ty::Set(inner) = &iter_ty {
                let item = (**inner).clone();
                value = LExpr::IntoIter(Box::new(value));
                iter_ty = Ty::Iterator(Box::new(item));
            } else if let Ty::Map(key, val) = &iter_ty {
                let item = Ty::Tuple(vec![(**key).clone(), (**val).clone()]);
                value = LExpr::IntoIter(Box::new(value));
                iter_ty = Ty::Iterator(Box::new(item));
            }
            if let Ty::Iterator(item_ty) = &iter_ty {
                let iter_local = self.new_temp(iter_ty.clone(), span);
                self.blocks[self.current]
                    .stmts
                    .push(LStmt::Let(iter_local, value, span));
                let item_local = self.new_temp((**item_ty).clone(), span);
                let header = self.new_block();
                let body_id = self.new_block();
                let exit = self.new_block();
                self.set_term(LTerm::Goto(header));
                self.current = header;
                self.set_term(LTerm::Next {
                    iter: iter_local,
                    item: item_local,
                    some: body_id,
                    none: exit,
                });
                self.current = body_id;
                self.bind_for_pattern(pattern, LExpr::Local(item_local), span);
                self.loops.push(LoopCtx {
                    break_to: exit,
                    continue_to: header,
                    value: None,
                });
                self.lower_block_to(body, Some(header));
                self.loops.pop();
                self.set_term(LTerm::Goto(header));
                self.current = exit;
                return;
            }
            if matches!(iter_ty, Ty::Vec(_) | Ty::Array(_, _) | Ty::Slice(_, _)) {
                let vec = self.new_temp(borrowed_ty.clone(), span);
                self.blocks[self.current]
                    .stmts
                    .push(LStmt::Let(vec, value, span));

                let index = self.new_temp(Ty::Usize, span);
                self.blocks[self.current]
                    .stmts
                    .push(LStmt::Let(index, LExpr::Int(0), span));
                let header = self.new_block();
                let body_id = self.new_block();
                let step = self.new_block();
                let exit = self.new_block();
                self.set_term(LTerm::Goto(header));
                self.current = header;
                self.set_term(LTerm::If(
                    LExpr::Binary(
                        LBinOp::Lt,
                        Box::new(LExpr::Local(index)),
                        Box::new(LExpr::Method {
                            receiver: Box::new(LExpr::Local(vec)),
                            def: None,
                            name: "len".to_owned(),
                            args: Vec::new(),
                        }),
                    ),
                    body_id,
                    exit,
                ));
                self.current = body_id;
                let element = match &iter_ty {
                    Ty::Vec(inner) | Ty::Array(inner, _) | Ty::Slice(inner, _) => (**inner).clone(),
                    _ => Ty::Error,
                };
                let item = LExpr::Index(Box::new(LExpr::Local(vec)), Box::new(LExpr::Local(index)));
                // `for x in v` copia el elemento: si no es Copy, se clona.
                let item = if is_copy_ty(&element) {
                    item
                } else {
                    LExpr::Method {
                        receiver: Box::new(item),
                        def: None,
                        name: "clone".to_owned(),
                        args: Vec::new(),
                    }
                };
                self.bind_for_pattern(pattern, item, span);
                self.loops.push(LoopCtx {
                    break_to: exit,
                    continue_to: step,
                    value: None,
                });
                self.lower_block_to(body, Some(step));
                self.loops.pop();
                self.current = step;
                self.blocks[self.current].stmts.push(LStmt::Assign(
                    index,
                    LExpr::Binary(
                        LBinOp::Add,
                        Box::new(LExpr::Local(index)),
                        Box::new(LExpr::Int(1)),
                    ),
                    span,
                ));
                self.set_term(LTerm::Goto(header));
                self.current = exit;
                return;
            }
            self.error(
                "PGS-E1901",
                "`for` sobre este tipo aún no se baja a LIR B3d",
                iter.span,
            );
            return;
        }
        let ExprKind::Range {
            start,
            end: Some(end),
            inclusive,
        } = &iter.kind
        else {
            return;
        };
        let Some(start) = self.lower_expr(start) else {
            return;
        };
        let Some(end) = self.lower_expr(end) else {
            return;
        };
        let index = self.new_temp(Ty::Int, span);
        self.blocks[self.current]
            .stmts
            .push(LStmt::Let(index, start, span));
        let header = self.new_block();
        let body_id = self.new_block();
        let step = self.new_block();
        let exit = self.new_block();
        self.set_term(LTerm::Goto(header));
        self.current = header;
        let cmp = if *inclusive { LBinOp::Le } else { LBinOp::Lt };
        self.set_term(LTerm::If(
            LExpr::Binary(cmp, Box::new(LExpr::Local(index)), Box::new(end)),
            body_id,
            exit,
        ));
        self.current = body_id;
        self.bind_for_pattern(pattern, LExpr::Local(index), span);
        self.loops.push(LoopCtx {
            break_to: exit,
            continue_to: step,
            value: None,
        });
        self.lower_block_to(body, Some(step));
        self.loops.pop();
        self.current = step;
        self.blocks[self.current].stmts.push(LStmt::Assign(
            index,
            LExpr::Binary(
                LBinOp::Add,
                Box::new(LExpr::Local(index)),
                Box::new(LExpr::Int(1)),
            ),
            span,
        ));
        self.set_term(LTerm::Goto(header));
        self.current = exit;
    }

    /// Clona un *place* (`campo` o `índice`) que no es `Copy` antes de
    /// consumirlo. Sin esto, `for x in @.items` y `match @.cwd` mueven un campo
    /// que vive detrás de `&self`/`&mut self` y rustc rechaza el Rust emitido
    /// (`E0507`).
    fn clone_place(&self, expr: &Expr, value: LExpr) -> LExpr {
        if is_copy_ty(&self.expr_ty(expr.span)) {
            return value;
        }
        if matches!(&expr.kind, ExprKind::Field { .. } | ExprKind::Index { .. }) {
            return LExpr::Method {
                receiver: Box::new(value),
                def: None,
                name: "clone".to_owned(),
                args: Vec::new(),
            };
        }
        value
    }

    fn lower_match(&mut self, scrutinee: &Expr, arms: &[pengu_syntax::ast::MatchArm], span: Span) {
        let Some(value) = self.lower_expr(scrutinee) else {
            return;
        };
        let value = self.clone_place(scrutinee, value);
        let temp = self.new_temp(self.expr_ty(scrutinee.span), span);
        self.blocks[self.current]
            .stmts
            .push(LStmt::Let(temp, value, span));
        let join = self.new_block();
        for arm in arms {
            let body_id = self.new_block();
            let next = self.new_block();
            let pattern = arm.pattern.as_ref();
            if let Some(pattern) = pattern {
                let cond = self.pattern_condition(pattern, temp);
                self.set_term(LTerm::If(cond, body_id, next));
            } else {
                self.set_term(LTerm::Goto(body_id));
            }
            self.current = body_id;
            // El payload solo se extrae en la rama que ha casado: hacerlo en
            // el bloque de prueba ejecutaría `unreachable!()` en las demás.
            if let Some(pattern) = pattern {
                self.bind_pattern_locals(pattern, temp, span);
            }
            self.lower_block_to(&arm.body, Some(join));
            self.current = next;
        }
        // El checker garantiza que el `match` es exhaustivo, así que el
        // fallthrough tras el último brazo es inalcanzable. Marcarlo como tal
        // evita aristas falsas en la liveness (que exigían valores phi para
        // locales definidos solo en algunos brazos).
        if arms.is_empty() {
            self.set_term(LTerm::Goto(join));
        } else {
            self.set_term(LTerm::Unreachable);
        }
        self.current = join;
    }

    fn lower_match_value(
        &mut self,
        scrutinee: &Expr,
        arms: &[pengu_syntax::ast::MatchArm],
        span: Span,
    ) -> Option<LExpr> {
        let value = self.lower_expr(scrutinee)?;
        let value = self.clone_place(scrutinee, value);
        let scrutinee_local = self.new_temp(self.expr_ty(scrutinee.span), span);
        self.blocks[self.current]
            .stmts
            .push(LStmt::Let(scrutinee_local, value, span));
        let result = self.new_temp(self.expr_ty(span), span);
        let join = self.new_block();
        for arm in arms {
            let body_id = self.new_block();
            let next = self.new_block();
            let pattern = arm.pattern.as_ref();
            if let Some(pattern) = pattern {
                let cond = self.pattern_condition(pattern, scrutinee_local);
                self.set_term(LTerm::If(cond, body_id, next));
            } else {
                self.set_term(LTerm::Goto(body_id));
            }
            self.current = body_id;
            if let Some(pattern) = pattern {
                self.bind_pattern_locals(pattern, scrutinee_local, span);
            }
            self.lower_value_block(&arm.body, result, join);
            self.current = next;
        }
        if arms.is_empty() {
            self.set_term(LTerm::Goto(join));
        } else {
            self.set_term(LTerm::Unreachable);
        }
        self.current = join;
        Some(LExpr::Local(result))
    }

    fn pattern_literal(&mut self, pattern: &Pattern) -> Option<LExpr> {
        if let PatternKind::Literal(expr) = &pattern.kind {
            self.lower_expr(expr)
        } else {
            None
        }
    }

    fn pattern_condition(&mut self, pattern: &Pattern, local: LocalIndex) -> LExpr {
        match &pattern.kind {
            PatternKind::Wildcard => LExpr::Bool(true),
            PatternKind::Path(_) | PatternKind::Bind { .. } => {
                if let Some(Res::Primitive(primitive)) = self.resolution_at(pattern.span) {
                    if matches!(
                        primitive,
                        pengu_hir::Primitive::OrderingLess
                            | pengu_hir::Primitive::OrderingEqual
                            | pengu_hir::Primitive::OrderingGreater
                    ) {
                        return LExpr::Binary(
                            LBinOp::Eq,
                            Box::new(LExpr::Local(local)),
                            Box::new(LExpr::Primitive(
                                primitive_name(primitive).to_owned(),
                                Vec::new(),
                            )),
                        );
                    }
                }
                if let Some(kind) = self.builtin_pattern_variant(pattern) {
                    if matches!(
                        kind,
                        BuiltinVariant::Some | BuiltinVariant::Ok | BuiltinVariant::Err
                    ) {
                        LExpr::IsBuiltin(Box::new(LExpr::Local(local)), kind)
                    } else {
                        LExpr::Bool(false)
                    }
                } else if let Some(variant) = self.pattern_variant_def(pattern) {
                    LExpr::IsVariant(Box::new(LExpr::Local(local)), variant)
                } else if self.pattern_local(pattern).is_some() {
                    LExpr::Bool(true)
                } else {
                    LExpr::Bool(false)
                }
            }
            PatternKind::Variant { .. } => {
                if let Some(kind) = self.builtin_pattern_variant(pattern) {
                    LExpr::IsBuiltin(Box::new(LExpr::Local(local)), kind)
                } else if let Some(variant) = self.pattern_variant_def(pattern) {
                    LExpr::IsVariant(Box::new(LExpr::Local(local)), variant)
                } else {
                    LExpr::Bool(false)
                }
            }
            PatternKind::Literal(expr) => {
                let Some(value) = self.lower_expr(expr) else {
                    return LExpr::Bool(false);
                };
                LExpr::Binary(LBinOp::Eq, Box::new(LExpr::Local(local)), Box::new(value))
            }
            PatternKind::Range {
                start,
                end,
                inclusive,
            } => {
                let lower = self.pattern_literal(start).unwrap_or(LExpr::Int(0));
                let upper = end
                    .as_deref()
                    .and_then(|pattern| self.pattern_literal(pattern))
                    .unwrap_or(LExpr::Int(0));
                let ge = LExpr::Binary(LBinOp::Ge, Box::new(LExpr::Local(local)), Box::new(lower));
                let cmp = if *inclusive { LBinOp::Le } else { LBinOp::Lt };
                let le = LExpr::Binary(cmp, Box::new(LExpr::Local(local)), Box::new(upper));
                LExpr::Binary(LBinOp::And, Box::new(ge), Box::new(le))
            }
            PatternKind::Or(patterns) => patterns
                .iter()
                .map(|p| self.pattern_condition(p, local))
                .reduce(|a, b| LExpr::Binary(LBinOp::Or, Box::new(a), Box::new(b)))
                .unwrap_or(LExpr::Bool(false)),
            _ => LExpr::Bool(false),
        }
    }

    fn bind_pattern_locals(&mut self, pattern: &Pattern, value: LocalIndex, span: Span) {
        self.bind_pattern_expr(pattern, LExpr::Local(value), span);
    }

    fn bind_pattern_expr(&mut self, pattern: &Pattern, expr: LExpr, span: Span) {
        if let Some(local) = self.pattern_local(pattern) {
            self.blocks[self.current]
                .stmts
                .push(LStmt::Assign(local, expr.clone(), span));
        }
        match &pattern.kind {
            PatternKind::Bind { pattern, .. } => {
                self.bind_pattern_expr(pattern, expr, span);
            }
            PatternKind::Variant { args, named, .. } => {
                if let Some(kind) = self.builtin_pattern_variant(pattern) {
                    if let Some(first) = args.first() {
                        let field = LExpr::BuiltinField(Box::new(expr.clone()), kind);
                        self.bind_pattern_expr(first, field, span);
                    }
                    return;
                }
                let Some(variant) = self.pattern_variant_def(pattern) else {
                    return;
                };
                for (index, arg) in args.iter().enumerate() {
                    let field = LExpr::VariantField(
                        Box::new(expr.clone()),
                        variant,
                        u32::try_from(index).unwrap_or(u32::MAX),
                    );
                    self.bind_pattern_expr(arg, field, span);
                }
                for (name, arg) in named {
                    let Some(field_index) = self.variant_field_index(variant, name) else {
                        continue;
                    };
                    let field = LExpr::VariantField(Box::new(expr.clone()), variant, field_index);
                    self.bind_pattern_expr(arg, field, span);
                }
            }
            _ => {}
        }
    }

    /// Variante integrada (`Some`/`Ok`/`Err`) de un patrón, si lo es.
    fn builtin_pattern_variant(&self, pattern: &Pattern) -> Option<BuiltinVariant> {
        let PatternKind::Variant { path, .. } = &pattern.kind else {
            return None;
        };
        let name = path.last()?;
        match (name.as_str(), self.resolution_at(pattern.span)) {
            (_, Some(Res::Primitive(pengu_hir::Primitive::Some))) | ("some", _) => {
                Some(BuiltinVariant::Some)
            }
            (_, Some(Res::Primitive(pengu_hir::Primitive::Ok))) | ("ok", _) => {
                Some(BuiltinVariant::Ok)
            }
            (_, Some(Res::Primitive(pengu_hir::Primitive::Err))) | ("err", _) => {
                Some(BuiltinVariant::Err)
            }
            _ => None,
        }
    }

    fn pattern_variant_def(&self, pattern: &Pattern) -> Option<DefId> {
        if !matches!(
            pattern.kind,
            PatternKind::Variant { .. } | PatternKind::Path(_)
        ) {
            return None;
        }
        match self.resolution_at(pattern.span) {
            Some(Res::Def(def)) if self.krate.variant_owners.contains_key(&def) => Some(def),
            _ => None,
        }
    }

    fn variant_field_index(&self, variant: DefId, name: &str) -> Option<u32> {
        let owner = self.krate.variant_owner(variant)?;
        let adt = self.krate.adt(owner)?;
        let variant_def = adt
            .variants
            .iter()
            .find(|candidate| candidate.def == variant)?;
        variant_def
            .fields
            .iter()
            .position(|field| field.name == name)
            .and_then(|index| u32::try_from(index).ok())
    }

    fn lower_if_value(
        &mut self,
        cond: &Expr,
        then_branch: &Block,
        else_branch: Option<&Block>,
        unless: bool,
        span: Span,
    ) -> Option<LExpr> {
        let mut condition = self.lower_expr(cond)?;
        if unless {
            condition = LExpr::Unary(LUnOp::Not, Box::new(condition));
        }
        let temp = self.new_temp(self.expr_ty(span), span);
        let then_id = self.new_block();
        let else_id = self.new_block();
        let join = self.new_block();
        self.set_term(LTerm::If(condition, then_id, else_id));
        self.current = then_id;
        self.lower_value_block(then_branch, temp, join);
        self.current = else_id;
        if let Some(else_branch) = else_branch {
            self.lower_value_block(else_branch, temp, join);
        } else {
            self.blocks[self.current]
                .stmts
                .push(LStmt::Assign(temp, LExpr::Unit, span));
            self.set_term(LTerm::Goto(join));
        }
        self.current = join;
        Some(LExpr::Local(temp))
    }

    fn lower_value_block(&mut self, block: &Block, temp: LocalIndex, join: BlockId) {
        if let Some((last, prefix)) = block.stmts.split_last() {
            for stmt in prefix {
                if !matches!(self.term(), LTerm::Unreachable) {
                    break;
                }
                self.lower_stmt(stmt);
            }
            if let StmtKind::Expr(expr) = &last.kind {
                if let Some(value) = self.lower_expr(expr) {
                    self.blocks[self.current]
                        .stmts
                        .push(LStmt::Assign(temp, value, last.span));
                }
            } else {
                self.lower_stmt(last);
            }
        }
        if matches!(self.term(), LTerm::Unreachable) {
            self.set_term(LTerm::Goto(join));
        }
    }

    fn resolve_method_def(&self, ty: &Ty, name: &str) -> Option<DefId> {
        let key = match ty {
            Ty::Adt(def, _) => self.krate.defs[def.index()].name.clone(),
            Ty::Bool => "Bool".to_owned(),
            Ty::Int | Ty::I32 | Ty::IntVar(_) => "Int".to_owned(),
            Ty::I8 => "I8".to_owned(),
            Ty::I16 => "I16".to_owned(),
            Ty::I64 => "I64".to_owned(),
            Ty::Isize => "Isize".to_owned(),
            Ty::U8 => "U8".to_owned(),
            Ty::U16 => "U16".to_owned(),
            Ty::U32 => "U32".to_owned(),
            Ty::U64 => "U64".to_owned(),
            Ty::Usize => "Usize".to_owned(),
            Ty::Float | Ty::F64 | Ty::FloatVar(_) => "Float".to_owned(),
            Ty::F32 => "F32".to_owned(),
            Ty::Char => "Char".to_owned(),
            Ty::Str => "Str".to_owned(),
            Ty::String => "String".to_owned(),
            Ty::Vec(_) => "Vec".to_owned(),
            Ty::Map(_, _) => "Map".to_owned(),
            Ty::Set(_) => "Set".to_owned(),
            _ => return None,
        };
        self.krate
            .methods
            .get(&key)?
            .iter()
            .copied()
            .find(|def| self.krate.defs[def.index()].name == name)
    }

    /// Baja una expresión y materializa la conversión `Str`↔`String` que el
    /// checker aceptó para este span (A4).
    fn lower_expr(&mut self, expr: &Expr) -> Option<LExpr> {
        let value = self.lower_expr_raw(expr)?;
        Some(self.apply_string_coercion(expr.span, value))
    }

    fn apply_string_coercion(&self, span: Span, value: LExpr) -> LExpr {
        let Some(coercion) = self.types.coercions.get(&span) else {
            return value;
        };
        let name = match coercion {
            pengu_types::Coercion::StrToString => "to_string",
            pengu_types::Coercion::StringToStr => "as_str",
        };
        LExpr::Method {
            receiver: Box::new(value),
            def: None,
            name: name.to_string(),
            args: Vec::new(),
        }
    }

    fn lower_expr_raw(&mut self, expr: &Expr) -> Option<LExpr> {
        match &expr.kind {
            ExprKind::Unit => Some(LExpr::Unit),
            ExprKind::Bool(value) => Some(LExpr::Bool(*value)),
            ExprKind::Int(raw) => Some(LExpr::Int(parse_int(raw))),
            ExprKind::Float(raw) => Some(LExpr::Float(parse_float(raw))),
            ExprKind::String(lit) => {
                let mut parts = Vec::new();
                let mut interpolated = false;
                for part in &lit.parts {
                    match part {
                        pengu_syntax::ast::StringPart::Text(value) => {
                            parts.push(LStringPart::Text(value.clone()));
                        }
                        pengu_syntax::ast::StringPart::Expr(inner) => {
                            interpolated = true;
                            let expr = self.lower_expr(inner)?;
                            parts.push(LStringPart::Expr(expr));
                        }
                    }
                }
                if interpolated {
                    Some(LExpr::Interpolate(parts))
                } else {
                    Some(LExpr::Str(
                        parts
                            .into_iter()
                            .filter_map(|part| match part {
                                LStringPart::Text(text) => Some(text),
                                LStringPart::Expr(_) => None,
                            })
                            .collect(),
                    ))
                }
            }
            ExprKind::None => Some(LExpr::Primitive("none".to_owned(), Vec::new())),
            ExprKind::SelfValue => self
                .body
                .self_local
                .and_then(|local| self.local_map.get(&local).copied())
                .map(LExpr::Local)
                .or_else(|| {
                    self.error("PGS-E4109", "`@` fuera de un método", expr.span);
                    None
                }),
            ExprKind::Path(_) => self.resolution_at(expr.span).and_then(|res| match res {
                Res::Local(local) => self.local_map.get(&local).copied().map(LExpr::Local),
                Res::Primitive(primitive) => Some(LExpr::Primitive(
                    primitive_name(primitive).to_owned(),
                    Vec::new(),
                )),
                Res::Def(def) if self.krate.variant_owner(def).is_some() => {
                    Some(LExpr::Variant(def, None))
                }
                Res::Def(def) if self.krate.def(def).kind == DefKind::Function => {
                    Some(LExpr::FuncRef(def))
                }
                Res::Def(def)
                    if matches!(self.krate.def(def).kind, DefKind::Const | DefKind::Static) =>
                {
                    Some(LExpr::ConstRef(def))
                }
                _ => {
                    self.error("PGS-E1901", "path no soportado en LIR", expr.span);
                    None
                }
            }),
            ExprKind::Unary { op, expr: inner } => {
                let inner_ty = self.expr_ty(inner.span);
                let lowered = self.lower_expr(inner)?;
                if matches!(op, UnOp::Neg) {
                    if let Some((pact, method)) = self.operator_pact(&inner_ty, "Neg") {
                        return Some(LExpr::TraitCall {
                            pact,
                            method,
                            args: vec![lowered],
                        });
                    }
                }
                Some(LExpr::Unary(un_op(*op), Box::new(lowered)))
            }
            ExprKind::Binary { op, lhs, rhs } => {
                let left = self.lower_expr(lhs)?;
                let right = self.lower_expr(rhs)?;
                let lhs_ty = self.expr_ty(lhs.span);
                let pact_name = match op {
                    BinOp::Add => Some("Add"),
                    BinOp::Sub => Some("Sub"),
                    BinOp::Mul => Some("Mul"),
                    BinOp::Div => Some("Div"),
                    BinOp::Rem => Some("Rem"),
                    _ => None,
                };
                if let Some((pact, method)) =
                    pact_name.and_then(|name| self.operator_pact(&lhs_ty, name))
                {
                    return Some(LExpr::TraitCall {
                        pact,
                        method,
                        args: vec![left, right],
                    });
                }
                Some(LExpr::Binary(bin_op(*op), Box::new(left), Box::new(right)))
            }
            ExprKind::Tuple(items) => {
                let items = items
                    .iter()
                    .map(|e| self.lower_expr(e))
                    .collect::<Option<_>>()?;
                Some(LExpr::Tuple(items))
            }
            ExprKind::Char(raw) | ExprKind::ByteChar(raw) => {
                if matches!(expr.kind, ExprKind::Char(_)) {
                    Some(LExpr::Char(raw.clone()))
                } else {
                    Some(LExpr::ByteChar(raw.clone()))
                }
            }
            ExprKind::Record { path, fields, base } => {
                let def = match self.resolution_at(expr.span) {
                    Some(Res::Def(def)) => Some(def),
                    _ => None,
                };
                let fields = fields
                    .iter()
                    .map(|(name, value)| self.lower_expr(value).map(|value| (name.clone(), value)))
                    .collect::<Option<_>>()?;
                let base = match base {
                    Some(base) => Some(Box::new(self.lower_expr(base)?)),
                    None => None,
                };
                Some(LExpr::Record {
                    def,
                    path: path.clone(),
                    fields,
                    base,
                })
            }
            ExprKind::Array(items) => Some(LExpr::Array(
                items
                    .iter()
                    .map(|item| self.lower_expr(item))
                    .collect::<Option<_>>()?,
            )),
            ExprKind::ArrayRepeat { value, count } => {
                let count = match &count.kind {
                    ExprKind::Int(raw) => parse_int(raw).try_into().unwrap_or(0),
                    _ => 0,
                };
                Some(LExpr::ArrayRepeat(Box::new(self.lower_expr(value)?), count))
            }
            ExprKind::Vector(items) => Some(LExpr::Vector(
                items
                    .iter()
                    .map(|item| self.lower_expr(item))
                    .collect::<Option<_>>()?,
            )),
            ExprKind::Map(entries) => Some(LExpr::Map(
                entries
                    .iter()
                    .map(|(key, value)| Some((self.lower_expr(key)?, self.lower_expr(value)?)))
                    .collect::<Option<_>>()?,
            )),
            ExprKind::Set(items) => Some(LExpr::Set(
                items
                    .iter()
                    .map(|item| self.lower_expr(item))
                    .collect::<Option<_>>()?,
            )),
            ExprKind::Cast { expr: inner, ty } => Some(LExpr::Cast(
                Box::new(self.lower_expr(inner)?),
                ast_type_ty(
                    ty,
                    &self.type_env,
                    self.krate,
                    self.impl_ty().as_ref(),
                    self.module(),
                ),
            )),
            ExprKind::Field { base, name } => {
                if let Some(Res::Def(def)) = self.resolution_at(expr.span) {
                    if self.krate.variant_owner(def).is_some() {
                        return Some(LExpr::Variant(def, None));
                    }
                }
                if let Some(def) = self.assoc_const(base, name) {
                    return Some(LExpr::ConstRef(def));
                }
                Some(LExpr::Field(Box::new(self.lower_expr(base)?), name.clone()))
            }
            ExprKind::Index { base, index } => Some(LExpr::Index(
                Box::new(self.lower_expr(base)?),
                Box::new(self.lower_expr(index)?),
            )),
            ExprKind::Try(inner) => Some(LExpr::Try(Box::new(self.lower_expr(inner)?))),
            ExprKind::Ref {
                mutable,
                expr: inner,
            } => Some(LExpr::Ref(*mutable, Box::new(self.lower_expr(inner)?))),
            ExprKind::Range {
                start,
                end,
                inclusive,
            } => Some(LExpr::Range(
                Box::new(self.lower_expr(start)?),
                match end {
                    Some(end) => Some(Box::new(self.lower_expr(end)?)),
                    None => None,
                },
                *inclusive,
            )),
            ExprKind::If {
                cond,
                then_branch,
                else_branch,
                unless,
            } => self.lower_if_value(cond, then_branch, else_branch.as_ref(), *unless, expr.span),
            ExprKind::Match { scrutinee, arms } => {
                self.lower_match_value(scrutinee, arms, expr.span)
            }
            ExprKind::Loop(body) => {
                let temp = self.new_temp(self.expr_ty(expr.span), expr.span);
                self.lower_loop(body, Some(temp));
                Some(LExpr::Local(temp))
            }
            ExprKind::Curse(body) => {
                // `curse` en posición de valor: se baja como un bloque que deja
                // su resultado en un temporal, igual que un `if` de valor.
                self.has_curse = true;
                let temp = self.new_temp(self.expr_ty(expr.span), expr.span);
                let join = self.new_block();
                self.lower_value_block(body, temp, join);
                self.current = join;
                Some(LExpr::Local(temp))
            }
            ExprKind::Lambda { params, body } => {
                let fn_ty = self.expr_ty(expr.span);
                let (param_tys, ret) = match fn_ty {
                    Ty::Fn(params, ret) => (params, *ret),
                    _ => (
                        params
                            .iter()
                            .map(|param| {
                                ast_type_ty(
                                    &param.ty,
                                    &self.type_env,
                                    self.krate,
                                    self.impl_ty().as_ref(),
                                    self.module(),
                                )
                            })
                            .collect(),
                        Ty::Unit,
                    ),
                };
                let params: Vec<(String, Ty)> = params
                    .iter()
                    .zip(param_tys)
                    .map(|(param, ty)| (param.name.clone(), ty))
                    .collect();
                let mut captures = Vec::new();
                let mut seen = std::collections::HashSet::new();
                for resolution in &self.body.resolutions {
                    if resolution.span.start < expr.span.start
                        || resolution.span.end > expr.span.end
                    {
                        continue;
                    }
                    let Res::Local(local) = resolution.res else {
                        continue;
                    };
                    let Some(index) = self.local_map.get(&local).copied() else {
                        continue;
                    };
                    let Some(name) = self
                        .body
                        .locals
                        .iter()
                        .find(|candidate| candidate.id == local)
                        .map(|candidate| candidate.name.clone())
                    else {
                        continue;
                    };
                    if params.iter().any(|(param, _)| *param == name) || !seen.insert(name.clone())
                    {
                        continue;
                    }
                    captures.push((name, index));
                }
                Some(LExpr::Closure {
                    params,
                    ret,
                    body: Box::new(body.clone()),
                    captures,
                })
            }
            ExprKind::Call { callee, args } => {
                if matches!(callee.kind, ExprKind::Lambda { .. }) {
                    let callee = self.lower_expr(callee)?;
                    let args = args
                        .iter()
                        .map(|e| self.lower_expr(e))
                        .collect::<Option<_>>()?;
                    return Some(LExpr::ClosureCall(Box::new(callee), args));
                }
                if let Some(res) = self.resolution_at(callee.span) {
                    if matches!(res, Res::Local(_))
                        && matches!(self.expr_ty(callee.span), Ty::Fn(_, _))
                    {
                        let callee = self.lower_expr(callee)?;
                        let args = args
                            .iter()
                            .map(|e| self.lower_expr(e))
                            .collect::<Option<_>>()?;
                        return Some(LExpr::ClosureCall(Box::new(callee), args));
                    }
                }
                // `CString.new(text)`: constructor del núcleo.
                if let ExprKind::Field { base, name } = &callee.kind {
                    if name == "new"
                        && matches!(
                            &base.kind,
                            ExprKind::Path(path) if path.last().is_some_and(|last| last == "CString")
                        )
                        && args.len() == 1
                    {
                        let arg = self.lower_expr(&args[0])?;
                        return Some(LExpr::CStringNew(Box::new(arg)));
                    }
                }
                // `modulo.funcion(args)`: función de otro módulo.
                if let ExprKind::Field { .. } = &callee.kind {
                    if let Some(Res::Def(def)) = self.resolution_at(callee.span) {
                        if self.krate.def(def).kind == DefKind::Function
                            && self
                                .krate
                                .signature(def)
                                .is_some_and(|sig| sig.receiver.is_none())
                        {
                            let args = args
                                .iter()
                                .map(|e| self.lower_expr(e))
                                .collect::<Option<_>>()?;
                            return Some(LExpr::Call(def, Vec::new(), args));
                        }
                    }
                }
                // `Tipo.metodo(args)`: función asociada de un `ritual`.
                if let ExprKind::Field { base, name } = &callee.kind {
                    if let ExprKind::Path(path) = &base.kind {
                        if let Some(type_name) = path.last() {
                            let is_type = match self.resolution_at(base.span) {
                                Some(Res::Def(owner)) => {
                                    self.krate.def(owner).kind == DefKind::Type
                                }
                                Some(Res::Primitive(_)) => true,
                                _ => matches!(
                                    path[0].as_str(),
                                    "Vec"
                                        | "Map"
                                        | "Set"
                                        | "Option"
                                        | "Result"
                                        | "Box"
                                        | "Rc"
                                        | "Arc"
                                ),
                            };
                            if is_type {
                                if let Some(def) =
                                    self.krate.methods.get(type_name).and_then(|defs| {
                                        defs.iter().copied().find(|def| {
                                            self.krate.def(*def).name == *name
                                                && self
                                                    .krate
                                                    .signature(*def)
                                                    .is_some_and(|sig| sig.receiver.is_none())
                                        })
                                    })
                                {
                                    let args = args
                                        .iter()
                                        .map(|e| self.lower_expr(e))
                                        .collect::<Option<_>>()?;
                                    return Some(LExpr::Call(def, Vec::new(), args));
                                }
                            }
                        }
                    }
                }
                let (base, type_expr) = match &callee.kind {
                    ExprKind::Index { base, index } => (base.as_ref(), Some(index.as_ref())),
                    _ => (callee.as_ref(), None),
                };
                let resolution = self
                    .resolution_at(base.span)
                    .or_else(|| self.resolution_at(callee.span));
                let args = args
                    .iter()
                    .map(|e| self.lower_expr(e))
                    .collect::<Option<_>>()?;
                if let ExprKind::Field { base, name } = &callee.kind {
                    if let Some(receiver) = self.lower_expr(base) {
                        let base_ty = self.expr_ty(base.span);
                        if matches!(base_ty, Ty::Vec(_) | Ty::Map(_, _) | Ty::Set(_)) {
                            if name == "iter" {
                                return Some(LExpr::IterCloned(Box::new(receiver)));
                            }
                            if name == "into_iter" {
                                return Some(LExpr::IntoIter(Box::new(receiver)));
                            }
                        }
                        if base_ty == Ty::Str {
                            let kind = match name.as_str() {
                                "chars" => Some(VecAdapterKind::StrChars),
                                "bytes" => Some(VecAdapterKind::StrBytes),
                                "char_indices" => Some(VecAdapterKind::StrCharIndices),
                                _ => None,
                            };
                            if let Some(kind) = kind {
                                return Some(LExpr::VecAdapter {
                                    kind,
                                    base: Box::new(receiver),
                                    args,
                                    ty: Some(self.expr_ty(expr.span)),
                                });
                            }
                        }
                        if matches!(base_ty, Ty::Vec(_) | Ty::Iterator(_)) {
                            let kind = match name.as_str() {
                                "map" => Some(VecAdapterKind::Map),
                                "filter" => Some(VecAdapterKind::Filter),
                                "fold" => Some(VecAdapterKind::Fold),
                                "collect" => Some(VecAdapterKind::Collect),
                                "count" => Some(VecAdapterKind::Count),
                                "last" => Some(VecAdapterKind::Last),
                                "nth" => Some(VecAdapterKind::Nth),
                                "sum" => Some(VecAdapterKind::Sum),
                                "min" => Some(VecAdapterKind::Min),
                                "max" => Some(VecAdapterKind::Max),
                                "any" => Some(VecAdapterKind::Any),
                                "all" => Some(VecAdapterKind::All),
                                "find" => Some(VecAdapterKind::Find),
                                "position" => Some(VecAdapterKind::Position),
                                "take" => Some(VecAdapterKind::Take),
                                "skip" => Some(VecAdapterKind::Skip),
                                "step_by" => Some(VecAdapterKind::StepBy),
                                "rev" => Some(VecAdapterKind::Rev),
                                "enumerate" => Some(VecAdapterKind::Enumerate),
                                "zip" => Some(VecAdapterKind::Zip),
                                "filter_map" => Some(VecAdapterKind::FilterMap),
                                "flat_map" => Some(VecAdapterKind::FlatMap),
                                "flatten" => Some(VecAdapterKind::Flatten),
                                "chain" => Some(VecAdapterKind::Chain),
                                "take_while" => Some(VecAdapterKind::TakeWhile),
                                "skip_while" => Some(VecAdapterKind::SkipWhile),
                                "reduce" => Some(VecAdapterKind::Reduce),
                                "product" => Some(VecAdapterKind::Product),
                                "for_each" => Some(VecAdapterKind::ForEach),
                                "inspect" => Some(VecAdapterKind::Inspect),
                                "fuse" => Some(VecAdapterKind::Fuse),
                                "max_by" => Some(VecAdapterKind::MaxBy),
                                "min_by" => Some(VecAdapterKind::MinBy),
                                _ => None,
                            };
                            // Los adaptadores que consumen (`sum`, `min`, `count`, …)
                            // solo existen sobre `Iterator`: sobre `Vec` hay métodos
                            // declarados en `std/capsa.pengu`.
                            let kind = if matches!(base_ty, Ty::Iterator(_)) {
                                kind
                            } else {
                                kind.filter(|kind| {
                                    matches!(
                                        kind,
                                        VecAdapterKind::Map
                                            | VecAdapterKind::Filter
                                            | VecAdapterKind::Fold
                                            | VecAdapterKind::Collect
                                            | VecAdapterKind::Any
                                            | VecAdapterKind::All
                                            | VecAdapterKind::Find
                                            | VecAdapterKind::Position
                                            | VecAdapterKind::FilterMap
                                            | VecAdapterKind::FlatMap
                                            | VecAdapterKind::Flatten
                                            | VecAdapterKind::Chain
                                            | VecAdapterKind::TakeWhile
                                            | VecAdapterKind::SkipWhile
                                            | VecAdapterKind::Inspect
                                            | VecAdapterKind::Fuse
                                    )
                                })
                            };
                            if let Some(kind) = kind {
                                let base = if matches!(base_ty, Ty::Vec(_))
                                    && matches!(
                                        kind,
                                        VecAdapterKind::Map
                                            | VecAdapterKind::Filter
                                            | VecAdapterKind::Any
                                            | VecAdapterKind::All
                                            | VecAdapterKind::Find
                                            | VecAdapterKind::Position
                                            | VecAdapterKind::FilterMap
                                            | VecAdapterKind::FlatMap
                                            | VecAdapterKind::Flatten
                                            | VecAdapterKind::Chain
                                            | VecAdapterKind::TakeWhile
                                            | VecAdapterKind::SkipWhile
                                            | VecAdapterKind::Inspect
                                            | VecAdapterKind::Fuse
                                    ) {
                                    LExpr::IterCloned(Box::new(receiver))
                                } else {
                                    receiver
                                };
                                return Some(LExpr::VecAdapter {
                                    kind,
                                    base: Box::new(base),
                                    args,
                                    ty: Some(self.expr_ty(expr.span)),
                                });
                            }
                        }
                        let def = self.resolve_method_def(&base_ty, name);
                        return Some(LExpr::Method {
                            receiver: Box::new(receiver),
                            def,
                            name: name.clone(),
                            args,
                        });
                    }
                }
                match resolution {
                    Some(Res::Primitive(primitive)) => {
                        Some(LExpr::Primitive(primitive_name(primitive).to_owned(), args))
                    }
                    Some(Res::Def(def)) if self.krate.variant_owner(def).is_some() => {
                        Some(LExpr::Variant(def, Some(args)))
                    }
                    Some(Res::Def(def)) => {
                        if self.krate.impls.iter().any(|imp| {
                            !imp.generics.is_empty()
                                && imp.methods.contains(&def)
                                && self
                                    .krate
                                    .signature(def)
                                    .is_some_and(|signature| signature.receiver.is_none())
                        }) {
                            self.error(
                                "PGS-E1305",
                                "las funciones asociadas de un `ritual` genérico no están soportadas; usa una función libre (N62)",
                                callee.span,
                            );
                            return None;
                        }
                        let mut type_args = type_expr
                            .map(|expr| self.type_arg_ty(expr))
                            .unwrap_or_default();
                        if type_args.is_empty() {
                            // El checker anota la instanciación que infirió para la
                            // llamada; el mono la necesita para bajar el genérico.
                            if let Some(inferred) = self.types.instantiations.get(&expr.span) {
                                type_args = inferred.clone();
                            }
                        }
                        if type_args.is_empty() {
                            // Función asociada de un `impl` genérico: el tipo del
                            // resultado (p. ej. `Pila[String]`) da la instancia.
                            let impl_generics = self
                                .krate
                                .impls
                                .iter()
                                .find(|imp| imp.methods.contains(&def))
                                .map_or(0, |imp| imp.generics.len());
                            if impl_generics > 0 {
                                if let Ty::Adt(_, args) = self.expr_ty(expr.span) {
                                    if args.len() == impl_generics {
                                        type_args = args;
                                    }
                                }
                            }
                        }
                        if let Some(sig) = self.krate.signatures.get(&def) {
                            if !sig.generics.is_empty() && type_args.len() != sig.generics.len() {
                                self.error(
                                    "PGS-E1305",
                                    "no se puede inferir la instancia genérica; usa turbofish",
                                    callee.span,
                                );
                                None
                            } else {
                                Some(LExpr::Call(def, type_args, args))
                            }
                        } else {
                            Some(LExpr::Call(def, type_args, args))
                        }
                    }
                    _ => {
                        self.error("PGS-E1901", "callee no resuelto", callee.span);
                        None
                    }
                }
            }
            _ => {
                self.error("PGS-E1901", "expresión no soportada en LIR B1", expr.span);
                None
            }
        }
    }

    fn type_arg_ty(&self, expr: &Expr) -> Vec<Ty> {
        let ExprKind::Path(segments) = &expr.kind else {
            return Vec::new();
        };
        if segments.len() != 1 {
            return Vec::new();
        }
        let name = &segments[0];
        if let Some((_, ty)) = self
            .type_env
            .iter()
            .find(|(def, _)| self.krate.defs[def.index()].name == *name)
        {
            return vec![ty.clone()];
        }
        if let Some(ty) = primitive_ty(name) {
            return vec![ty];
        }
        Vec::new()
    }

    /// `Tipo.CONST`: constante asociada de un `ritual`.
    fn assoc_const(&self, base: &Expr, name: &str) -> Option<DefId> {
        let ExprKind::Path(path) = &base.kind else {
            return None;
        };
        if path.len() != 1 {
            return None;
        }
        let is_type = match self.resolution_at(base.span) {
            Some(Res::Def(def)) => self.krate.def(def).kind == DefKind::Type,
            Some(Res::Primitive(_)) => true,
            None => primitive_ty(&path[0]).is_some(),
            _ => false,
        };
        if !is_type {
            return None;
        }
        self.krate
            .assoc_consts
            .get(&path[0])?
            .iter()
            .copied()
            .find(|def| self.krate.def(*def).name == name)
    }

    fn resolution_at(&self, span: Span) -> Option<Res> {
        self.body
            .resolutions
            .iter()
            .find(|resolution| resolution.span == span)
            .map(|resolution| resolution.res)
    }

    fn expr_local(&self, expr: &Expr) -> Option<LocalIndex> {
        match &expr.kind {
            ExprKind::SelfValue => self
                .body
                .self_local
                .and_then(|local| self.local_map.get(&local).copied()),
            ExprKind::Path(_) => self.resolution_at(expr.span).and_then(|res| match res {
                Res::Local(local) => self.local_map.get(&local).copied(),
                _ => None,
            }),
            _ => None,
        }
    }

    fn bind_for_pattern(&mut self, pattern: &Pattern, value: LExpr, span: Span) {
        match &pattern.kind {
            PatternKind::Wildcard => {}
            PatternKind::Path(_) | PatternKind::Bind { .. } => {
                if let Some(local) = self.pattern_local(pattern) {
                    self.blocks[self.current]
                        .stmts
                        .push(LStmt::Assign(local, value, span));
                } else {
                    self.error("PGS-E1901", "patrón de `for` sin local", span);
                }
            }
            PatternKind::Tuple(items) => {
                if matches!(value, LExpr::Local(_)) || self.destructure_target(pattern).is_some() {
                    match self.destructure_target(pattern) {
                        Some(target) => {
                            self.blocks[self.current].stmts.push(LStmt::Destructure(
                                value.clone(),
                                target,
                                span,
                            ));
                        }
                        None => {
                            self.error("PGS-E1901", "patrón de `for` no soportado", span);
                        }
                    }
                } else {
                    for (index, item) in items.iter().enumerate() {
                        let field = LExpr::Field(Box::new(value.clone()), index.to_string());
                        self.bind_for_pattern(item, field, span);
                    }
                }
            }
            _ => self.error("PGS-E1901", "patrón de `for` no soportado en LIR", span),
        }
    }

    fn destructure_target(&self, pattern: &Pattern) -> Option<DestructureTarget> {
        match &pattern.kind {
            PatternKind::Wildcard => Some(DestructureTarget::Ignore),
            PatternKind::Path(_) | PatternKind::Bind { .. } => {
                self.pattern_local(pattern).map(DestructureTarget::Local)
            }
            PatternKind::Tuple(items) => {
                let mut targets = Vec::with_capacity(items.len());
                for item in items {
                    targets.push(self.destructure_target(item)?);
                }
                Some(DestructureTarget::Tuple(targets))
            }
            _ => None,
        }
    }

    fn pattern_local(&self, pattern: &Pattern) -> Option<LocalIndex> {
        match &pattern.kind {
            PatternKind::Path(_) | PatternKind::Bind { .. } => {
                self.resolution_at(pattern.span).and_then(|res| match res {
                    Res::Local(local) => self.local_map.get(&local).copied(),
                    _ => None,
                })
            }
            _ => None,
        }
    }

    fn error(&mut self, code: &'static str, message: &str, span: Span) {
        self.diagnostics
            .push(Diagnostic::error(code, message, span));
    }
}

fn primitive_ty(name: &str) -> Option<Ty> {
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
        "Unit" => Ty::Unit,
        "Never" => Ty::Never,
        "CStr" => Ty::CStr,
        "CString" => Ty::CString,
        "Ordering" => Ty::Ordering,
        _ => return None,
    })
}

fn ast_type_ty(
    ty: &Type,
    env: &HashMap<DefId, Ty>,
    krate: &HirCrate,
    self_ty: Option<&Ty>,
    module: ModuleId,
) -> Ty {
    match &ty.kind {
        TypeKind::Unit => Ty::Unit,
        TypeKind::Option(inner) => {
            Ty::Option(Box::new(ast_type_ty(inner, env, krate, self_ty, module)))
        }
        TypeKind::Ref { mutable, inner } => {
            // `Str` ya es una vista prestada (`&str`): `&Str` se normaliza a
            // `Str` para que las firmas del doc (`(s: &Str)`) coincidan con
            // los literales de string y con `ty_rust`.
            if matches!(&inner.kind, TypeKind::Path { segments, args } if args.is_empty()
                && segments.last().is_some_and(|name| name == "Str"))
            {
                return Ty::Str;
            }
            if matches!(&inner.kind, TypeKind::Path { segments, args } if args.is_empty()
                && segments.last().is_some_and(|name| name == "CStr"))
            {
                return Ty::CStr;
            }
            // `[T]` ya es una vista prestada (`&[T]`): igual que `Str`.
            if let TypeKind::Slice(elem) = &inner.kind {
                return Ty::Slice(
                    Box::new(ast_type_ty(elem, env, krate, self_ty, module)),
                    *mutable,
                );
            }
            Ty::Ref(
                Box::new(ast_type_ty(inner, env, krate, self_ty, module)),
                *mutable,
            )
        }
        TypeKind::Array { elem, len } => {
            let n = match &len.kind {
                ExprKind::Int(text) => parse_int(text).try_into().unwrap_or(0),
                _ => 0,
            };
            Ty::Array(Box::new(ast_type_ty(elem, env, krate, self_ty, module)), n)
        }
        TypeKind::Slice(inner) => Ty::Slice(
            Box::new(ast_type_ty(inner, env, krate, self_ty, module)),
            false,
        ),
        TypeKind::Tuple(items) => Ty::Tuple(
            items
                .iter()
                .map(|t| ast_type_ty(t, env, krate, self_ty, module))
                .collect(),
        ),
        TypeKind::Path { segments, args } => {
            let name = segments.last().map(String::as_str).unwrap_or("");
            if let [name] = segments.as_slice() {
                for (def, ty) in env {
                    if krate.defs.get(def.index()).is_some_and(|d| d.name == *name) {
                        return ty.clone();
                    }
                }
                if let Some(ty) = primitive_ty(name) {
                    return ty;
                }
            }
            let args = args
                .iter()
                .map(|arg| ast_type_ty(arg, env, krate, self_ty, module))
                .collect::<Vec<_>>();
            match (name, args.as_slice()) {
                ("Vec", [inner]) => Ty::Vec(Box::new(inner.clone())),
                ("Option", [inner]) => Ty::Option(Box::new(inner.clone())),
                ("Set", [inner]) => Ty::Set(Box::new(inner.clone())),
                ("Box", [inner]) => Ty::Box(Box::new(inner.clone())),
                ("Rc", [inner]) => Ty::Rc(Box::new(inner.clone())),
                ("Arc", [inner]) => Ty::Arc(Box::new(inner.clone())),
                ("Map", [key, value]) => Ty::Map(Box::new(key.clone()), Box::new(value.clone())),
                ("Result", [ok, err]) => Ty::Result(Box::new(ok.clone()), Box::new(err.clone())),
                ("Range", [inner]) => Ty::Range(Box::new(inner.clone())),
                ("Ordering", []) => Ty::Ordering,
                ("CStr", []) => Ty::CStr,
                ("CString", []) => Ty::CString,
                _ => lookup_crate_type(krate, module, name)
                    .map_or(Ty::Error, |def| Ty::Adt(def, args)),
            }
        }
        TypeKind::Ptr(inner) => Ty::Ptr(Box::new(ast_type_ty(inner, env, krate, self_ty, module))),
        TypeKind::Fn { params, ret } => Ty::Fn(
            params
                .iter()
                .map(|t| ast_type_ty(t, env, krate, self_ty, module))
                .collect(),
            Box::new(ast_type_ty(ret, env, krate, self_ty, module)),
        ),
        TypeKind::SelfType => self_ty.cloned().unwrap_or(Ty::Error),
    }
}

/// Resuelve un tipo por nombre en el módulo dado y sus ancestros.
///
/// El nombre de un tipo solo es único dentro de su módulo: dos módulos
/// hermanos pueden declarar `IoError` y cada uno debe ver el suyo.
fn lookup_crate_type(krate: &HirCrate, module: ModuleId, name: &str) -> Option<DefId> {
    let mut current = Some(module);
    while let Some(id) = current {
        let scope = &krate.scopes[krate.modules[id.index()].scope.index()];
        if let Some(binding) = scope.types.get(name) {
            if let Res::Def(def) = binding.res {
                if krate.def(def).kind == DefKind::Type {
                    return Some(def);
                }
            }
        }
        current = krate.modules[id.index()].parent;
    }
    None
}

fn subst_ty(ty: &Ty, env: &HashMap<DefId, Ty>) -> Ty {
    match ty {
        Ty::Generic(def) => env.get(def).cloned().unwrap_or_else(|| ty.clone()),
        Ty::Tuple(items) => Ty::Tuple(items.iter().map(|t| subst_ty(t, env)).collect()),
        Ty::Array(inner, n) => Ty::Array(Box::new(subst_ty(inner, env)), *n),
        Ty::Slice(inner, mutable) => Ty::Slice(Box::new(subst_ty(inner, env)), *mutable),
        Ty::Ref(inner, mutable) => Ty::Ref(Box::new(subst_ty(inner, env)), *mutable),
        Ty::Ptr(inner) => Ty::Ptr(Box::new(subst_ty(inner, env))),
        Ty::Vec(inner) => Ty::Vec(Box::new(subst_ty(inner, env))),
        Ty::Map(k, v) => Ty::Map(Box::new(subst_ty(k, env)), Box::new(subst_ty(v, env))),
        Ty::Set(inner) => Ty::Set(Box::new(subst_ty(inner, env))),
        Ty::Option(inner) => Ty::Option(Box::new(subst_ty(inner, env))),
        Ty::Result(ok, err) => {
            Ty::Result(Box::new(subst_ty(ok, env)), Box::new(subst_ty(err, env)))
        }
        Ty::Box(inner) => Ty::Box(Box::new(subst_ty(inner, env))),
        Ty::Rc(inner) => Ty::Rc(Box::new(subst_ty(inner, env))),
        Ty::Arc(inner) => Ty::Arc(Box::new(subst_ty(inner, env))),
        Ty::Adt(def, args) => Ty::Adt(*def, args.iter().map(|t| subst_ty(t, env)).collect()),
        Ty::Fn(params, ret) => Ty::Fn(
            params.iter().map(|t| subst_ty(t, env)).collect(),
            Box::new(subst_ty(ret, env)),
        ),
        Ty::Range(inner) => Ty::Range(Box::new(subst_ty(inner, env))),
        Ty::Iterator(inner) => Ty::Iterator(Box::new(subst_ty(inner, env))),
        _ => ty.clone(),
    }
}

/// Quita el sufijo de tipo de un literal numérico (`41_u64` → `41`).
fn strip_numeric_suffix(raw: &str) -> &str {
    if let Some((digits, suffix)) = raw.rsplit_once('_') {
        if matches!(
            suffix,
            "i8" | "i16"
                | "i32"
                | "i64"
                | "i128"
                | "isize"
                | "u8"
                | "u16"
                | "u32"
                | "u64"
                | "u128"
                | "usize"
                | "f32"
                | "f64"
        ) {
            return digits;
        }
    }
    raw
}

fn parse_int(raw: &str) -> i64 {
    let raw = strip_numeric_suffix(raw.trim_end_matches(|c: char| c.is_ascii_alphabetic()));
    let cleaned = raw.replace('_', "");
    if let Some(hex) = cleaned.strip_prefix("0x") {
        i64::from_str_radix(hex, 16).unwrap_or(0)
    } else if let Some(oct) = cleaned.strip_prefix("0o") {
        i64::from_str_radix(oct, 8).unwrap_or(0)
    } else if let Some(bin) = cleaned.strip_prefix("0b") {
        i64::from_str_radix(bin, 2).unwrap_or(0)
    } else {
        cleaned.parse().unwrap_or(0)
    }
}

fn is_copy_ty(ty: &Ty) -> bool {
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
        | Ty::Ref(_, _)
        | Ty::Unit
        | Ty::Never => true,
        Ty::Tuple(items) => items.iter().all(is_copy_ty),
        Ty::Array(inner, _) => is_copy_ty(inner),
        _ => false,
    }
}

fn parse_float(raw: &str) -> f64 {
    let cleaned = strip_numeric_suffix(raw.trim_end_matches(|c: char| c.is_ascii_alphabetic()))
        .replace('_', "");
    cleaned.parse().unwrap_or(0.0)
}

const fn primitive_name(primitive: pengu_hir::Primitive) -> &'static str {
    use pengu_hir::Primitive;
    match primitive {
        Primitive::Print => "print",
        Primitive::Format => "format",
        Primitive::Assert => "assert",
        Primitive::Panic => "panic",
        Primitive::AssertEq => "assert_eq",
        Primitive::AssertNe => "assert_ne",
        Primitive::Some => "some",
        Primitive::None => "none",
        Primitive::Ok => "ok",
        Primitive::Err => "err",
        Primitive::OrderingLess => "ordering_less",
        Primitive::OrderingEqual => "ordering_equal",
        Primitive::OrderingGreater => "ordering_greater",
        _ => "primitive",
    }
}

fn bin_op(op: BinOp) -> LBinOp {
    match op {
        BinOp::Add => LBinOp::Add,
        BinOp::Sub => LBinOp::Sub,
        BinOp::Mul => LBinOp::Mul,
        BinOp::Div => LBinOp::Div,
        BinOp::Rem => LBinOp::Rem,
        BinOp::Eq | BinOp::Is => LBinOp::Eq,
        BinOp::Ne | BinOp::Isnt => LBinOp::Ne,
        BinOp::Lt => LBinOp::Lt,
        BinOp::Le => LBinOp::Le,
        BinOp::Gt => LBinOp::Gt,
        BinOp::Ge => LBinOp::Ge,
        BinOp::And => LBinOp::And,
        BinOp::Or => LBinOp::Or,
        BinOp::Range | BinOp::RangeInclusive | BinOp::In => LBinOp::Eq,
    }
}

const fn un_op(op: UnOp) -> LUnOp {
    match op {
        UnOp::Neg => LUnOp::Neg,
        UnOp::Not => LUnOp::Not,
    }
}
