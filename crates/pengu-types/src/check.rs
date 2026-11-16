//! Checker de tipos e inferencia local (C2).

use std::collections::{HashMap, HashSet};

use pengu_diag::Diagnostic;
use pengu_hir::{
    AdtDef, AdtField, AdtKind, AdtVariant, Body, BodyId, DefId, DefKind, GenericParam, HirCrate,
    LocalId, ModuleId, Primitive, Res, Signature,
};
use pengu_span::Span;
use pengu_syntax::StringKind;
use pengu_syntax::ast::{
    BinOp, Block, Expr, ExprKind, MatchArm, Param, Pattern, PatternKind, Receiver, Stmt, StmtKind,
    StringLit, StringPart, Type, TypeKind, UnOp,
};

use crate::ty::Ty;
use crate::unify::Infer;

/// Resultado del checker de C2.
#[derive(Clone, Debug, Default)]
pub struct CheckResult {
    /// Diagnósticos de tipos.
    pub diagnostics: Vec<Diagnostic>,
    /// Tipo final de cada expresión comprobada.
    pub types: Vec<(Span, Ty)>,
    /// Tipos de los locales de cada cuerpo.
    pub locals: std::collections::HashMap<BodyId, std::collections::HashMap<LocalId, Ty>>,
    /// Conversiones `Str` ↔ `String` que el LIR debe materializar (A4).
    pub coercions: std::collections::HashMap<Span, Coercion>,
    /// Instanciación inferida de cada llamada a una función genérica.
    pub instantiations: std::collections::HashMap<Span, Vec<Ty>>,
}

/// Conversión implícita entre `Str` y `String` en contextos de valor.
///
/// El checker acepta el par y anota aquí qué hay que emitir; el LIR la
/// materializa (`to_string()` o `as_str()`) al bajar la expresión.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Coercion {
    /// Se esperaba `String` y llegó un `Str` (literal o préstamo).
    StrToString,
    /// Se esperaba `Str`/`&Str` y llegó un `String`.
    StringToStr,
}

impl CheckResult {
    /// `true` si no hubo errores.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        !self.diagnostics.iter().any(Diagnostic::is_error)
    }
}

/// Comprueba tipos de todos los cuerpos con AST del crate.
#[must_use]
pub fn check_crate(krate: &HirCrate) -> CheckResult {
    let mut checker = Checker::new(krate);
    checker.run();
    checker.finish()
}

struct Checker<'a> {
    krate: &'a HirCrate,
    infer: Infer,
    diagnostics: Vec<Diagnostic>,
    types: Vec<(Span, Ty)>,
    resolutions: HashMap<Span, Res>,
    locals: HashMap<LocalId, Ty>,
    return_ty: Ty,
    self_ty: Ty,
    break_tys: Vec<Ty>,
    loop_value: Vec<bool>,
    int_literals: Vec<(Span, i128)>,
    coercions: std::collections::HashMap<Span, Coercion>,
    instantiations: std::collections::HashMap<Span, Vec<Ty>>,
    negated_literals: std::collections::HashSet<Span>,
    extra_resolutions: HashMap<Span, Res>,
    body_locals: std::collections::HashMap<BodyId, std::collections::HashMap<LocalId, Ty>>,
    generic_env: HashMap<DefId, Ty>,
    in_curse: bool,
    curse_used: bool,
    nul_checked: usize,
    current_module: Option<ModuleId>,
    used_locals: HashSet<LocalId>,
}

impl<'a> Checker<'a> {
    fn new(krate: &'a HirCrate) -> Self {
        let mut resolutions = HashMap::new();
        for body in &krate.bodies {
            for resolution in &body.resolutions {
                resolutions.insert(resolution.span, resolution.res);
            }
        }
        Self {
            krate,
            infer: Infer::default(),
            diagnostics: Vec::new(),
            types: Vec::new(),
            resolutions,
            locals: HashMap::new(),
            return_ty: Ty::Unit,
            self_ty: Ty::Error,
            break_tys: Vec::new(),
            loop_value: Vec::new(),
            int_literals: Vec::new(),
            coercions: std::collections::HashMap::new(),
            instantiations: std::collections::HashMap::new(),
            negated_literals: std::collections::HashSet::new(),
            extra_resolutions: HashMap::new(),
            body_locals: std::collections::HashMap::new(),
            generic_env: HashMap::new(),
            in_curse: false,
            curse_used: false,
            nul_checked: 0,
            current_module: None,
            used_locals: HashSet::new(),
        }
    }

    fn run(&mut self) {
        self.check_derives();
        self.check_consts();
        self.check_impls();
        self.check_unused_generics();
        for body in &self.krate.bodies {
            let Some(ast) = &body.ast else {
                continue;
            };
            let Some(signature) = self.krate.signature(body.owner) else {
                continue;
            };
            self.check_body(body, ast, signature);
        }
    }

    fn check_unused_generics(&mut self) {
        let mut diagnostics = Vec::new();
        for (def, signature) in &self.krate.signatures {
            for generic in &signature.generics {
                let used = signature
                    .params
                    .iter()
                    .any(|ty| type_mentions(ty, &generic.name))
                    || type_mentions(&signature.ret, &generic.name);
                if !used {
                    diagnostics.push((*def, format!("el genérico `{}` no se usa", generic.name)));
                }
            }
        }
        for (def, message) in diagnostics {
            self.error("PGS-E1301", message, self.krate.def(def).span);
        }
    }

    fn check_consts(&mut self) {
        let constants: Vec<(DefId, pengu_hir::ConstDef)> = self
            .krate
            .consts
            .iter()
            .map(|(def, constant)| (*def, constant.clone()))
            .collect();
        for (def, constant) in constants {
            let declared = self.ty_from_ast(&constant.ty);
            let Some(value) = &constant.value else {
                continue;
            };
            self.locals.clear();
            self.return_ty = Ty::Unit;
            let actual = self.check_expr(value);
            if !matches!(actual, Ty::Error) {
                let _ = self.unify_at(declared, actual, constant.ty.span, "PGS-E3001");
            }
            if !is_const_expr(value) {
                self.error(
                    "PGS-E1107",
                    "`sigil` requiere una expresión constante",
                    value.span,
                );
            }
            if has_const_div_zero(value) {
                self.error("PGS-E1403", "división por cero constante", value.span);
            }
            let _ = def;
        }
    }

    fn adt_by_name(&self, name: &str) -> Option<&AdtDef> {
        self.krate
            .adts
            .values()
            .find(|adt| self.krate.def(adt.def).name == name)
    }

    fn check_derives(&mut self) {
        const KNOWN: &[&str] = &[
            "Debug",
            "Clone",
            "Copy",
            "PartialEq",
            "Eq",
            "PartialOrd",
            "Ord",
            "Hash",
            "Default",
        ];
        for adt in self.krate.adts.values() {
            let has = |name: &str| adt.derives.iter().any(|d| d == name);
            let span = self.krate.def(adt.def).span;
            for derive in &adt.derives {
                if !KNOWN.contains(&derive.as_str()) {
                    self.error("PGS-E8006", format!("`@@derive({derive})` no existe"), span);
                }
            }
            if has("Default") && adt.kind == AdtKind::Sum {
                self.error(
                    "PGS-E8007",
                    "`Default` no se puede derivar en un `enchanting`",
                    span,
                );
            }
            if has("Copy") && !has("Clone") {
                self.error(
                    "PGS-E8007",
                    "`Copy` requiere `Clone` en el mismo `@@derive`",
                    span,
                );
            }
            let fields = if adt.kind == AdtKind::Record {
                adt.fields.iter().map(|f| &f.ty).collect::<Vec<_>>()
            } else {
                adt.variants
                    .iter()
                    .flat_map(|v| v.fields.iter().map(|f| &f.ty))
                    .collect::<Vec<_>>()
            };
            if has("Copy") && !fields.iter().all(|ty| self.is_copy_ast(ty)) {
                self.error(
                    "PGS-E8007",
                    "`Copy` requiere que todos los campos sean `Copy`",
                    span,
                );
            }
            if has("Default") && !fields.iter().all(|ty| self.is_default_ast(ty)) {
                self.error(
                    "PGS-E8007",
                    "`Default` requiere que todos los campos tengan valor por defecto",
                    span,
                );
            }
            if (has("Eq") || has("Ord") || has("Hash"))
                && fields.iter().any(|ty| self.has_float_ast(ty))
            {
                self.error(
                    "PGS-E8007",
                    "`Eq`, `Ord` y `Hash` no se pueden derivar con campos `Float`",
                    span,
                );
            }
            if has("Ord") && !has("Eq") {
                self.error(
                    "PGS-E8007",
                    "`Ord` requiere `Eq` en el mismo `@@derive`",
                    span,
                );
            }
        }
    }

    fn has_float_ast(&self, ty: &Type) -> bool {
        match &ty.kind {
            TypeKind::Path { segments, args } => {
                let name = segments.last().map(String::as_str).unwrap_or("");
                matches!(name, "Float" | "F32" | "F64")
                    || args.iter().any(|arg| self.has_float_ast(arg))
            }
            TypeKind::Tuple(items) => items.iter().any(|item| self.has_float_ast(item)),
            TypeKind::Array { elem, .. } | TypeKind::Slice(elem) => self.has_float_ast(elem),
            TypeKind::Ref { inner, .. } | TypeKind::Ptr(inner) => self.has_float_ast(inner),
            TypeKind::Fn { params, ret } => {
                params.iter().any(|p| self.has_float_ast(p)) || self.has_float_ast(ret)
            }
            _ => false,
        }
    }

    fn is_copy_ast(&self, ty: &Type) -> bool {
        match &ty.kind {
            TypeKind::Unit => true,
            TypeKind::Path { segments, args } => {
                let name = segments.last().map(String::as_str).unwrap_or("");
                if matches!(
                    name,
                    "Bool"
                        | "Int"
                        | "I8"
                        | "I16"
                        | "I32"
                        | "I64"
                        | "Isize"
                        | "U8"
                        | "U16"
                        | "U32"
                        | "UInt"
                        | "U64"
                        | "Usize"
                        | "Float"
                        | "F32"
                        | "F64"
                        | "Char"
                        | "Str"
                ) {
                    return true;
                }
                if args.iter().any(|arg| !self.is_copy_ast(arg)) {
                    return false;
                }
                self.adt_by_name(name).is_some_and(|adt| adt.is_copy)
            }
            TypeKind::Tuple(items) => items.iter().all(|item| self.is_copy_ast(item)),
            TypeKind::Array { elem, .. } | TypeKind::Slice(elem) => self.is_copy_ast(elem),
            TypeKind::Ref { .. } | TypeKind::Ptr(_) => true,
            TypeKind::Fn { .. } => true,
            _ => false,
        }
    }

    fn is_default_ast(&self, ty: &Type) -> bool {
        matches!(
            &ty.kind,
            TypeKind::Unit | TypeKind::Path { .. } | TypeKind::Tuple(_) | TypeKind::Array { .. }
        )
    }

    fn check_borrowed_field_returns(&mut self) {
        for imp in &self.krate.impls {
            for method in &imp.methods {
                let Some(sig) = self.krate.signature(*method).cloned() else {
                    continue;
                };
                if matches!(sig.receiver, Some(Receiver::Own)) {
                    continue;
                }
                let Some(body) = self
                    .krate
                    .bodies
                    .iter()
                    .find(|body| body.owner == *method)
                    .and_then(|body| body.ast.as_ref())
                else {
                    continue;
                };
                let Some(StmtKind::Expr(expr)) = body.stmts.last().map(|stmt| &stmt.kind) else {
                    continue;
                };
                let ExprKind::Field { base, .. } = &expr.kind else {
                    continue;
                };
                if !matches!(base.kind, ExprKind::SelfValue) {
                    continue;
                }
                if self.is_copy_ast(&sig.ret) {
                    continue;
                }
                self.error(
                    "PGS-E4105",
                    "un método `@`/`@mut` que devuelve un campo no-`Copy` debe usar `@own`",
                    expr.span,
                );
            }
        }
    }

    fn check_impls(&mut self) {
        self.check_borrowed_field_returns();
        let mut seen: HashSet<(String, DefId)> = HashSet::new();
        for imp in &self.krate.impls {
            let Some(pact_def) = imp.pact else {
                continue;
            };
            let Some(pact) = self.krate.pacts.get(&pact_def) else {
                continue;
            };
            let self_name = type_path_name(&imp.ty).unwrap_or("<tipo>").to_owned();
            if is_forbidden_operator(&self.krate.def(pact_def).name) {
                self.error(
                    "PGS-E1406",
                    format!(
                        "el operador `{}` no se puede sobrecargar",
                        self.krate.def(pact_def).name
                    ),
                    imp.ty.span,
                );
                continue;
            }
            if !seen.insert((self_name.clone(), pact_def)) {
                self.error(
                    "PGS-E1206",
                    format!(
                        "implementación solapada de `{}`",
                        self.krate.def(pact_def).name
                    ),
                    imp.ty.span,
                );
            }
            for required in &pact.methods {
                let required_name = &self.krate.def(*required).name;
                let Some(actual) = imp
                    .methods
                    .iter()
                    .find(|method| self.krate.def(**method).name == *required_name)
                else {
                    self.error(
                        "PGS-E1201",
                        format!(
                            "falta el método `{required_name}` del pact `{}`",
                            self.krate.def(pact_def).name
                        ),
                        imp.ty.span,
                    );
                    continue;
                };
                let Some(expected_sig) = self.krate.signature(*required) else {
                    continue;
                };
                let Some(actual_sig) = self.krate.signature(*actual) else {
                    continue;
                };
                if !signature_matches(expected_sig, actual_sig, &self_name) {
                    let code = if is_operator_pact(&self.krate.def(pact_def).name) {
                        "PGS-E1407"
                    } else {
                        "PGS-E1202"
                    };
                    self.error(
                        code,
                        format!("la firma de `{required_name}` no coincide con el pact"),
                        self.krate.def(*actual).span,
                    );
                }
            }
        }
    }

    fn check_body(&mut self, body: &Body, ast: &Block, signature: &Signature) {
        self.in_curse = self.krate.curse_fns.contains(&body.owner);
        self.curse_used = false;
        self.current_module = Some(self.krate.def(body.owner).module);
        self.locals.clear();
        self.used_locals.clear();
        let previous_env = std::mem::take(&mut self.generic_env);
        for generic in &signature.generics {
            self.generic_env
                .insert(generic.def, Ty::Generic(generic.def));
        }
        self.self_ty = body.self_ty.map_or(Ty::Error, |res| self.res_ty(res));
        self.return_ty = self.ty_from_ast(&signature.ret);

        for (index, local) in body.params.iter().enumerate() {
            if let Some(param_ty) = signature.params.get(index) {
                let ty = self.ty_from_ast(param_ty);
                self.locals.insert(*local, ty);
            }
        }
        let block_ty = self.check_block(ast);
        if self.in_curse && !self.curse_used {
            self.error(
                "PGS-E1607",
                "`curse` solo se permite en la frontera FFI",
                ast.span,
            );
        }
        // El valor de un `curse` al final del cuerpo se descarta cuando la
        // función devuelve `Unit` (ejemplo normativo de FFI en §16.5).
        let tail_is_curse = ast.stmts.last().is_some_and(|stmt| {
            matches!(&stmt.kind, StmtKind::Expr(expr) if matches!(expr.kind, ExprKind::Curse(_)))
        });
        if !(tail_is_curse && matches!(self.infer.resolve(self.return_ty.clone()), Ty::Unit)) {
            let expected = self.return_ty.clone();
            // La conversión se anota en el span de la expresión final, que es
            // el que el LIR vuelve a ver al bajar el bloque.
            let tail_span = ast
                .stmts
                .last()
                .filter(|stmt| matches!(stmt.kind, StmtKind::Expr(_)))
                .map_or(ast.span, |stmt| match &stmt.kind {
                    StmtKind::Expr(expr) => expr.span,
                    _ => ast.span,
                });
            let tail_place = ast.stmts.last().is_some_and(|stmt| {
                matches!(
                    &stmt.kind,
                    StmtKind::Expr(Expr {
                        kind: ExprKind::Path(_) | ExprKind::Field { .. } | ExprKind::Index { .. },
                        ..
                    })
                )
            });
            if self
                .coerce_strings(&expected, &block_ty, tail_span, tail_place)
                .is_none()
            {
                let _ = self.unify_at(expected, block_ty, ast.span, "PGS-E7002");
            }
        }
        for local in &body.locals {
            if body.self_local == Some(local.id) {
                continue;
            }
            if !body.params.contains(&local.id) && !self.used_locals.contains(&local.id) {
                self.warning(
                    "PGS-W1101",
                    format!("el binding `{}` no se usa", local.name),
                    local.span,
                );
            }
        }
        let locals = self
            .locals
            .iter()
            .map(|(id, ty)| (*id, self.infer.apply_defaults(ty.clone())))
            .collect();
        self.body_locals.insert(body.id, locals);
        self.generic_env = previous_env;
    }

    fn finish(mut self) -> CheckResult {
        self.diagnostics.sort_by_key(|diagnostic| {
            (
                diagnostic.primary.file.raw(),
                diagnostic.primary.start,
                diagnostic.primary.end,
                diagnostic.severity,
                diagnostic.code,
            )
        });
        let all_types = std::mem::take(&mut self.types);
        let mut types = Vec::with_capacity(all_types.len());
        for (span, ty) in all_types {
            let ty = self.infer.apply_defaults(ty);
            if let Some((code, message)) = self.unresolved_option_result(&ty) {
                self.diagnostics
                    .push(Diagnostic::error(code, message, span));
            } else if self.infer.has_unresolved(ty.clone()) {
                self.diagnostics.push(Diagnostic::error(
                    "PGS-E3002",
                    "no se puede inferir el tipo de la expresión",
                    span,
                ));
            }
            types.push((span, ty));
        }
        for (span, value) in &self.int_literals {
            if let Some((_, ty)) = types.iter().find(|(candidate, _)| candidate == span) {
                if let Some((min, max)) = integer_range(ty) {
                    if *value < min || *value > max {
                        self.diagnostics.push(Diagnostic::error(
                            "PGS-E3001",
                            format!("el literal `{value}` no cabe en `{ty}`"),
                            *span,
                        ));
                    }
                }
            }
        }
        CheckResult {
            diagnostics: self.diagnostics,
            types,
            locals: std::mem::take(&mut self.body_locals),
            coercions: std::mem::take(&mut self.coercions),
            instantiations: std::mem::take(&mut self.instantiations),
        }
    }

    fn unresolved_option_result(&mut self, ty: &Ty) -> Option<(&'static str, &'static str)> {
        match self.infer.resolve(ty.clone()) {
            Ty::Option(inner) => {
                if self.infer.has_unresolved(*inner) {
                    Some(("PGS-E1508", "no se puede inferir el tipo de `none`"))
                } else {
                    None
                }
            }
            Ty::Result(ok, _) => {
                if self.infer.has_unresolved(*ok) {
                    Some(("PGS-E1507", "no se puede inferir el tipo de éxito de `err`"))
                } else {
                    None
                }
            }
            _ => None,
        }
    }

    fn error(&mut self, code: &'static str, message: impl Into<String>, span: Span) {
        self.diagnostics
            .push(Diagnostic::error(code, message, span));
    }

    fn warning(&mut self, code: &'static str, message: impl Into<String>, span: Span) {
        self.diagnostics
            .push(Diagnostic::warning(code, message, span));
    }

    fn unify_at(&mut self, left: Ty, right: Ty, span: Span, code: &'static str) -> Ty {
        match self.infer.unify(left.clone(), right.clone()) {
            Ok(ty) => ty,
            Err(crate::unify::UnifyError) => {
                self.error(
                    code,
                    format!("tipos incompatibles: `{left}` y `{right}`"),
                    span,
                );
                Ty::Error
            }
        }
    }

    /// A4: acepta `Str` → `String` en valor y anota la conversión para el LIR.
    ///
    /// El sentido contrario (`String` → `&Str`) solo se acepta para *places*
    /// (locales, campos e índices): prestar un temporal produciría `E0716`.
    fn coerce_strings(
        &mut self,
        expected: &Ty,
        actual: &Ty,
        span: Span,
        place: bool,
    ) -> Option<Ty> {
        let expected = self.infer.resolve(expected.clone());
        let actual = self.infer.resolve(actual.clone());
        let coercion = match (&expected, &actual) {
            (Ty::String, Ty::Str) => Coercion::StrToString,
            (Ty::Str, Ty::String) if place => Coercion::StringToStr,
            (Ty::Ref(inner, _), Ty::String) if matches!(**inner, Ty::Str) && place => {
                Coercion::StringToStr
            }
            (Ty::Str, Ty::Ref(inner, _)) if matches!(**inner, Ty::String) => Coercion::StringToStr,
            _ => return None,
        };
        self.coercions.insert(span, coercion);
        Some(expected)
    }

    fn res_at(&self, span: Span) -> Res {
        self.extra_resolutions
            .get(&span)
            .or_else(|| self.resolutions.get(&span))
            .copied()
            .unwrap_or(Res::Error)
    }

    fn res_ty(&mut self, res: Res) -> Ty {
        match res {
            Res::Local(id) => {
                self.used_locals.insert(id);
                self.locals.get(&id).cloned().unwrap_or(Ty::Error)
            }
            Res::Def(def) => {
                let kind = self.krate.def(def).kind;
                match kind {
                    DefKind::Type => Ty::Adt(def, Vec::new()),
                    DefKind::Variant => self
                        .krate
                        .variant_owner(def)
                        .map_or(Ty::Error, |owner| Ty::Adt(owner, Vec::new())),
                    DefKind::Generic => self
                        .generic_env
                        .get(&def)
                        .cloned()
                        .unwrap_or(Ty::Generic(def)),
                    DefKind::Const | DefKind::Static => self
                        .krate
                        .consts
                        .get(&def)
                        .map_or(Ty::Error, |constant| self.ty_from_ast(&constant.ty)),
                    DefKind::Function => {
                        if let Some(signature) = self.krate.signature(def) {
                            let params = signature
                                .params
                                .iter()
                                .map(|ty| self.ty_from_ast(ty))
                                .collect();
                            let ret = self.ty_from_ast(&signature.ret);
                            Ty::Fn(params, Box::new(ret))
                        } else {
                            Ty::Error
                        }
                    }
                    _ => Ty::Error,
                }
            }
            Res::Primitive(primitive) => primitive_ty(primitive),
            Res::Error => Ty::Error,
        }
    }

    fn ty_from_field_with(&mut self, field: &AdtField, env: HashMap<DefId, Ty>) -> Ty {
        let previous = std::mem::take(&mut self.extra_resolutions);
        for resolution in &field.resolutions {
            self.extra_resolutions
                .insert(resolution.span, resolution.res);
        }
        let previous_env = std::mem::replace(&mut self.generic_env, env);
        let ty = self.ty_from_ast(&field.ty);
        self.generic_env = previous_env;
        self.extra_resolutions = previous;
        ty
    }

    fn adt_args(&mut self, adt: &AdtDef) -> (Vec<Ty>, HashMap<DefId, Ty>) {
        let mut env = HashMap::new();
        let args = adt
            .generics
            .iter()
            .map(|generic| {
                let ty = self.infer.fresh();
                env.insert(generic.def, ty.clone());
                ty
            })
            .collect();
        (args, env)
    }

    fn adt_for(&self, span: Span) -> Option<(DefId, AdtDef, Option<AdtVariant>)> {
        match self.res_at(span) {
            Res::Def(def) => {
                if let Some(adt) = self.krate.adt(def) {
                    return Some((def, adt.clone(), None));
                }
                let owner = self.krate.variant_owner(def)?;
                let adt = self.krate.adt(owner)?;
                let variant = adt.variants.iter().find(|v| v.def == def).cloned()?;
                Some((owner, adt.clone(), Some(variant)))
            }
            _ => None,
        }
    }

    fn ty_from_ast(&mut self, ty: &Type) -> Ty {
        match &ty.kind {
            TypeKind::Unit => Ty::Unit,
            TypeKind::Option(inner) => Ty::Option(Box::new(self.ty_from_ast(inner))),
            TypeKind::Ref { mutable, inner } => {
                // `Str` ya es una vista prestada (`&str`): `&Str` se normaliza
                // a `Str` para que las firmas del doc (`(s: &Str)`) coincidan
                // con los literales de string.
                if matches!(&inner.kind, TypeKind::Path { segments, args } if args.is_empty()
                    && segments.last().is_some_and(|name| name == "Str"))
                {
                    return Ty::Str;
                }
                // `CStr` también es una vista prestada (`&CStr`).
                if matches!(&inner.kind, TypeKind::Path { segments, args } if args.is_empty()
                    && segments.last().is_some_and(|name| name == "CStr"))
                {
                    return Ty::CStr;
                }
                // `[T]` ya es una vista prestada (`&[T]`): igual que `Str`.
                if let TypeKind::Slice(elem) = &inner.kind {
                    return Ty::Slice(Box::new(self.ty_from_ast(elem)), *mutable);
                }
                Ty::Ref(Box::new(self.ty_from_ast(inner)), *mutable)
            }
            TypeKind::Array { elem, len } => {
                let elem = self.ty_from_ast(elem);
                let Some(len) = self.const_len(len) else {
                    self.error(
                        "PGS-E3002",
                        "la longitud del array no es constante",
                        ty.span,
                    );
                    return Ty::Error;
                };
                Ty::Array(Box::new(elem), len)
            }
            TypeKind::Slice(inner) => Ty::Slice(Box::new(self.ty_from_ast(inner)), false),
            TypeKind::Tuple(items) => {
                Ty::Tuple(items.iter().map(|item| self.ty_from_ast(item)).collect())
            }
            TypeKind::Path { segments, args } => {
                let name = segments.last().map(String::as_str).unwrap_or("");
                if name == "Result" && args.len() != 2 {
                    self.error(
                        "PGS-E3008",
                        "`Result` requiere un tipo de error concreto",
                        ty.span,
                    );
                    self.error("PGS-E1505", "`Result` sin tipo de error concreto", ty.span);
                }
                let args: Vec<Ty> = args.iter().map(|arg| self.ty_from_ast(arg)).collect();
                match self.res_at(ty.span) {
                    Res::Primitive(primitive) => {
                        let base = primitive_ty(primitive);
                        if !matches!(base, Ty::Error) {
                            base
                        } else {
                            constructor_ty(primitive, args).unwrap_or(Ty::Error)
                        }
                    }
                    Res::Def(def) => match self.krate.def(def).kind {
                        DefKind::Type => Ty::Adt(def, args),
                        DefKind::Generic => self
                            .generic_env
                            .get(&def)
                            .cloned()
                            .unwrap_or(Ty::Generic(def)),
                        _ => Ty::Error,
                    },
                    Res::Error => ty_by_name(name).unwrap_or(Ty::Error),
                    Res::Local(_) => ty_by_name(name).unwrap_or(Ty::Error),
                }
            }
            TypeKind::Ptr(inner) => Ty::Ptr(Box::new(self.ty_from_ast(inner))),
            TypeKind::Fn { params, ret } => Ty::Fn(
                params.iter().map(|param| self.ty_from_ast(param)).collect(),
                Box::new(self.ty_from_ast(ret)),
            ),
            TypeKind::SelfType => self.self_ty.clone(),
        }
    }

    fn const_len(&mut self, expr: &Expr) -> Option<u64> {
        match &expr.kind {
            ExprKind::Int(raw) => parse_u64(raw),
            _ => None,
        }
    }

    fn check_block(&mut self, block: &Block) -> Ty {
        let mut last = Ty::Unit;
        let mut unreachable = false;
        for stmt in &block.stmts {
            if unreachable {
                self.warning("PGS-W6001", "código inalcanzable", stmt.span);
            }
            last = self.check_stmt(stmt);
            if matches!(self.infer.resolve(last.clone()), Ty::Never) {
                unreachable = true;
            }
        }
        last
    }

    fn check_stmt(&mut self, stmt: &Stmt) -> Ty {
        match &stmt.kind {
            StmtKind::Bind {
                pattern,
                ty,
                value,
                else_block,
                ..
            } => {
                if ty.is_none()
                    && matches!(&value.kind, ExprKind::Vector(items) if items.is_empty())
                {
                    self.error(
                        "PGS-E3104",
                        "no se puede inferir el tipo de un `Vec` vacío; anota el binding",
                        value.span,
                    );
                }
                if ty.is_none()
                    && matches!(&value.kind, ExprKind::Path(_) | ExprKind::Field { .. })
                    && matches!(
                        self.res_at(value.span),
                        Res::Def(def) if matches!(self.krate.def(def).kind, DefKind::Function)
                    )
                {
                    self.error(
                        "PGS-E7007",
                        "una función usada como valor requiere un tipo explícito",
                        value.span,
                    );
                }
                // `bind ok(x) = CString.new(...) else ...` maneja el `NulError`.
                let handles_nul = else_block.is_some();
                if handles_nul {
                    self.nul_checked += 1;
                }
                let declared = ty.as_ref().map(|ty| self.ty_from_ast(ty));
                let value_ty = match &declared {
                    Some(declared) => self.check_expr_expected(value, Some(declared)),
                    None => self.check_expr(value),
                };
                if handles_nul {
                    self.nul_checked -= 1;
                }
                if matches!(self.infer.resolve(value_ty.clone()), Ty::Never) {
                    self.error(
                        "PGS-E7008",
                        "una expresión `Never` no puede inicializar un binding",
                        value.span,
                    );
                }
                let target_ty = if let Some(declared) = declared {
                    let place = matches!(
                        value.kind,
                        ExprKind::Path(_) | ExprKind::Field { .. } | ExprKind::Index { .. }
                    );
                    if let Some(ty) = self.coerce_strings(&declared, &value_ty, value.span, place) {
                        ty
                    } else {
                        self.unify_at(declared, value_ty, value.span, "PGS-E3001")
                    }
                } else {
                    value_ty
                };
                if let Some(else_block) = else_block {
                    let else_ty = self.check_block(else_block);
                    let resolved = self.infer.resolve(else_ty);
                    if !matches!(resolved, Ty::Never | Ty::Error) {
                        self.error(
                            "PGS-E9005",
                            "el bloque `else` debe divergir (`return`, `break`, `continue` o `panic`)",
                            else_block.span,
                        );
                    }
                } else if !pattern_is_irrefutable(pattern) {
                    self.error(
                        "PGS-E1105",
                        "el patrón es refutable; añade `else` o usa un patrón irrefutable",
                        pattern.span,
                    );
                }
                self.check_pattern_top(pattern, target_ty.clone());
                self.bind_pattern(pattern, target_ty.clone());
                Ty::Unit
            }
            StmtKind::Assign { target, value } => {
                if matches!(target.kind, ExprKind::Path(_)) {
                    if let Res::Def(def) = self.res_at(target.span) {
                        match self.krate.def(def).kind {
                            DefKind::Static => self.error(
                                "PGS-E1108",
                                "no se puede reasignar un `relic`",
                                target.span,
                            ),
                            DefKind::Const => self.error(
                                "PGS-E1103",
                                "no se puede reasignar un `sigil`",
                                target.span,
                            ),
                            _ => {}
                        }
                    }
                }
                if !matches!(
                    target.kind,
                    ExprKind::Path(_)
                        | ExprKind::Field { .. }
                        | ExprKind::Index { .. }
                        | ExprKind::SelfValue
                ) {
                    self.error(
                        "PGS-E6007",
                        "el destino de una asignación no es un lugar válido",
                        target.span,
                    );
                }
                let target_ty = self.check_expr(target);
                let value_ty = self.check_expr_expected(value, Some(&target_ty));
                let _ = self.unify_at(target_ty, value_ty, value.span, "PGS-E3001");
                Ty::Unit
            }
            StmtKind::Expr(expr) => self.check_expr(expr),
            StmtKind::While { cond, body } => {
                if let ExprKind::Bool(_) = cond.kind {
                    self.warning("PGS-W6002", "condición de bucle constante", cond.span);
                }
                let cond_ty = self.check_expr(cond);
                let _ = self.unify_at(cond_ty, Ty::Bool, cond.span, "PGS-E6001");
                self.break_tys.push(Ty::Unit);
                self.loop_value.push(false);
                let _ = self.check_block(body);
                self.loop_value.pop();
                self.break_tys.pop();
                Ty::Unit
            }
            StmtKind::For {
                pattern,
                iter,
                body,
            } => {
                let iter_ty = self.check_expr(iter);
                let elem_ty = self.iter_item_ty(iter_ty, iter.span);
                if !pattern_is_irrefutable(pattern) {
                    self.error(
                        "PGS-E1105",
                        "el patrón de `for` debe ser irrefutable",
                        pattern.span,
                    );
                }
                self.check_pattern_top(pattern, elem_ty.clone());
                self.bind_pattern(pattern, elem_ty);
                self.break_tys.push(Ty::Unit);
                self.loop_value.push(false);
                let _ = self.check_block(body);
                self.loop_value.pop();
                self.break_tys.pop();
                Ty::Unit
            }
            StmtKind::Return(value) => {
                let expected = self.return_ty.clone();
                let value_ty = value.as_ref().map_or(Ty::Unit, |expr| {
                    self.check_expr_expected(expr, Some(&expected))
                });
                let span = value.as_ref().map_or(stmt.span, |expr| expr.span);
                let place = value.as_ref().is_some_and(|expr| {
                    matches!(
                        expr.kind,
                        ExprKind::Path(_) | ExprKind::Field { .. } | ExprKind::Index { .. }
                    )
                });
                if self
                    .coerce_strings(&expected, &value_ty, span, place)
                    .is_none()
                {
                    let _ = self.unify_at(expected, value_ty, stmt.span, "PGS-E6006");
                }
                Ty::Never
            }
            StmtKind::Break(value) => {
                let value_ty = value
                    .as_ref()
                    .map_or(Ty::Unit, |expr| self.check_expr(expr));
                if let Some(current) = self.break_tys.last().cloned() {
                    if value.is_some() && !self.loop_value.last().copied().unwrap_or(false) {
                        self.error("PGS-E6005", "`break` con valor fuera de `loop`", stmt.span);
                    } else {
                        let index = self.break_tys.len() - 1;
                        self.break_tys[index] =
                            self.unify_at(current, value_ty, stmt.span, "PGS-E6008");
                    }
                } else {
                    self.error("PGS-E6004", "`break` fuera de un bucle", stmt.span);
                }
                Ty::Never
            }
            StmtKind::Continue => Ty::Never,
        }
    }

    fn bind_pattern(&mut self, pattern: &Pattern, ty: Ty) {
        let ty = self.infer.resolve(ty);
        match &pattern.kind {
            PatternKind::Path(path) if path.len() == 1 && is_local_binding(&path[0]) => {
                self.bind_local(pattern.span, ty);
            }
            PatternKind::Bind { pattern, .. } => {
                self.bind_local(pattern.span, ty.clone());
                self.bind_pattern(pattern, ty);
            }
            PatternKind::Tuple(patterns) => {
                if let Ty::Tuple(items) = ty {
                    for (pattern, item) in patterns.iter().zip(items) {
                        self.bind_pattern(pattern, item);
                    }
                }
            }
            PatternKind::Slice(patterns) => {
                let item_ty = match ty {
                    Ty::Array(item, _) | Ty::Slice(item, _) | Ty::Vec(item) => *item,
                    _ => Ty::Error,
                };
                for pattern in patterns {
                    self.bind_pattern(pattern, item_ty.clone());
                }
            }
            PatternKind::Variant { path, args, named } => {
                if let Some((inner, _)) = self.primitive_variant_parts(&path[..], &ty) {
                    for arg in args {
                        self.bind_pattern(arg, inner.clone());
                    }
                    return;
                }
                if let Some((fields, tuple, _is_record)) = self.pattern_adt_fields(pattern.span) {
                    let env = if let Some((owner, adt, _)) = self.adt_for(pattern.span) {
                        let (_adt_args, env) = self.pattern_adt_args(owner, &adt, &ty);
                        env
                    } else {
                        HashMap::new()
                    };
                    let positional = tuple || !args.is_empty();
                    self.bind_field_patterns(&fields, positional, args, named, env);
                }
            }
            PatternKind::Or(patterns) => {
                for pattern in patterns {
                    self.bind_pattern(pattern, ty.clone());
                }
            }
            _ => {}
        }
    }

    fn bind_local(&mut self, span: Span, ty: Ty) {
        if let Res::Local(id) = self.res_at(span) {
            self.locals.insert(id, ty);
        }
    }

    fn bind_field_patterns(
        &mut self,
        fields: &[AdtField],
        tuple: bool,
        args: &[Pattern],
        named: &[(String, Pattern)],
        env: HashMap<DefId, Ty>,
    ) {
        if tuple {
            for (index, pattern) in args.iter().enumerate() {
                if matches!(pattern.kind, PatternKind::Rest) {
                    continue;
                }
                if let Some(field) = fields.get(index) {
                    let field_ty = self.ty_from_field_with(field, env.clone());
                    self.bind_pattern(pattern, field_ty);
                }
            }
        } else {
            for (name, pattern) in named {
                if let Some(field) = fields.iter().find(|field| field.name == *name) {
                    let field_ty = self.ty_from_field_with(field, env.clone());
                    self.bind_pattern(pattern, field_ty);
                }
            }
        }
    }

    fn primitive_variant_parts(&mut self, path: &[String], ty: &Ty) -> Option<(Ty, bool)> {
        let name = path.last()?.as_str();
        match (name, self.infer.resolve(ty.clone())) {
            ("some", Ty::Option(inner)) => Some((*inner, true)),
            ("ok", Ty::Result(ok, _)) => Some((*ok, true)),
            ("err", Ty::Result(_, err)) => Some((*err, true)),
            ("none", Ty::Option(_)) => Some((Ty::Unit, false)),
            _ => None,
        }
    }

    fn pattern_adt_fields(&self, span: Span) -> Option<(Vec<AdtField>, bool, bool)> {
        let (_, adt, variant) = self.adt_for(span)?;
        if let Some(variant) = variant {
            return Some((variant.fields.clone(), variant.tuple, false));
        }
        if adt.kind == AdtKind::Record {
            return Some((adt.fields.clone(), false, true));
        }
        None
    }

    /// Argumentos genéricos que debe usar un patrón: los del tipo escrutado si
    /// ya es `Adt(owner, ...)`; si no, variables frescas. Devuelve también el
    /// entorno para sustituir los parámetros en los tipos de los campos.
    fn pattern_adt_args(
        &mut self,
        owner: DefId,
        adt: &AdtDef,
        ty: &Ty,
    ) -> (Vec<Ty>, HashMap<DefId, Ty>) {
        let args = match self.infer.resolve(ty.clone()) {
            Ty::Adt(def, args) if def == owner && args.len() == adt.generics.len() => args,
            _ => adt.generics.iter().map(|_| self.infer.fresh()).collect(),
        };
        let env = adt
            .generics
            .iter()
            .zip(args.iter())
            .map(|(generic, arg)| (generic.def, arg.clone()))
            .collect();
        (args, env)
    }

    fn iter_item_ty(&mut self, ty: Ty, span: Span) -> Ty {
        // Recorrer un préstamo es recorrer lo prestado (`for x in &values`).
        let ty = match self.infer.resolve(ty) {
            Ty::Ref(inner, _) => *inner,
            other => other,
        };
        match ty {
            Ty::Vec(inner)
            | Ty::Array(inner, _)
            | Ty::Slice(inner, _)
            | Ty::Set(inner)
            | Ty::Iterator(inner)
            | Ty::Option(inner)
            | Ty::Range(inner) => *inner,
            Ty::Map(key, value) => Ty::Tuple(vec![*key, *value]),
            other => {
                self.error("PGS-E3001", format!("`{other}` no se puede recorrer"), span);
                Ty::Error
            }
        }
    }

    fn check_expr(&mut self, expr: &Expr) -> Ty {
        self.check_expr_expected(expr, None)
    }

    /// Como [`Self::check_expr`], pero con el tipo que el contexto espera.
    ///
    /// Propaga el tipo esperado a los constructores (`Call` de una variante y
    /// `Record`) y a los argumentos de una llamada: así se instancian sus
    /// genéricos con los argumentos del tipo esperado y se acepta la coerción
    /// `Str` → `String` en los campos (`bind m: Maybe[String] = Just("hi")`).
    fn check_expr_expected(&mut self, expr: &Expr, expected: Option<&Ty>) -> Ty {
        let ty = match &expr.kind {
            ExprKind::Unit => Ty::Unit,
            ExprKind::Bool(_) => Ty::Bool,
            ExprKind::None => {
                let inner = self.infer.fresh();
                Ty::Option(Box::new(inner))
            }
            ExprKind::Int(raw) => {
                if let Some(value) = parse_int_value(raw) {
                    if !self.negated_literals.contains(&expr.span) {
                        self.int_literals.push((expr.span, value));
                    }
                }
                int_literal_ty(raw).unwrap_or_else(|| self.infer.fresh_int())
            }
            ExprKind::Float(raw) => {
                float_literal_ty(raw).unwrap_or_else(|| self.infer.fresh_float())
            }
            ExprKind::Char(_) => Ty::Char,
            ExprKind::ByteChar(_) => Ty::U8,
            ExprKind::String(lit) => self.string_ty(lit),
            ExprKind::Path(path) => self.path_ty(path, expr.span),
            ExprKind::Record { path, fields, base } => {
                self.record_ty(path, fields, base.as_deref(), expected, expr.span)
            }
            ExprKind::SelfValue => self.self_ty.clone(),
            ExprKind::Tuple(items) => {
                Ty::Tuple(items.iter().map(|item| self.check_expr(item)).collect())
            }
            ExprKind::Array(items) => {
                if items.is_empty() {
                    Ty::Array(Box::new(self.infer.fresh()), 0)
                } else {
                    let elem = self.sequence_ty(items, expr.span);
                    Ty::Array(Box::new(elem), items.len() as u64)
                }
            }
            ExprKind::ArrayRepeat { value, count } => {
                let elem = self.check_expr(value);
                let len = self.const_len(count).unwrap_or_else(|| {
                    self.error(
                        "PGS-E3002",
                        "el tamaño del array no es constante",
                        count.span,
                    );
                    0
                });
                Ty::Array(Box::new(elem), len)
            }
            ExprKind::Vector(items) => Ty::Vec(Box::new(self.sequence_ty(items, expr.span))),
            ExprKind::Map(entries) => {
                let (key, value) = self.map_ty(entries, expr.span);
                if !self.is_hash_eq(&key) {
                    self.error(
                        "PGS-E3102",
                        "la clave del `Map` requiere `Eq` y `Hash`",
                        expr.span,
                    );
                }
                Ty::Map(Box::new(key), Box::new(value))
            }
            ExprKind::Set(items) => {
                let elem = self.sequence_ty(items, expr.span);
                if !self.is_hash_eq(&elem) {
                    self.error(
                        "PGS-E3103",
                        "el elemento del `Set` requiere `Eq` y `Hash`",
                        expr.span,
                    );
                }
                Ty::Set(Box::new(elem))
            }
            ExprKind::Unary { op, expr: inner } => {
                // `-2147483648` se evalúa como el literal negativo, no como la
                // negación de `2147483648` (que no cabe en `Int`).
                if matches!(op, UnOp::Neg) {
                    if let ExprKind::Int(raw) = &inner.kind {
                        if let Some(value) = parse_int_value(raw) {
                            self.negated_literals.insert(inner.span);
                            self.int_literals.push((expr.span, -value));
                        }
                    }
                }
                let inner_ty = self.check_expr(inner);
                match op {
                    UnOp::Not => {
                        let _ = self.unify_at(inner_ty, Ty::Bool, inner.span, "PGS-E6001");
                        Ty::Bool
                    }
                    UnOp::Neg => {
                        if self.user_operator(&inner_ty, "Neg") {
                            return inner_ty;
                        }
                        if !inner_ty.is_numeric() && !matches!(inner_ty, Ty::Error) {
                            self.error(
                                "PGS-E3001",
                                format!("`-` no se puede aplicar a `{inner_ty}`"),
                                expr.span,
                            );
                            Ty::Error
                        } else {
                            inner_ty
                        }
                    }
                }
            }
            ExprKind::Binary { op, lhs, rhs } => self.binary_ty(*op, lhs, rhs, expr.span),
            ExprKind::Range {
                start,
                end,
                inclusive: _,
            } => {
                let start_ty = self.check_expr(start);
                let end_ty = end
                    .as_ref()
                    .map_or(start_ty.clone(), |end| self.check_expr(end));
                let elem = self.unify_at(start_ty, end_ty, expr.span, "PGS-E3001");
                Ty::Range(Box::new(elem))
            }
            ExprKind::Cast { expr: inner, ty } => {
                let from = self.check_expr(inner);
                let to = self.ty_from_ast(ty);
                if !castable(&self.infer.resolve(from.clone()), &to) {
                    self.error(
                        "PGS-E1404",
                        format!("cast inválido de `{from}` a `{to}`"),
                        expr.span,
                    );
                    Ty::Error
                } else {
                    to
                }
            }
            ExprKind::Call { callee, args } => self.call_ty(callee, args, expected, expr.span),
            ExprKind::Index { base, index } => {
                let checked_base = self.check_expr(base);
                let base_ty = match self.infer.resolve(checked_base) {
                    Ty::Ref(inner, _) => *inner,
                    other => other,
                };
                let index_ty = self.check_expr(index);
                match base_ty {
                    Ty::Vec(inner) | Ty::Array(inner, _) | Ty::Slice(inner, _) => {
                        if let (ExprKind::Array(items), Some(value)) =
                            (&base.kind, const_int(&index.kind))
                        {
                            if value < 0 || value as usize >= items.len() {
                                self.error(
                                    "PGS-E3101",
                                    "índice fuera de rango en tiempo de compilación",
                                    index.span,
                                );
                            }
                        }
                        let _ = self.unify_at(index_ty, Ty::Int, index.span, "PGS-E3001");
                        *inner
                    }
                    Ty::Map(key, value) => {
                        let _ = self.unify_at(index_ty, *key, index.span, "PGS-E3001");
                        *value
                    }
                    other => {
                        self.error(
                            "PGS-E3001",
                            format!("`{other}` no se puede indexar"),
                            expr.span,
                        );
                        Ty::Error
                    }
                }
            }
            ExprKind::Field { base, name } => {
                if let Res::Def(def) = self.res_at(expr.span) {
                    if self.krate.variant_owner(def).is_some() {
                        return self.res_ty(Res::Def(def));
                    }
                    // `modulo.item`: función o constante de otro módulo.
                    match self.krate.def(def).kind {
                        pengu_hir::DefKind::Function => {
                            if let Some(signature) = self.krate.signature(def).cloned() {
                                let params = signature
                                    .params
                                    .iter()
                                    .map(|ty| self.ty_from_ast(ty))
                                    .collect();
                                let ret = Box::new(self.ty_from_ast(&signature.ret));
                                return Ty::Fn(params, ret);
                            }
                        }
                        pengu_hir::DefKind::Const | pengu_hir::DefKind::Static => {
                            if let Some(constant) = self.krate.consts.get(&def) {
                                let ty = constant.ty.clone();
                                return self.ty_from_ast(&ty);
                            }
                        }
                        _ => {}
                    }
                }
                if let Some(def) = self.assoc_const(base, name) {
                    return match self.krate.consts.get(&def) {
                        Some(constant) => {
                            let ty = constant.ty.clone();
                            self.ty_from_ast(&ty)
                        }
                        None => Ty::Error,
                    };
                }
                let base_ty = self.check_expr(base);
                let base_ty = self.peel_refs(base_ty);
                if let Ok(index) = name.parse::<usize>() {
                    if let Ty::Tuple(items) = self.infer.resolve(base_ty) {
                        items.get(index).cloned().unwrap_or_else(|| {
                            self.error("PGS-E3001", "campo de tupla inexistente", expr.span);
                            Ty::Error
                        })
                    } else {
                        self.error("PGS-E3001", "el acceso `.N` requiere una tupla", expr.span);
                        Ty::Error
                    }
                } else {
                    self.field_ty(base_ty, name, expr.span)
                }
            }
            ExprKind::Try(inner) => {
                self.nul_checked += 1;
                let inner_ty = self.check_expr(inner);
                self.nul_checked -= 1;
                self.try_ty(inner_ty, expr.span)
            }
            ExprKind::Ref {
                mutable,
                expr: inner,
            } => Ty::Ref(Box::new(self.check_expr(inner)), *mutable),
            ExprKind::If {
                cond,
                then_branch,
                else_branch,
                ..
            } => {
                let cond_ty = self.check_expr(cond);
                let _ = self.unify_at(cond_ty, Ty::Bool, cond.span, "PGS-E6001");
                let then_ty = self.check_block(then_branch);
                if let Some(else_branch) = else_branch {
                    let else_ty = self.check_block(else_branch);
                    self.unify_at(then_ty, else_ty, expr.span, "PGS-E6002")
                } else {
                    let _ = self.unify_at(then_ty, Ty::Unit, expr.span, "PGS-E3001");
                    Ty::Unit
                }
            }
            ExprKind::Match { scrutinee, arms } => {
                let scrutinee_ty = self.check_expr(scrutinee);
                let mut result = Ty::Never;
                for arm in arms {
                    if let Some(pattern) = &arm.pattern {
                        self.check_pattern_top(pattern, scrutinee_ty.clone());
                    }
                    if let Some(guard) = &arm.guard {
                        let guard_ty = self.check_expr(guard);
                        let _ = self.unify_at(guard_ty, Ty::Bool, guard.span, "PGS-E9004");
                    }
                    let arm_ty = self.check_block(&arm.body);
                    result = self.unify_at(result, arm_ty, arm.body.span, "PGS-E6002");
                }
                self.check_match_exhaustive(&scrutinee_ty, arms, expr.span);
                result
            }
            ExprKind::Do(block) => self.check_block(block),
            ExprKind::Curse(block) => {
                let saved = self.in_curse;
                self.in_curse = true;
                let ty = self.check_block(block);
                self.in_curse = saved;
                ty
            }
            ExprKind::Loop(block) => {
                self.break_tys.push(Ty::Never);
                self.loop_value.push(true);
                let _ = self.check_block(block);
                self.loop_value.pop();
                self.break_tys.pop().unwrap_or(Ty::Never)
            }
            ExprKind::Lambda { params, body } => {
                let param_tys: Vec<Ty> = params
                    .iter()
                    .map(|param| self.ty_from_ast(&param.ty))
                    .collect();
                for (param, ty) in params.iter().zip(param_tys.iter()) {
                    if let Res::Local(local) = self.res_at(param.span) {
                        self.locals.insert(local, ty.clone());
                    }
                }
                let ret = self.check_block(body);
                Ty::Fn(param_tys, Box::new(ret))
            }
        };
        self.types.push((expr.span, ty.clone()));
        ty
    }

    fn try_ty(&mut self, inner_ty: Ty, span: Span) -> Ty {
        let return_ty = self.infer.resolve(self.return_ty.clone());
        match self.infer.resolve(inner_ty) {
            Ty::Option(value) => {
                if !matches!(return_ty, Ty::Option(_)) {
                    self.error(
                        "PGS-E1501",
                        "`?` sobre Option requiere que la función devuelva Option",
                        span,
                    );
                    self.error(
                        "PGS-E1405",
                        "`?` fuera de una función que devuelve `Option`",
                        span,
                    );
                }
                *value
            }
            Ty::Result(value, error) => {
                if let Ty::Result(_, expected) = return_ty {
                    let _ = self.unify_at(*error, *expected, span, "PGS-E1502");
                } else {
                    self.error(
                        "PGS-E1501",
                        "`?` sobre Result requiere que la función devuelva Result",
                        span,
                    );
                    self.error(
                        "PGS-E1405",
                        "`?` fuera de una función que devuelve `Result`",
                        span,
                    );
                }
                *value
            }
            other => {
                self.error(
                    "PGS-E1504",
                    format!("`?` requiere Option o Result, no `{other}`"),
                    span,
                );
                Ty::Error
            }
        }
    }

    fn string_ty(&mut self, lit: &StringLit) -> Ty {
        let mut interpolated = false;
        for part in &lit.parts {
            if let StringPart::Expr(expr) = part {
                interpolated = true;
                let _ = self.check_expr(expr);
            }
        }
        match lit.kind {
            StringKind::Byte => Ty::Slice(Box::new(Ty::U8), false),
            StringKind::C => Ty::CStr,
            // Una interpolación construye un `String` en propiedad; un literal
            // sin partes sigue siendo el préstamo `Str`.
            StringKind::Normal | StringKind::Triple | StringKind::Raw => {
                if interpolated {
                    Ty::String
                } else {
                    Ty::Str
                }
            }
        }
    }

    fn sequence_ty(&mut self, items: &[Expr], _span: Span) -> Ty {
        if items.is_empty() {
            return self.infer.fresh();
        }
        let mut elem = self.check_expr(&items[0]);
        for item in &items[1..] {
            let ty = self.check_expr(item);
            elem = self.unify_at(elem, ty, item.span, "PGS-E3001");
        }
        elem
    }

    fn map_ty(&mut self, entries: &[(Expr, Expr)], _span: Span) -> (Ty, Ty) {
        if entries.is_empty() {
            return (self.infer.fresh(), self.infer.fresh());
        }
        let (first_key, first_value) = &entries[0];
        let mut key = self.check_expr(first_key);
        let mut value = self.check_expr(first_value);
        for (k, v) in &entries[1..] {
            let k_ty = self.check_expr(k);
            let v_ty = self.check_expr(v);
            key = self.unify_at(key, k_ty, k.span, "PGS-E3001");
            value = self.unify_at(value, v_ty, v.span, "PGS-E3001");
        }
        (key, value)
    }

    fn is_hash_eq(&mut self, ty: &Ty) -> bool {
        match self.infer.resolve(ty.clone()) {
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
            | Ty::Char
            | Ty::Str
            | Ty::String
            | Ty::Unit
            | Ty::Error => true,
            Ty::Infer(_) | Ty::IntVar(_) => true,
            Ty::Adt(def, _) => self
                .krate
                .adt(def)
                .is_some_and(|adt| adt.derives.iter().any(|d| d == "Eq")),
            Ty::Tuple(items) => items.iter().all(|ty| self.is_hash_eq(ty)),
            _ => false,
        }
    }

    fn user_operator(&self, ty: &Ty, pact: &str) -> bool {
        match ty {
            Ty::Adt(def, _) => {
                let type_name = &self.krate.def(*def).name;
                self.krate.impls.iter().any(|imp| {
                    imp.pact
                        .is_some_and(|pact_def| self.krate.def(pact_def).name == pact)
                        && type_path_name(&imp.ty).is_some_and(|name| name == type_name)
                })
            }
            _ => false,
        }
    }

    fn binary_ty(&mut self, op: BinOp, lhs: &Expr, rhs: &Expr, span: Span) -> Ty {
        let left = self.check_expr(lhs);
        let right = self.check_expr(rhs);
        let resolved_left = self.infer.resolve(left.clone());
        if let Ty::Generic(def) = &resolved_left {
            let required = match op {
                BinOp::Add => Some("Add"),
                BinOp::Sub => Some("Sub"),
                BinOp::Mul => Some("Mul"),
                BinOp::Div => Some("Div"),
                BinOp::Rem => Some("Rem"),
                BinOp::Eq | BinOp::Ne => Some("Eq"),
                BinOp::Lt | BinOp::Le | BinOp::Gt | BinOp::Ge => Some("Ord"),
                _ => None,
            };
            if let Some(required) = required {
                if !self.generic_has_bound(*def, required) {
                    self.error(
                        "PGS-E3004",
                        format!("el genérico no declara el bound `{required}`"),
                        span,
                    );
                }
            }
        }
        if matches!(
            op,
            BinOp::Add | BinOp::Sub | BinOp::Mul | BinOp::Div | BinOp::Rem
        ) && self.user_operator(&resolved_left, operator_pact(op))
        {
            return resolved_left;
        }
        if matches!(
            op,
            BinOp::Eq | BinOp::Ne | BinOp::Lt | BinOp::Le | BinOp::Gt | BinOp::Ge
        ) && self.user_operator(
            &resolved_left,
            if matches!(op, BinOp::Eq | BinOp::Ne) {
                "Eq"
            } else {
                "Ord"
            },
        ) {
            return Ty::Bool;
        }
        match op {
            BinOp::And | BinOp::Or => {
                let _ = self.unify_at(left, Ty::Bool, lhs.span, "PGS-E3001");
                let _ = self.unify_at(right, Ty::Bool, rhs.span, "PGS-E3001");
                Ty::Bool
            }
            BinOp::In => {
                let right = self.infer.resolve(right);
                match right {
                    Ty::Range(elem)
                    | Ty::Vec(elem)
                    | Ty::Set(elem)
                    | Ty::Array(elem, _)
                    | Ty::Slice(elem, _) => {
                        let _ = self.unify_at(left, *elem, span, "PGS-E3001");
                    }
                    Ty::Map(key, _) => {
                        let _ = self.unify_at(left, *key, span, "PGS-E3001");
                    }
                    Ty::Error => {}
                    other => {
                        self.error("PGS-E3001", format!("`in` no acepta `{other}`"), span);
                    }
                }
                Ty::Bool
            }
            BinOp::Eq
            | BinOp::Ne
            | BinOp::Lt
            | BinOp::Le
            | BinOp::Gt
            | BinOp::Ge
            | BinOp::Is
            | BinOp::Isnt => {
                let _ = self.unify_at(left, right, span, "PGS-E1401");
                Ty::Bool
            }
            BinOp::Range | BinOp::RangeInclusive => {
                let elem = self.unify_at(left, right, span, "PGS-E3001");
                Ty::Range(Box::new(elem))
            }
            BinOp::Add | BinOp::Sub | BinOp::Mul | BinOp::Div | BinOp::Rem => {
                if matches!(self.infer.resolve(left.clone()), Ty::String)
                    && is_str_like(&self.infer.resolve(right.clone()))
                    && matches!(op, BinOp::Add)
                {
                    return Ty::String;
                }
                let l = self.infer.resolve(left.clone());
                let r = self.infer.resolve(right.clone());
                if (!l.is_numeric() || !r.is_numeric())
                    && !matches!(l, Ty::Error | Ty::Never)
                    && !matches!(r, Ty::Error | Ty::Never)
                {
                    self.error(
                        "PGS-E1402",
                        format!("operador aritmético no definido para `{l}` y `{r}`"),
                        span,
                    );
                    return Ty::Error;
                }
                let result = self.unify_at(left.clone(), right.clone(), span, "PGS-E3001");
                if !result.is_numeric() && !matches!(result, Ty::Error | Ty::Never) {
                    self.error(
                        "PGS-E1402",
                        format!("operador aritmético sobre `{result}`"),
                        span,
                    );
                    Ty::Error
                } else {
                    result
                }
            }
        }
    }

    fn record_ty(
        &mut self,
        _path: &[String],
        fields: &[(String, Expr)],
        base: Option<&Expr>,
        expected: Option<&Ty>,
        span: Span,
    ) -> Ty {
        let Some((owner, adt, variant)) = self.adt_for(span) else {
            self.error(
                "PGS-E3003",
                "el constructor no es un record ni una variante",
                span,
            );
            return Ty::Error;
        };
        if adt.kind == AdtKind::Record && variant.is_some() {
            self.error("PGS-E3003", "un record no puede ser una variante", span);
            return Ty::Error;
        }
        if adt.kind == AdtKind::Sum && variant.is_none() {
            self.error("PGS-E3003", "se esperaba una variante de la suma", span);
            return Ty::Error;
        }
        let expected_fields: &[AdtField] = variant.as_ref().map_or(&adt.fields, |v| &v.fields);
        // Si el contexto declara el tipo (`Wrap[String]`), instancia los
        // genéricos con esos argumentos para que los campos acepten la
        // coerción `Str` → `String`.
        let (args, env) = match expected.map(|ty| self.infer.resolve(ty.clone())) {
            Some(Ty::Adt(def, adt_args))
                if def == owner && adt_args.len() == adt.generics.len() =>
            {
                let env = adt
                    .generics
                    .iter()
                    .map(|generic| generic.def)
                    .zip(adt_args.iter().cloned())
                    .collect();
                (adt_args, env)
            }
            _ => self.adt_args(&adt),
        };
        let mut seen = HashSet::new();
        let mut provided = HashSet::new();
        for (name, value) in fields {
            if !seen.insert(name.as_str()) {
                self.error("PGS-E8001", format!("campo `{name}` duplicado"), value.span);
                continue;
            }
            let Some(field) = expected_fields.iter().find(|field| field.name == *name) else {
                self.error(
                    "PGS-E8003",
                    format!("campo `{name}` desconocido"),
                    value.span,
                );
                continue;
            };
            provided.insert(name.clone());
            let field_ty = self.ty_from_field_with(field, env.clone());
            let value_ty = self.check_expr_expected(value, Some(&field_ty));
            let place = matches!(
                value.kind,
                ExprKind::Path(_) | ExprKind::Field { .. } | ExprKind::Index { .. }
            );
            if self
                .coerce_strings(&field_ty, &value_ty, value.span, place)
                .is_none()
            {
                let _ = self.unify_at(field_ty, value_ty, value.span, "PGS-E3001");
            }
        }
        if let Some(base) = base {
            let base_ty = self.check_expr(base);
            let _ = self.unify_at(
                base_ty,
                Ty::Adt(owner, args.clone()),
                base.span,
                "PGS-E8005",
            );
        } else {
            for field in expected_fields {
                if !provided.contains(&field.name) {
                    self.error(
                        "PGS-E8002",
                        format!("falta el campo `{}`", field.name),
                        span,
                    );
                }
            }
        }
        Ty::Adt(owner, args)
    }

    fn field_ty(&mut self, base_ty: Ty, name: &str, span: Span) -> Ty {
        match self.infer.resolve(base_ty) {
            Ty::Adt(def, args) => {
                let Some(adt) = self.krate.adt(def).cloned() else {
                    self.error("PGS-E3001", "el tipo no tiene campos", span);
                    return Ty::Error;
                };
                if adt.kind != AdtKind::Record {
                    self.error("PGS-E3001", "solo los records tienen campos", span);
                    return Ty::Error;
                }
                let env: HashMap<DefId, Ty> = adt
                    .generics
                    .iter()
                    .zip(args.iter())
                    .map(|(generic, ty)| (generic.def, ty.clone()))
                    .collect();
                if let Some(field) = adt.fields.iter().find(|field| field.name == name) {
                    if field.vis == pengu_syntax::ast::Visibility::Private
                        && self.current_module != Some(adt.module)
                    {
                        self.error("PGS-E1104", format!("el campo `{name}` es privado"), span);
                    }
                    self.ty_from_field_with(field, env)
                } else {
                    self.error("PGS-E8003", format!("campo `{name}` desconocido"), span);
                    Ty::Error
                }
            }
            other => {
                self.error(
                    "PGS-E3001",
                    format!("`{other}` no tiene el campo `{name}`"),
                    span,
                );
                Ty::Error
            }
        }
    }

    /// `Tipo.CONST`: constante asociada de un `ritual`.
    fn assoc_const(&self, base: &Expr, name: &str) -> Option<DefId> {
        let ExprKind::Path(path) = &base.kind else {
            return None;
        };
        if path.len() != 1 {
            return None;
        }
        let is_type = match self.res_at(base.span) {
            Res::Def(def) => self.krate.def(def).kind == DefKind::Type,
            Res::Primitive(_) => true,
            _ => is_builtin_type_name(&path[0]),
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

    /// `Tipo.nombre(args)`: función asociada de un `ritual` (sin receptor).
    fn associated_call(&mut self, callee: &Expr, args: &[Expr], span: Span) -> Option<Ty> {
        let ExprKind::Field { base, name } = &callee.kind else {
            return None;
        };
        let ExprKind::Path(path) = &base.kind else {
            return None;
        };
        if path.len() != 1 {
            return None;
        }
        let is_type = match self.res_at(base.span) {
            Res::Def(def) => self.krate.def(def).kind == DefKind::Type,
            Res::Primitive(_) => true,
            _ => is_builtin_type_name(&path[0]),
        };
        if !is_type {
            return None;
        }
        let def = *self.krate.methods.get(&path[0])?.iter().find(|def| {
            self.krate.def(**def).name == *name
                && self
                    .krate
                    .signature(**def)
                    .is_some_and(|sig| sig.receiver.is_none())
        })?;
        let signature = self.krate.signature(def)?.clone();
        let saved_env = self.generic_env.clone();
        let mut impl_generics: Vec<pengu_hir::DefId> = Vec::new();
        if let Some(imp) = self
            .krate
            .impls
            .iter()
            .find(|imp| imp.methods.contains(&def))
        {
            for generic in &imp.generics {
                self.generic_env
                    .entry(generic.def)
                    .or_insert_with(|| self.infer.fresh());
                impl_generics.push(generic.def);
            }
        }
        let params: Vec<Ty> = signature
            .params
            .iter()
            .map(|ty| self.ty_from_ast(ty))
            .collect();
        let ret = self.ty_from_ast(&signature.ret);
        // Variables de inferencia del `impl` genérico: se resuelven tras unificar
        // los argumentos y se anotan para que el LIR resuelva la instancia.
        let impl_vars: Vec<Ty> = impl_generics
            .iter()
            .map(|def| self.generic_env.get(def).cloned().unwrap_or(Ty::Error))
            .collect();
        self.generic_env = saved_env;
        if args.len() != params.len() {
            self.error(
                "PGS-E3001",
                format!("`{name}` espera {} argumentos", params.len()),
                span,
            );
            return Some(ret);
        }
        for (param, arg) in params.iter().cloned().zip(args) {
            let actual = self.check_expr(arg);
            let _ = self.unify_at(param, actual, arg.span, "PGS-E3001");
        }
        if !impl_vars.is_empty() {
            let mut resolved: Vec<Ty> = Vec::with_capacity(impl_vars.len());
            for ty in &impl_vars {
                let ty = self.infer.resolve(ty.clone());
                resolved.push(self.infer.apply_defaults(ty));
            }
            if !resolved
                .iter()
                .any(|ty| self.infer.has_unresolved(ty.clone()))
            {
                self.instantiations.insert(span, resolved);
            }
        }
        Some(ret)
    }

    /// Comprueba `arg` contra `expected` aceptando la coerción `Str` →
    /// `String` y devuelve el tipo con el que debe figurar el valor.
    fn check_coerced_arg(&mut self, arg: &Expr, expected: &Ty) -> Ty {
        let ty = self.check_expr_expected(arg, Some(expected));
        let place = matches!(
            arg.kind,
            ExprKind::Path(_) | ExprKind::Field { .. } | ExprKind::Index { .. }
        );
        if let Some(coerced) = self.coerce_strings(expected, &ty, arg.span, place) {
            return coerced;
        }
        let _ = self.unify_at(expected.clone(), ty.clone(), arg.span, "PGS-E3001");
        ty
    }

    fn call_ty(&mut self, callee: &Expr, args: &[Expr], expected: Option<&Ty>, span: Span) -> Ty {
        if let Some(ty) = self.associated_call(callee, args, span) {
            return ty;
        }
        let expected_ty = expected.map(|ty| self.infer.resolve(ty.clone()));
        let callee_is_item = match &callee.kind {
            // Una ruta cualificada por módulo (`std::via::exists`) también es una
            // función de item: sin esto no se instancian sus genéricos (N66).
            ExprKind::Path(path) => {
                path.len() == 1
                    || matches!(
                        self.res_at(callee.span),
                        Res::Def(def) if self.krate.def(def).kind == DefKind::Function
                    )
            }
            ExprKind::Field { .. } => matches!(
                self.res_at(callee.span),
                Res::Def(def) if self.krate.def(def).kind == DefKind::Function
            ),
            _ => false,
        };
        if callee_is_item {
            if let Res::Def(def) = self.res_at(callee.span) {
                if self.krate.def(def).kind == DefKind::Function {
                    if let Some(signature) = self.krate.signature(def).cloned() {
                        if !signature.generics.is_empty() {
                            return self.call_generic(def, &signature, args, None, span);
                        }
                        if matches!(callee.kind, ExprKind::Field { .. }) {
                            if signature.params.len() != args.len() {
                                self.error(
                                    "PGS-E3001",
                                    format!(
                                        "la función espera {} argumentos, no {}",
                                        signature.params.len(),
                                        args.len()
                                    ),
                                    span,
                                );
                                return self.ty_from_ast(&signature.ret);
                            }
                            for (param, arg) in signature.params.iter().zip(args) {
                                let param_ty = self.ty_from_ast(param);
                                let arg_ty = self.check_expr_expected(arg, Some(&param_ty));
                                let place = matches!(
                                    arg.kind,
                                    ExprKind::Path(_)
                                        | ExprKind::Field { .. }
                                        | ExprKind::Index { .. }
                                );
                                if self
                                    .coerce_strings(&param_ty, &arg_ty, arg.span, place)
                                    .is_none()
                                {
                                    let _ = self.unify_at(param_ty, arg_ty, arg.span, "PGS-E7006");
                                }
                            }
                            return self.ty_from_ast(&signature.ret);
                        }
                    }
                }
            }
        }
        if let ExprKind::Index { base, index } = &callee.kind {
            if let ExprKind::Path(path) = &base.kind {
                if path.len() == 1 {
                    if let Res::Def(def) = self.res_at(base.span) {
                        if self.krate.def(def).kind == DefKind::Function {
                            if let Some(signature) = self.krate.signature(def) {
                                if !signature.generics.is_empty() {
                                    let explicit = self.type_arg_ty(index);
                                    return self.call_generic(
                                        def,
                                        signature,
                                        args,
                                        Some(explicit),
                                        span,
                                    );
                                }
                            }
                        }
                    }
                }
            }
        }
        if let ExprKind::Path(path) = &callee.kind {
            if path.len() == 1 {
                match path[0].as_str() {
                    "some" => {
                        let expected_inner = match &expected_ty {
                            Some(Ty::Option(inner)) => Some((**inner).clone()),
                            _ => None,
                        };
                        let arg = match (args.first(), &expected_inner) {
                            (Some(arg), Some(inner)) => self.check_coerced_arg(arg, inner),
                            (Some(arg), None) => self.check_expr(arg),
                            (None, _) => Ty::Error,
                        };
                        if args.len() != 1 {
                            self.error("PGS-E3001", "`some` espera un argumento", span);
                        }
                        return Ty::Option(Box::new(arg));
                    }
                    "ok" => {
                        let expected_ok = match &expected_ty {
                            Some(Ty::Result(ok, _)) => Some((**ok).clone()),
                            _ => None,
                        };
                        let ok = match (args.first(), &expected_ok) {
                            (Some(arg), Some(ok)) => self.check_coerced_arg(arg, ok),
                            (Some(arg), None) => self.check_expr(arg),
                            (None, _) => Ty::Error,
                        };
                        let err = self.infer.fresh();
                        if args.len() != 1 {
                            self.error("PGS-E3001", "`ok` espera un argumento", span);
                        }
                        return Ty::Result(Box::new(ok), Box::new(err));
                    }
                    "err" => {
                        let expected_err = match &expected_ty {
                            Some(Ty::Result(_, err)) => Some((**err).clone()),
                            _ => None,
                        };
                        let err = match (args.first(), &expected_err) {
                            (Some(arg), Some(err)) => self.check_coerced_arg(arg, err),
                            (Some(arg), None) => self.check_expr(arg),
                            (None, _) => Ty::Error,
                        };
                        let ok = self.infer.fresh();
                        if args.len() != 1 {
                            self.error("PGS-E3001", "`err` espera un argumento", span);
                        }
                        return Ty::Result(Box::new(ok), Box::new(err));
                    }
                    "print" => {
                        for arg in args {
                            let ty = self.check_expr(arg);
                            self.require_show(ty, arg.span);
                        }
                        return Ty::Unit;
                    }
                    "format" => {
                        for arg in args {
                            let ty = self.check_expr(arg);
                            self.require_show(ty, arg.span);
                        }
                        return Ty::String;
                    }
                    "assert" => {
                        if args.len() != 2 {
                            self.error("PGS-E7005", "`assert` espera dos argumentos", span);
                        } else {
                            let condition = self.check_expr(&args[0]);
                            let _ = self.unify_at(condition, Ty::Bool, args[0].span, "PGS-E3001");
                            let message = self.check_expr(&args[1]);
                            self.require_show(message, args[1].span);
                        }
                        return Ty::Unit;
                    }
                    "panic" => {
                        if args.len() != 1 {
                            self.error("PGS-E7005", "`panic` espera un argumento", span);
                        } else {
                            let message = self.check_expr(&args[0]);
                            self.require_show(message, args[0].span);
                        }
                        return Ty::Never;
                    }
                    "assert_eq" | "assert_ne" => {
                        if args.len() != 2 {
                            self.error("PGS-E7005", "`assert_eq` espera dos argumentos", span);
                        } else {
                            let left = self.check_expr(&args[0]);
                            let right = self.check_expr(&args[1]);
                            let _ = self.unify_at(left, right, span, "PGS-E1704");
                        }
                        return Ty::Unit;
                    }
                    _ => {}
                }
            }
        }
        if let ExprKind::Field { base, name } = &callee.kind {
            let base_ty = self.check_expr(base);
            let base_ty = self.peel_refs(base_ty);
            if name == "unwrap" || name == "expect" {
                self.warning(
                    "PGS-W1501",
                    "`unwrap`/`expect` puede abortar en producción",
                    span,
                );
            }
            if self.infer.resolve(base_ty.clone()) == Ty::CString && name == "new" {
                if self.nul_checked == 0 {
                    self.error(
                        "PGS-E1608",
                        "`CString.new` puede fallar con `NulError`; usa `?` o maneja el `Result`",
                        span,
                    );
                }
                return Ty::Result(Box::new(Ty::CString), Box::new(Ty::Error));
            }
            if let Some((params, ret)) = self.method_signature(&base_ty, name) {
                if params.len() != args.len() {
                    self.error(
                        "PGS-E3001",
                        format!(
                            "el método `{name}` espera {} argumentos, no {}",
                            params.len(),
                            args.len()
                        ),
                        span,
                    );
                    return ret;
                }
                for (param, arg) in params.into_iter().zip(args) {
                    let arg_ty = self.check_expr_expected(arg, Some(&param));
                    let place = matches!(
                        arg.kind,
                        ExprKind::Path(_) | ExprKind::Field { .. } | ExprKind::Index { .. }
                    );
                    if self
                        .coerce_strings(&param, &arg_ty, arg.span, place)
                        .is_none()
                    {
                        let _ = self.unify_at(param, arg_ty, arg.span, "PGS-E7006");
                    }
                }
                return ret;
            }
            if let ExprKind::Field { name, .. } = &callee.kind {
                let has_field = match self.infer.resolve(base_ty.clone()) {
                    Ty::Adt(def, _) => self
                        .krate
                        .adt(def)
                        .is_some_and(|adt| adt.fields.iter().any(|field| field.name == *name)),
                    _ => false,
                };
                if !has_field {
                    self.error(
                        "PGS-E3001",
                        format!("no se encuentra el método `{name}`"),
                        span,
                    );
                    return Ty::Error;
                }
            }
        }
        if let ExprKind::Path(path) = &callee.kind {
            if let Some(res) = self
                .resolutions
                .get(&callee.span)
                .copied()
                .or_else(|| self.extra_resolutions.get(&callee.span).copied())
            {
                if let Res::Def(def) = res
                    && (self.krate.foreign_fns.contains(&def)
                        || self.krate.curse_fns.contains(&def))
                {
                    self.curse_used = true;
                }
                if let Res::Def(def) = res
                    && self.krate.curse_fns.contains(&def)
                    && !self.in_curse
                {
                    self.error(
                        "PGS-E1602",
                        "llamada a una función `curse` fuera de un bloque `curse`",
                        callee.span,
                    );
                }
                if let Res::Def(def) = res
                    && self.krate.foreign_fns.contains(&def)
                    && !self.in_curse
                    && self
                        .krate
                        .foreign_abis
                        .get(&def)
                        .is_none_or(|abi| abi != "pengu")
                {
                    self.error(
                        "PGS-E1602",
                        "llamada a `foreign` fuera de un bloque `curse`",
                        callee.span,
                    );
                }
            }
            let _ = path;
        }
        let callee_ty = self.check_expr(callee);
        match self.infer.resolve(callee_ty) {
            Ty::Fn(params, ret) => {
                if params.len() != args.len() {
                    self.error(
                        "PGS-E7005",
                        format!(
                            "la función espera {} argumentos, no {}",
                            params.len(),
                            args.len()
                        ),
                        span,
                    );
                    return *ret;
                }
                // Constructor de variante con tipo declarado: instancia sus
                // parámetros genéricos con los argumentos del esperado, para
                // que `Just("hi")` acepte `Str` → `String` si se declara
                // `Maybe[String]`.
                let variant_expected = match (&expected_ty, self.adt_for(callee.span)) {
                    (Some(Ty::Adt(def, adt_args)), Some((owner, adt, Some(variant))))
                        if *def == owner
                            && adt_args.len() == adt.generics.len()
                            && variant.fields.len() == args.len() =>
                    {
                        Some((
                            adt.generics.clone(),
                            adt_args.clone(),
                            variant.fields.clone(),
                        ))
                    }
                    _ => None,
                };
                for (index, (param, arg)) in params.into_iter().zip(args).enumerate() {
                    let mut param = param;
                    if let Some((generics, adt_args, fields)) = &variant_expected {
                        let env: HashMap<DefId, Ty> = generics
                            .iter()
                            .map(|generic| generic.def)
                            .zip(adt_args.iter().cloned())
                            .collect();
                        let field_ty = self.ty_from_field_with(&fields[index], env);
                        param = self.unify_at(param, field_ty, arg.span, "PGS-E3001");
                    }
                    let arg_ty = self.check_expr_expected(arg, Some(&param));
                    let place = matches!(
                        arg.kind,
                        ExprKind::Path(_) | ExprKind::Field { .. } | ExprKind::Index { .. }
                    );
                    if self
                        .coerce_strings(&param, &arg_ty, arg.span, place)
                        .is_none()
                    {
                        let _ = self.unify_at(param, arg_ty, arg.span, "PGS-E7006");
                    }
                }
                if variant_expected.is_some() {
                    expected_ty.unwrap_or(*ret)
                } else {
                    *ret
                }
            }
            other => {
                self.error("PGS-E3001", format!("`{other}` no es invocable"), span);
                Ty::Error
            }
        }
    }

    /// Sustituye por su variable de inferencia cualquier `Ty::Generic` que se
    /// haya colado en una firma (HIR puede resolver el `T` del tipo con un
    /// `DefId` distinto del registrado en `signature.generics`); si el `DefId`
    /// no está en el entorno se busca por nombre, que es estable.
    fn resolve_stray_generics(
        &self,
        ty: &Ty,
        env: &HashMap<DefId, Ty>,
        gens: &[GenericParam],
    ) -> Ty {
        match ty {
            Ty::Generic(def) => {
                if let Some(found) = env.get(def) {
                    return found.clone();
                }
                let name = &self.krate.defs[def.index()].name;
                gens.iter()
                    .find(|generic| &generic.name == name)
                    .and_then(|generic| env.get(&generic.def).cloned())
                    .unwrap_or_else(|| ty.clone())
            }
            Ty::Tuple(items) => Ty::Tuple(
                items
                    .iter()
                    .map(|item| self.resolve_stray_generics(item, env, gens))
                    .collect(),
            ),
            Ty::Array(elem, len) => {
                Ty::Array(Box::new(self.resolve_stray_generics(elem, env, gens)), *len)
            }
            Ty::Slice(elem, mutable) => Ty::Slice(
                Box::new(self.resolve_stray_generics(elem, env, gens)),
                *mutable,
            ),
            Ty::Ref(elem, mutable) => Ty::Ref(
                Box::new(self.resolve_stray_generics(elem, env, gens)),
                *mutable,
            ),
            Ty::Ptr(elem) => Ty::Ptr(Box::new(self.resolve_stray_generics(elem, env, gens))),
            Ty::Vec(elem) => Ty::Vec(Box::new(self.resolve_stray_generics(elem, env, gens))),
            Ty::Set(elem) => Ty::Set(Box::new(self.resolve_stray_generics(elem, env, gens))),
            Ty::Option(elem) => Ty::Option(Box::new(self.resolve_stray_generics(elem, env, gens))),
            Ty::Box(elem) => Ty::Box(Box::new(self.resolve_stray_generics(elem, env, gens))),
            Ty::Rc(elem) => Ty::Rc(Box::new(self.resolve_stray_generics(elem, env, gens))),
            Ty::Arc(elem) => Ty::Arc(Box::new(self.resolve_stray_generics(elem, env, gens))),
            Ty::Range(elem) => Ty::Range(Box::new(self.resolve_stray_generics(elem, env, gens))),
            Ty::Iterator(elem) => {
                Ty::Iterator(Box::new(self.resolve_stray_generics(elem, env, gens)))
            }
            Ty::Map(key, value) => Ty::Map(
                Box::new(self.resolve_stray_generics(key, env, gens)),
                Box::new(self.resolve_stray_generics(value, env, gens)),
            ),
            Ty::Result(ok, err) => Ty::Result(
                Box::new(self.resolve_stray_generics(ok, env, gens)),
                Box::new(self.resolve_stray_generics(err, env, gens)),
            ),
            Ty::Adt(def, args) => Ty::Adt(
                *def,
                args.iter()
                    .map(|arg| self.resolve_stray_generics(arg, env, gens))
                    .collect(),
            ),
            Ty::Fn(params, ret) => Ty::Fn(
                params
                    .iter()
                    .map(|param| self.resolve_stray_generics(param, env, gens))
                    .collect(),
                Box::new(self.resolve_stray_generics(ret, env, gens)),
            ),
            _ => ty.clone(),
        }
    }

    fn call_generic(
        &mut self,
        _def: DefId,
        signature: &Signature,
        args: &[Expr],
        explicit: Option<Ty>,
        span: Span,
    ) -> Ty {
        let mut env = HashMap::new();
        if let Some(explicit) = explicit {
            if signature.generics.len() != 1 {
                self.error("PGS-E1304", "número incorrecto de argumentos de tipo", span);
            } else if let Some(generic) = signature.generics.first() {
                env.insert(generic.def, explicit);
            }
        }
        for generic in &signature.generics {
            env.entry(generic.def).or_insert_with(|| self.infer.fresh());
        }
        let old = std::mem::replace(&mut self.generic_env, env.clone());
        let params: Vec<Ty> = signature
            .params
            .iter()
            .map(|ty| self.ty_from_ast(ty))
            .collect();
        let ret = self.ty_from_ast(&signature.ret);
        let params: Vec<Ty> = params
            .iter()
            .map(|param| self.resolve_stray_generics(param, &env, &signature.generics))
            .collect();
        let ret = self.resolve_stray_generics(&ret, &env, &signature.generics);
        if params.len() != args.len() {
            self.error(
                "PGS-E7005",
                format!(
                    "la función espera {} argumentos, no {}",
                    params.len(),
                    args.len()
                ),
                span,
            );
        } else {
            for (param, arg) in params.iter().cloned().zip(args) {
                let arg_ty = self.check_expr_expected(arg, Some(&param));
                let place = matches!(
                    arg.kind,
                    ExprKind::Path(_) | ExprKind::Field { .. } | ExprKind::Index { .. }
                );
                if self
                    .coerce_strings(&param, &arg_ty, arg.span, place)
                    .is_none()
                {
                    let _ = self.unify_at(param, arg_ty, arg.span, "PGS-E7006");
                }
            }
        }
        let mut inferred = Vec::with_capacity(signature.generics.len());
        for generic in &signature.generics {
            let ty = env.get(&generic.def).cloned().unwrap_or(Ty::Error);
            let ty = self.infer.apply_defaults(ty);
            inferred.push(ty.clone());
            if self.infer.has_unresolved(ty.clone()) {
                self.error(
                    "PGS-E1305",
                    format!("no se puede inferir el parámetro `{}`", generic.name),
                    span,
                );
            }
            for bound in &generic.bounds {
                if !self.implements(&ty, *bound) {
                    self.error(
                        "PGS-E1302",
                        format!(
                            "`{ty}` no cumple el bound `{}`",
                            self.krate.def(*bound).name
                        ),
                        span,
                    );
                    self.error(
                        "PGS-E3005",
                        format!(
                            "`{ty}` no satisface el bound `{}`",
                            self.krate.def(*bound).name
                        ),
                        span,
                    );
                }
            }
        }
        self.instantiations.insert(span, inferred);
        self.generic_env = old;
        ret
    }

    fn type_arg_ty(&mut self, expr: &Expr) -> Ty {
        if let ExprKind::Path(path) = &expr.kind {
            if path.len() == 1 {
                for (def, ty) in &self.generic_env {
                    if self.krate.defs[def.index()].name == path[0] {
                        return ty.clone();
                    }
                }
                return match path[0].as_str() {
                    "Bool" => Ty::Bool,
                    "Int" | "I32" => Ty::Int,
                    "I8" => Ty::I8,
                    "I16" => Ty::I16,
                    "I64" => Ty::I64,
                    "Isize" => Ty::Isize,
                    "U8" => Ty::U8,
                    "U16" => Ty::U16,
                    "U32" | "UInt" => Ty::U32,
                    "U64" => Ty::U64,
                    "Usize" => Ty::Usize,
                    "Float" | "F64" => Ty::Float,
                    "F32" => Ty::F32,
                    "Char" => Ty::Char,
                    "String" => Ty::String,
                    "Str" => Ty::Str,
                    _ => {
                        if let Some(binding) = self
                            .krate
                            .scopes
                            .iter()
                            .find_map(|scope| scope.types.get(&path[0]))
                        {
                            if let Res::Def(def) = binding.res {
                                if let Some(ty) = self.generic_env.get(&def) {
                                    return ty.clone();
                                }
                                return Ty::Adt(def, Vec::new());
                            }
                        }
                        Ty::Error
                    }
                };
            }
        }
        self.error("PGS-E1304", "el argumento de tipo no es un tipo", expr.span);
        Ty::Error
    }

    fn require_show(&mut self, ty: Ty, span: Span) {
        let ty = self.infer.resolve(ty);
        if self.infer.has_unresolved(ty.clone()) {
            return;
        }
        if matches!(
            ty,
            Ty::Error
                | Ty::Never
                | Ty::String
                | Ty::Str
                | Ty::Bool
                | Ty::Char
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
                | Ty::Unit
                | Ty::Array(_, _)
                | Ty::Slice(_, _)
                | Ty::Tuple(_)
                | Ty::Vec(_)
                | Ty::Map(_, _)
                | Ty::Set(_)
                | Ty::Option(_)
                | Ty::Result(_, _)
                | Ty::Box(_)
                | Ty::Rc(_)
                | Ty::Arc(_)
                | Ty::Ordering
                | Ty::Range(_)
        ) {
            return;
        }
        if let Ty::Ref(inner, _) = ty {
            self.require_show(*inner, span);
            return;
        }
        let shown = self.krate.impls.iter().any(|imp| {
            imp.pact
                .is_some_and(|pact| self.krate.def(pact).name == "Show")
                && match (&ty, &imp.ty.kind) {
                    (Ty::Adt(def, _), TypeKind::Path { segments, .. }) => segments
                        .last()
                        .is_some_and(|name| name == &self.krate.def(*def).name),
                    _ => false,
                }
        });
        if !shown {
            self.error(
                "PGS-E1202",
                format!("`{ty}` no implementa `Show`; no se puede imprimir"),
                span,
            );
        }
    }

    /// Tipos primitivos con igualdad estructural (`Eq`/`Ord`).
    fn implements_equality(&self, ty: &Ty) -> bool {
        matches!(
            ty,
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
                | Ty::Char
                | Ty::String
                | Ty::Str
        )
    }

    fn implements(&self, ty: &Ty, pact: DefId) -> bool {
        let name = self.krate.def(pact).name.as_str();
        match name {
            "Eq" => self.implements_equality(ty),
            "Ord" => self.implements_equality(ty) || matches!(
                ty,
                Ty::Int
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
                    | Ty::Char
                    | Ty::String
                    | Ty::Str
            ),
            "Show" => matches!(ty, Ty::String | Ty::Str | Ty::Bool | Ty::Char | Ty::Int | Ty::I8 | Ty::I16 | Ty::I32 | Ty::I64 | Ty::Isize | Ty::U8 | Ty::U16 | Ty::U32 | Ty::U64 | Ty::Usize | Ty::Float | Ty::F32 | Ty::F64),
            _ => match ty {
                Ty::Adt(def, _) => self.krate.impls.iter().any(|imp| {
                    imp.pact == Some(pact)
                        && matches!(&imp.ty.kind, TypeKind::Path { segments, .. }
                            if segments.last().is_some_and(|name| name == &self.krate.def(*def).name))
                }),
                _ => false,
            },
        }
    }

    fn peel_refs(&mut self, mut ty: Ty) -> Ty {
        loop {
            ty = self.infer.resolve(ty);
            match ty {
                Ty::Ref(inner, _) => ty = *inner,
                other => return other,
            }
        }
    }

    fn generic_has_bound(&self, def: pengu_hir::DefId, name: &str) -> bool {
        for signature in self.krate.signatures.values() {
            for generic in &signature.generics {
                if generic.def == def {
                    return generic
                        .bounds
                        .iter()
                        .any(|bound| self.krate.def(*bound).name == name);
                }
            }
        }
        false
    }

    fn method_signature(&mut self, base: &Ty, name: &str) -> Option<(Vec<Ty>, Ty)> {
        if let Ty::Iterator(inner) = self.infer.resolve(base.clone()) {
            match name {
                "map" => {
                    let out = self.infer.fresh();
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(out.clone()));
                    return Some((vec![f], Ty::Iterator(Box::new(out))));
                }
                "filter" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Bool));
                    return Some((vec![f], Ty::Iterator(inner)));
                }
                "fold" => {
                    let acc = self.infer.fresh();
                    let f = Ty::Fn(vec![acc.clone(), (*inner).clone()], Box::new(acc.clone()));
                    return Some((vec![acc.clone(), f], acc));
                }
                "collect" => return Some((Vec::new(), Ty::Vec(inner))),
                "count" => return Some((Vec::new(), Ty::Usize)),
                "last" => return Some((Vec::new(), Ty::Option(Box::new((*inner).clone())))),
                "nth" => return Some((vec![Ty::Usize], Ty::Option(Box::new((*inner).clone())))),
                "sum" => return Some((Vec::new(), (*inner).clone())),
                "min" | "max" => return Some((Vec::new(), Ty::Option(Box::new((*inner).clone())))),
                "any" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Bool));
                    return Some((vec![f], Ty::Bool));
                }
                "all" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Bool));
                    return Some((vec![f], Ty::Bool));
                }
                "find" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Bool));
                    return Some((vec![f], Ty::Option(Box::new((*inner).clone()))));
                }
                "position" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Bool));
                    return Some((vec![f], Ty::Option(Box::new(Ty::Usize))));
                }
                "take" | "skip" | "step_by" => return Some((vec![Ty::Usize], Ty::Iterator(inner))),
                "rev" => return Some((Vec::new(), Ty::Iterator(inner))),
                "enumerate" => {
                    let item = Ty::Tuple(vec![Ty::Usize, (*inner).clone()]);
                    return Some((Vec::new(), Ty::Iterator(Box::new(item))));
                }
                "zip" => {
                    let other = self.infer.fresh();
                    let item = Ty::Tuple(vec![(*inner).clone(), other.clone()]);
                    return Some((
                        vec![Ty::Iterator(Box::new(other))],
                        Ty::Iterator(Box::new(item)),
                    ));
                }
                "filter_map" => {
                    let out = self.infer.fresh();
                    let f = Ty::Fn(
                        vec![(*inner).clone()],
                        Box::new(Ty::Option(Box::new(out.clone()))),
                    );
                    return Some((vec![f], Ty::Iterator(Box::new(out))));
                }
                "flat_map" => {
                    // El cierre devuelve una `Vec[U]` (que en Rust es
                    // `IntoIterator`, lo que `flat_map` necesita).
                    let out = self.infer.fresh();
                    let f = Ty::Fn(
                        vec![(*inner).clone()],
                        Box::new(Ty::Vec(Box::new(out.clone()))),
                    );
                    return Some((vec![f], Ty::Iterator(Box::new(out))));
                }
                "flatten" => {
                    let out = match self.infer.resolve((*inner).clone()) {
                        Ty::Iterator(item) => *item,
                        Ty::Vec(item) => *item,
                        _ => return Some((Vec::new(), Ty::Iterator(Box::new(Ty::Error)))),
                    };
                    return Some((Vec::new(), Ty::Iterator(Box::new(out))));
                }
                "chain" => {
                    return Some((vec![Ty::Iterator(inner.clone())], Ty::Iterator(inner)));
                }
                "take_while" | "skip_while" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Bool));
                    return Some((vec![f], Ty::Iterator(inner)));
                }
                "reduce" => {
                    let f = Ty::Fn(
                        vec![(*inner).clone(), (*inner).clone()],
                        Box::new((*inner).clone()),
                    );
                    return Some((vec![f], Ty::Option(inner)));
                }
                "product" => return Some((Vec::new(), (*inner).clone())),
                "for_each" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Unit));
                    return Some((vec![f], Ty::Unit));
                }
                "inspect" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Unit));
                    return Some((vec![f], Ty::Iterator(inner)));
                }
                "fuse" => return Some((Vec::new(), Ty::Iterator(inner))),
                "max_by" | "min_by" => {
                    let f = Ty::Fn(
                        vec![(*inner).clone(), (*inner).clone()],
                        Box::new(Ty::Ordering),
                    );
                    return Some((vec![f], Ty::Option(inner)));
                }
                _ => {}
            }
        }
        if matches!(
            self.infer.resolve(base.clone()),
            Ty::Vec(_) | Ty::Map(_, _) | Ty::Set(_) | Ty::String | Ty::Str
        ) && name == "len"
        {
            return Some((Vec::new(), Ty::Usize));
        }
        if matches!(self.infer.resolve(base.clone()), Ty::Str | Ty::String) {
            match name {
                "chars" => {
                    return Some((Vec::new(), Ty::Iterator(Box::new(Ty::Char))));
                }
                "bytes" => {
                    return Some((Vec::new(), Ty::Iterator(Box::new(Ty::U8))));
                }
                "char_indices" => {
                    let item = Ty::Tuple(vec![Ty::Usize, Ty::Char]);
                    return Some((Vec::new(), Ty::Iterator(Box::new(item))));
                }
                _ => {}
            }
        }
        match self.infer.resolve(base.clone()) {
            Ty::Map(key, value) => {
                if matches!(name, "iter" | "into_iter") {
                    let item = Ty::Tuple(vec![*key, *value]);
                    return Some((Vec::new(), Ty::Iterator(Box::new(item))));
                }
            }
            Ty::Set(inner) => {
                if matches!(name, "iter" | "into_iter") {
                    return Some((Vec::new(), Ty::Iterator(inner)));
                }
            }
            _ => {}
        }
        if let Ty::Vec(inner) = self.infer.resolve(base.clone()) {
            match name {
                "iter" | "into_iter" => {
                    return Some((Vec::new(), Ty::Iterator(inner)));
                }
                "map" => {
                    let out = self.infer.fresh();
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(out.clone()));
                    return Some((vec![f], Ty::Iterator(Box::new(out))));
                }
                "filter" => {
                    let f = Ty::Fn(vec![(*inner).clone()], Box::new(Ty::Bool));
                    return Some((vec![f], Ty::Iterator(inner)));
                }
                _ => {}
            }
        }
        let type_name = match self.infer.resolve(base.clone()) {
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
            Ty::String => "String".to_owned(),
            Ty::Str => "Str".to_owned(),
            Ty::Vec(_) => "Vec".to_owned(),
            Ty::Map(..) => "Map".to_owned(),
            Ty::Set(_) => "Set".to_owned(),
            Ty::Option(_) => "Option".to_owned(),
            Ty::Result(..) => "Result".to_owned(),
            _ => return None,
        };
        let methods = self.krate.methods.get(&type_name)?;
        for def in methods {
            if self.krate.defs[def.index()].name != name {
                continue;
            }
            let Some(sig) = self.krate.signature(*def).cloned() else {
                continue;
            };
            let saved_env = self.generic_env.clone();
            let saved_extra = self.extra_resolutions.clone();
            let saved_self = self.self_ty.clone();
            if let Some(imp) = self
                .krate
                .impls
                .iter()
                .find(|imp| imp.methods.contains(def))
            {
                let base_resolved = self.infer.resolve(base.clone());
                match (&base_resolved, &imp.ty.kind) {
                    (Ty::Adt(base_def, args), TypeKind::Path { segments, .. }) => {
                        if segments
                            .last()
                            .is_some_and(|name| name == &self.krate.def(*base_def).name)
                        {
                            for (generic, arg) in imp.generics.iter().zip(args.iter()) {
                                self.generic_env.insert(generic.def, arg.clone());
                            }
                        }
                    }
                    (other, TypeKind::Path { .. }) if !imp.generics.is_empty() => {
                        let args = builtin_args(other);
                        for (generic, arg) in imp.generics.iter().zip(args) {
                            self.generic_env.insert(generic.def, arg);
                        }
                    }
                    _ => {}
                }
            }
            if let Some(body) = self.krate.bodies.iter().find(|body| body.owner == *def) {
                for resolution in &body.resolutions {
                    self.extra_resolutions
                        .insert(resolution.span, resolution.res);
                }
            }
            self.self_ty = self.infer.resolve(base.clone());
            let params = sig.params.iter().map(|ty| self.ty_from_ast(ty)).collect();
            let ret = self.ty_from_ast(&sig.ret);
            self.generic_env = saved_env;
            self.extra_resolutions = saved_extra;
            self.self_ty = saved_self;
            return Some((params, ret));
        }
        None
    }

    fn path_ty(&mut self, path: &[String], span: Span) -> Ty {
        if path.len() == 1 {
            match path[0].as_str() {
                "none" => {
                    let inner = self.infer.fresh();
                    return Ty::Option(Box::new(inner));
                }
                "true" | "false" => return Ty::Bool,
                _ => {}
            }
        }
        let res = self.res_at(span);
        if let Res::Def(def) = res {
            if let Some(owner) = self.krate.variant_owner(def) {
                let Some(adt) = self.krate.adt(owner).cloned() else {
                    return Ty::Error;
                };
                let Some(variant) = adt.variants.iter().find(|v| v.def == def).cloned() else {
                    return Ty::Error;
                };
                let (args, env) = self.adt_args(&adt);
                let result = Ty::Adt(owner, args);
                if variant.fields.is_empty() {
                    return result;
                }
                let params = variant
                    .fields
                    .iter()
                    .map(|field| self.ty_from_field_with(field, env.clone()))
                    .collect();
                return Ty::Fn(params, Box::new(result));
            }
        }
        self.res_ty(res)
    }

    fn check_pattern_top(&mut self, pattern: &Pattern, ty: Ty) {
        if matches!(pattern.kind, PatternKind::Rest) {
            self.error(
                "PGS-E9006",
                "`..` solo se permite dentro de un patrón agregado",
                pattern.span,
            );
            return;
        }
        self.check_pattern(pattern, ty);
    }

    fn check_pattern(&mut self, pattern: &Pattern, ty: Ty) {
        let ty = self.infer.resolve(ty);
        if matches!(ty, Ty::Error) {
            return;
        }
        match &pattern.kind {
            PatternKind::Wildcard | PatternKind::Rest => {
                if matches!(pattern.kind, PatternKind::Rest) {
                    self.error(
                        "PGS-E9006",
                        "`..` solo se permite dentro de un patrón agregado",
                        pattern.span,
                    );
                }
            }
            PatternKind::Literal(expr) => {
                let lit_ty = self.check_expr(expr);
                let _ = self.unify_at(lit_ty, ty, pattern.span, "PGS-E9003");
            }
            PatternKind::Path(path) => {
                if path.len() == 1 && is_local_binding(&path[0]) {
                    self.bind_local(pattern.span, ty);
                } else if let Res::Def(def) = self.res_at(pattern.span) {
                    if let Some(owner) = self.krate.variant_owner(def) {
                        let Some(adt) = self.krate.adt(owner).cloned() else {
                            return;
                        };
                        let Some(variant) = adt.variants.iter().find(|v| v.def == def) else {
                            return;
                        };
                        if !variant.fields.is_empty() {
                            self.error(
                                "PGS-E9003",
                                "la variante requiere argumentos",
                                pattern.span,
                            );
                        }
                        let (adt_args, _env) = self.pattern_adt_args(owner, &adt, &ty);
                        let _ =
                            self.unify_at(Ty::Adt(owner, adt_args), ty, pattern.span, "PGS-E9003");
                    } else {
                        self.error("PGS-E9003", "el patrón no es una variante", pattern.span);
                    }
                } else if let Res::Primitive(primitive) = self.res_at(pattern.span) {
                    let _ = self.unify_at(primitive_ty(primitive), ty, pattern.span, "PGS-E9003");
                }
            }
            PatternKind::Bind { pattern, .. } => {
                self.bind_local(pattern.span, ty.clone());
                self.check_pattern(pattern, ty);
            }
            PatternKind::Tuple(patterns) => {
                if let Ty::Tuple(items) = ty {
                    let has_rest = patterns
                        .iter()
                        .any(|pattern| matches!(pattern.kind, PatternKind::Rest));
                    let non_rest = patterns
                        .iter()
                        .filter(|pattern| !matches!(pattern.kind, PatternKind::Rest))
                        .count();
                    if (!has_rest && items.len() != patterns.len())
                        || (has_rest && non_rest > items.len())
                    {
                        self.error("PGS-E9003", "aridad de tupla incorrecta", pattern.span);
                    }
                    for (pattern, item) in patterns.iter().zip(items) {
                        if !matches!(pattern.kind, PatternKind::Rest) {
                            self.check_pattern(pattern, item);
                        }
                    }
                } else {
                    self.error(
                        "PGS-E9003",
                        "el patrón de tupla requiere una tupla",
                        pattern.span,
                    );
                }
            }
            PatternKind::Slice(patterns) => {
                let item_ty = match ty {
                    Ty::Array(item, _) | Ty::Slice(item, _) | Ty::Vec(item) => *item,
                    _ => {
                        self.error(
                            "PGS-E9003",
                            "el patrón de slice requiere una colección",
                            pattern.span,
                        );
                        return;
                    }
                };
                for pattern in patterns {
                    self.check_pattern(pattern, item_ty.clone());
                }
            }
            PatternKind::Range { start, end, .. } => {
                self.check_pattern(start, ty.clone());
                if let Some(end) = end {
                    self.check_pattern(end, ty.clone());
                }
            }
            PatternKind::Or(patterns) => {
                for pattern in patterns {
                    self.check_pattern(pattern, ty.clone());
                }
            }
            PatternKind::Variant { path, args, named } => {
                if let Some((inner, has_arg)) = self.primitive_variant_parts(&path[..], &ty) {
                    if has_arg && args.len() != 1 {
                        self.error("PGS-E9003", "la variante espera un argumento", pattern.span);
                    }
                    for arg in args {
                        self.check_pattern(arg, inner.clone());
                    }
                    return;
                }
                let Some((fields, tuple, _is_record)) = self.pattern_adt_fields(pattern.span)
                else {
                    self.error(
                        "PGS-E9003",
                        "la variante no pertenece al tipo",
                        pattern.span,
                    );
                    return;
                };
                // Instancia la suma con los argumentos del tipo escrutado
                // (`Maybe[Int]`) para no dejar `T` genéricos sueltos en los
                // campos del patrón.
                let env = if let Some((owner, adt, _)) = self.adt_for(pattern.span) {
                    let (adt_args, env) = self.pattern_adt_args(owner, &adt, &ty);
                    let _ = self.unify_at(
                        Ty::Adt(owner, adt_args),
                        ty.clone(),
                        pattern.span,
                        "PGS-E9003",
                    );
                    env
                } else {
                    HashMap::new()
                };
                if tuple || !args.is_empty() {
                    if !named.is_empty() {
                        self.error(
                            "PGS-E9003",
                            "el patrón posicional no acepta campos",
                            pattern.span,
                        );
                    }
                    let has_rest = args.iter().any(|arg| matches!(arg.kind, PatternKind::Rest));
                    let non_rest = args
                        .iter()
                        .filter(|arg| !matches!(arg.kind, PatternKind::Rest))
                        .count();
                    if (!has_rest && non_rest != fields.len())
                        || (has_rest && non_rest > fields.len())
                    {
                        self.error("PGS-E9003", "aridad de variante incorrecta", pattern.span);
                    }
                    for (index, arg) in args.iter().enumerate() {
                        if matches!(arg.kind, PatternKind::Rest) {
                            continue;
                        }
                        if let Some(field) = fields.get(index) {
                            let field_ty = self.ty_from_field_with(field, env.clone());
                            self.check_pattern(arg, field_ty);
                        }
                    }
                } else {
                    let mut seen = HashSet::new();
                    for (name, arg) in named {
                        if !seen.insert(name.as_str()) {
                            self.error("PGS-E9007", format!("campo `{name}` duplicado"), arg.span);
                            continue;
                        }
                        if let Some(field) = fields.iter().find(|field| field.name == *name) {
                            let field_ty = self.ty_from_field_with(field, env.clone());
                            self.check_pattern(arg, field_ty);
                        } else {
                            self.error(
                                "PGS-E8003",
                                format!("campo `{name}` desconocido"),
                                arg.span,
                            );
                        }
                    }
                }
            }
        }
    }

    fn check_match_exhaustive(&mut self, ty: &Ty, arms: &[MatchArm], span: Span) {
        let ty = self.infer.resolve(ty.clone());
        if matches!(ty, Ty::Error | Ty::Never) {
            return;
        }
        let mut coverage = Coverage::default();
        let mut has_else = false;
        let mut else_span = None;
        let mut unreachable = false;
        let mut seen_units: HashSet<String> = HashSet::new();
        for arm in arms {
            let Some(pattern) = &arm.pattern else {
                has_else = true;
                else_span = Some(arm.body.span);
                unreachable = true;
                continue;
            };
            if unreachable {
                self.warning("PGS-W9001", "brazo inalcanzable", arm.body.span);
                continue;
            }
            if arm.guard.is_none() {
                if let Some(key) = unit_variant_key(pattern) {
                    if !seen_units.insert(key) {
                        self.warning("PGS-W9001", "brazo inalcanzable", arm.body.span);
                    }
                }
                coverage.collect(self, pattern);
                if pattern_is_irrefutable(pattern) || coverage.covers(self, &ty) {
                    unreachable = true;
                }
            }
        }
        let exhaustive = coverage.covers(self, &ty);
        if has_else && exhaustive {
            self.error(
                "PGS-E9008",
                "`else` es inalcanzable porque los brazos ya son exhaustivos",
                else_span.unwrap_or(span),
            );
        } else if !has_else && !exhaustive {
            self.error(
                "PGS-E9001",
                "`match` no es exhaustivo; añade los brazos faltantes o un `else`",
                span,
            );
        }
    }
}

fn unit_variant_key(pattern: &Pattern) -> Option<String> {
    match &pattern.kind {
        PatternKind::Variant { path, args, named } if args.is_empty() && named.is_empty() => {
            Some(path.join("::"))
        }
        PatternKind::Path(path) if path.len() == 1 => Some(path.join("::")),
        _ => None,
    }
}

#[derive(Default)]
struct Coverage {
    wildcard: bool,
    bools: HashSet<bool>,
    variants: HashSet<String>,
}

impl Coverage {
    fn collect(&mut self, checker: &Checker<'_>, pattern: &Pattern) {
        if pattern_is_irrefutable(pattern) {
            self.wildcard = true;
            return;
        }
        match &pattern.kind {
            PatternKind::Literal(Expr {
                kind: ExprKind::Bool(value),
                ..
            }) => {
                self.bools.insert(*value);
            }
            PatternKind::Literal(Expr {
                kind: ExprKind::None,
                ..
            }) => {
                self.variants.insert("none".to_owned());
            }
            PatternKind::Variant { path, args, named } => {
                if let Some((fields, tuple, is_record)) = checker.pattern_adt_fields(pattern.span) {
                    if is_record && !tuple {
                        let has_rest = args.iter().any(|arg| matches!(arg.kind, PatternKind::Rest));
                        let full = if named.is_empty() {
                            (has_rest || args.len() >= fields.len())
                                && args.iter().all(|arg| {
                                    matches!(arg.kind, PatternKind::Rest)
                                        || pattern_is_irrefutable(arg)
                                })
                        } else {
                            fields.iter().all(|field| {
                                named.iter().any(|(name, pattern)| {
                                    name == &field.name && pattern_is_irrefutable(pattern)
                                })
                            })
                        };
                        if full {
                            self.wildcard = true;
                            return;
                        }
                    }
                }
                if let Some(name) = path.last() {
                    self.variants.insert(name.clone());
                }
            }
            PatternKind::Path(path) if !path.is_empty() => {
                self.variants.insert(path[path.len() - 1].clone());
            }
            PatternKind::Or(patterns) => {
                for pattern in patterns {
                    self.collect(checker, pattern);
                }
            }
            _ => {}
        }
        let _ = checker;
    }

    fn covers(&self, _checker: &Checker<'_>, ty: &Ty) -> bool {
        if self.wildcard {
            return true;
        }
        match ty {
            Ty::Bool => self.bools.len() >= 2,
            Ty::Option(_) => self.variants.contains("some") && self.variants.contains("none"),
            Ty::Result(_, _) => self.variants.contains("ok") && self.variants.contains("err"),
            Ty::Ordering => {
                self.variants.contains("Less")
                    && self.variants.contains("Equal")
                    && self.variants.contains("Greater")
            }
            Ty::Adt(def, _) => {
                let Some(adt) = _checker.krate.adt(*def) else {
                    return false;
                };
                if adt.kind != AdtKind::Sum {
                    return false;
                }
                adt.variants
                    .iter()
                    .all(|variant| self.variants.contains(&variant.name))
            }
            _ => false,
        }
    }
}

fn pattern_is_irrefutable(pattern: &Pattern) -> bool {
    match &pattern.kind {
        PatternKind::Wildcard => true,
        PatternKind::Bind { pattern, .. } => pattern_is_irrefutable(pattern),
        PatternKind::Path(path) => path.len() == 1 && is_local_binding(&path[0]),
        PatternKind::Tuple(patterns) => patterns.iter().all(pattern_is_irrefutable),
        PatternKind::Variant { .. }
        | PatternKind::Slice(_)
        | PatternKind::Range { .. }
        | PatternKind::Literal(_) => false,
        PatternKind::Or(patterns) => patterns.iter().any(pattern_is_irrefutable),
        PatternKind::Rest => false,
    }
}

/// Tipo por nombre cuando la resolución del AST no está disponible (p. ej.
/// el `String` interno de un `&mut String` en una firma `foreign`).
fn ty_by_name(name: &str) -> Option<Ty> {
    Some(match name {
        "Bool" => Ty::Bool,
        "Int" | "I32" => Ty::Int,
        "I8" => Ty::I8,
        "I16" => Ty::I16,
        "I64" => Ty::I64,
        "Isize" => Ty::Isize,
        "U8" => Ty::U8,
        "U16" => Ty::U16,
        "U32" | "UInt" => Ty::U32,
        "U64" => Ty::U64,
        "Usize" => Ty::Usize,
        "Float" | "F64" => Ty::Float,
        "F32" => Ty::F32,
        "Char" => Ty::Char,
        "Str" => Ty::Str,
        "String" => Ty::String,
        "Unit" => Ty::Unit,
        "Ordering" => Ty::Ordering,
        "CStr" => Ty::CStr,
        "CString" => Ty::CString,
        _ => return None,
    })
}

fn primitive_ty(primitive: Primitive) -> Ty {
    match primitive {
        Primitive::Bool => Ty::Bool,
        Primitive::Int => Ty::Int,
        Primitive::I8 => Ty::I8,
        Primitive::I16 => Ty::I16,
        Primitive::I32 => Ty::I32,
        Primitive::I64 => Ty::I64,
        Primitive::Isize => Ty::Isize,
        Primitive::U8 => Ty::U8,
        Primitive::U16 => Ty::U16,
        Primitive::U32 => Ty::U32,
        Primitive::U64 => Ty::U64,
        Primitive::Usize => Ty::Usize,
        Primitive::F32 => Ty::F32,
        Primitive::F64 => Ty::F64,
        Primitive::Float => Ty::Float,
        Primitive::Char => Ty::Char,
        Primitive::String => Ty::String,
        Primitive::Str => Ty::Str,
        Primitive::Unit => Ty::Unit,
        Primitive::Never => Ty::Never,
        Primitive::CStr => Ty::CStr,
        Primitive::CString => Ty::CString,
        Primitive::Ordering => Ty::Ordering,
        Primitive::Range => Ty::Error,
        Primitive::OrderingLess | Primitive::OrderingEqual | Primitive::OrderingGreater => {
            Ty::Ordering
        }
        _ => Ty::Error,
    }
}

fn constructor_ty(primitive: Primitive, args: Vec<Ty>) -> Option<Ty> {
    let mut args = args.into_iter();
    Some(match primitive {
        Primitive::Vec => Ty::Vec(Box::new(args.next()?)),
        Primitive::Set => Ty::Set(Box::new(args.next()?)),
        Primitive::Map => Ty::Map(Box::new(args.next()?), Box::new(args.next()?)),
        Primitive::Option => Ty::Option(Box::new(args.next()?)),
        Primitive::Result => Ty::Result(Box::new(args.next()?), Box::new(args.next()?)),
        Primitive::Box => Ty::Box(Box::new(args.next()?)),
        Primitive::Rc => Ty::Rc(Box::new(args.next()?)),
        Primitive::Arc => Ty::Arc(Box::new(args.next()?)),
        Primitive::Ptr => Ty::Ptr(Box::new(args.next()?)),
        Primitive::Range => Ty::Range(Box::new(args.next()?)),
        _ => return None,
    })
}

fn castable(from: &Ty, to: &Ty) -> bool {
    if from == to {
        return true;
    }
    match (from, to) {
        (from, to) if from.is_integer() && (to.is_integer() || to.is_float()) => true,
        (from, to) if from.is_float() && (to.is_integer() || to.is_float()) => true,
        (Ty::Char, to) if to.is_integer() => true,
        (Ty::U8, Ty::Char) => true,
        _ => false,
    }
}

fn is_str_like(ty: &Ty) -> bool {
    match ty {
        Ty::Str | Ty::String => true,
        Ty::Ref(inner, false) => matches!(**inner, Ty::Str),
        _ => false,
    }
}

fn operator_pact(op: BinOp) -> &'static str {
    match op {
        BinOp::Add => "Add",
        BinOp::Sub => "Sub",
        BinOp::Mul => "Mul",
        BinOp::Div => "Div",
        BinOp::Rem => "Rem",
        _ => "Add",
    }
}

fn type_path_name(ty: &Type) -> Option<&str> {
    match &ty.kind {
        TypeKind::Path { segments, .. } => segments.last().map(String::as_str),
        _ => None,
    }
}

fn signature_matches(expected: &Signature, actual: &Signature, self_name: &str) -> bool {
    expected.receiver == actual.receiver
        && expected.params.len() == actual.params.len()
        && expected
            .params
            .iter()
            .zip(&actual.params)
            .all(|(expected, actual)| type_matches(expected, actual, self_name))
        && type_matches(&expected.ret, &actual.ret, self_name)
}

fn type_matches(expected: &Type, actual: &Type, self_name: &str) -> bool {
    if expected == actual {
        return true;
    }
    match (&expected.kind, &actual.kind) {
        // `Self` en un pacto equivale al tipo del `ritual` que lo implementa.
        (TypeKind::SelfType, TypeKind::SelfType) => true,
        (TypeKind::SelfType, TypeKind::Path { segments, .. })
        | (TypeKind::Path { segments, .. }, TypeKind::SelfType) => {
            segments.last().map(String::as_str) == Some(self_name)
        }
        (
            TypeKind::Path {
                segments: expected,
                args: expected_args,
            },
            TypeKind::Path {
                segments: actual,
                args: actual_args,
            },
        ) => {
            let expected_name = expected.last().map(String::as_str).unwrap_or("");
            let actual_name = actual.last().map(String::as_str).unwrap_or("");
            let names_match = expected_name == actual_name
                || (expected_name == "Self" && actual_name == self_name);
            names_match
                && expected_args.len() == actual_args.len()
                && expected_args
                    .iter()
                    .zip(actual_args)
                    .all(|(expected, actual)| type_matches(expected, actual, self_name))
        }
        (TypeKind::Option(expected), TypeKind::Option(actual))
        | (TypeKind::Slice(expected), TypeKind::Slice(actual))
        | (TypeKind::Ptr(expected), TypeKind::Ptr(actual)) => {
            type_matches(expected, actual, self_name)
        }
        (
            TypeKind::Ref {
                mutable: expected_mut,
                inner: expected,
            },
            TypeKind::Ref {
                mutable: actual_mut,
                inner: actual,
            },
        ) => expected_mut == actual_mut && type_matches(expected, actual, self_name),
        (TypeKind::Tuple(expected), TypeKind::Tuple(actual)) => {
            expected.len() == actual.len()
                && expected
                    .iter()
                    .zip(actual)
                    .all(|(expected, actual)| type_matches(expected, actual, self_name))
        }
        (
            TypeKind::Array {
                elem: expected_elem,
                len: expected_len,
            },
            TypeKind::Array {
                elem: actual_elem,
                len: actual_len,
            },
        ) => expected_len == actual_len && type_matches(expected_elem, actual_elem, self_name),
        (
            TypeKind::Fn {
                params: expected_params,
                ret: expected_ret,
            },
            TypeKind::Fn {
                params: actual_params,
                ret: actual_ret,
            },
        ) => {
            expected_params.len() == actual_params.len()
                && expected_params
                    .iter()
                    .zip(actual_params)
                    .all(|(expected, actual)| type_matches(expected, actual, self_name))
                && type_matches(expected_ret, actual_ret, self_name)
        }
        _ => false,
    }
}

fn is_local_binding(name: &str) -> bool {
    !name.chars().next().is_some_and(char::is_uppercase)
        && !matches!(
            name,
            "true" | "false" | "none" | "some" | "ok" | "err" | "print" | "format"
        )
}

fn parse_u64(raw: &str) -> Option<u64> {
    let raw = raw.replace('_', "");
    let raw = raw
        .split_once('_')
        .map_or(raw.as_str(), |(digits, _)| digits);
    raw.parse().ok()
}

fn int_literal_ty(raw: &str) -> Option<Ty> {
    let (digits, suffix) = raw.rsplit_once('_')?;
    if digits.is_empty() {
        return None;
    }
    match suffix {
        "i8" => Some(Ty::I8),
        "i16" => Some(Ty::I16),
        "i32" => Some(Ty::I32),
        "i64" => Some(Ty::I64),
        "isize" => Some(Ty::Isize),
        "u8" => Some(Ty::U8),
        "u16" => Some(Ty::U16),
        "u32" => Some(Ty::U32),
        "u64" => Some(Ty::U64),
        "usize" => Some(Ty::Usize),
        _ => None,
    }
}

fn float_literal_ty(raw: &str) -> Option<Ty> {
    let (digits, suffix) = raw.rsplit_once('_')?;
    if digits.is_empty() {
        return None;
    }
    match suffix {
        "f32" => Some(Ty::F32),
        "f64" => Some(Ty::F64),
        _ => None,
    }
}

#[allow(dead_code)]
fn _keep(_: &Param) {}

fn parse_int_value(raw: &str) -> Option<i128> {
    let (digits, _) = match raw.rsplit_once('_') {
        Some((digits, suffix)) if is_integer_suffix(suffix) => (digits, suffix),
        _ => (raw, ""),
    };
    let digits = digits.replace('_', "");
    let (radix, digits) = if let Some(rest) = digits.strip_prefix("0x") {
        (16, rest)
    } else if let Some(rest) = digits.strip_prefix("0o") {
        (8, rest)
    } else if let Some(rest) = digits.strip_prefix("0b") {
        (2, rest)
    } else {
        (10, digits.as_str())
    };
    i128::from_str_radix(digits, radix).ok()
}

fn is_integer_suffix(suffix: &str) -> bool {
    matches!(
        suffix,
        "i8" | "i16" | "i32" | "i64" | "isize" | "u8" | "u16" | "u32" | "u64" | "usize"
    )
}

fn integer_range(ty: &Ty) -> Option<(i128, i128)> {
    Some(match ty {
        Ty::Int | Ty::I32 => (i128::from(i32::MIN), i128::from(i32::MAX)),
        Ty::I8 => (-128, 127),
        Ty::I16 => (-32_768, 32_767),
        Ty::I64 | Ty::Isize => (i128::from(i64::MIN), i128::from(i64::MAX)),
        Ty::U8 => (0, 255),
        Ty::U16 => (0, 65_535),
        Ty::U32 => (0, i128::from(u32::MAX)),
        Ty::U64 | Ty::Usize => (0, i128::from(u64::MAX)),
        _ => return None,
    })
}

fn is_const_expr(expr: &Expr) -> bool {
    match &expr.kind {
        ExprKind::Int(_)
        | ExprKind::Float(_)
        | ExprKind::Bool(_)
        | ExprKind::Char(_)
        | ExprKind::ByteChar(_)
        | ExprKind::String(_)
        | ExprKind::None
        | ExprKind::Unit => true,
        ExprKind::Tuple(items) | ExprKind::Array(items) => items.iter().all(is_const_expr),
        ExprKind::ArrayRepeat { value, count } => is_const_expr(value) && is_const_expr(count),
        ExprKind::Unary { expr, .. } | ExprKind::Cast { expr, .. } => is_const_expr(expr),
        ExprKind::Vector(items) | ExprKind::Set(items) => items.iter().all(is_const_expr),
        ExprKind::Map(entries) => entries
            .iter()
            .all(|(key, value)| is_const_expr(key) && is_const_expr(value)),
        ExprKind::Binary { lhs, rhs, .. } => is_const_expr(lhs) && is_const_expr(rhs),
        ExprKind::Path(path) => !path.is_empty(),
        ExprKind::Field { base, .. } => is_const_expr(base),
        ExprKind::Record { fields, base, .. } => {
            fields.iter().all(|(_, value)| is_const_expr(value))
                && base.as_deref().is_none_or(is_const_expr)
        }
        _ => false,
    }
}

fn has_const_div_zero(expr: &Expr) -> bool {
    match &expr.kind {
        ExprKind::Binary {
            op: BinOp::Div | BinOp::Rem,
            lhs,
            rhs,
        } => {
            let zero = matches!(&rhs.kind, ExprKind::Int(text) if text.replace('_', "") == "0");
            zero || has_const_div_zero(lhs) || has_const_div_zero(rhs)
        }
        ExprKind::Binary { lhs, rhs, .. } => has_const_div_zero(lhs) || has_const_div_zero(rhs),
        ExprKind::Unary { expr, .. } | ExprKind::Cast { expr, .. } => has_const_div_zero(expr),
        ExprKind::Tuple(items) | ExprKind::Array(items) => items.iter().any(has_const_div_zero),
        _ => false,
    }
}

fn const_int(kind: &ExprKind) -> Option<i64> {
    match kind {
        ExprKind::Int(value) => value.parse().ok(),
        _ => None,
    }
}

fn is_operator_pact(name: &str) -> bool {
    matches!(
        name,
        "Add" | "Sub" | "Mul" | "Div" | "Rem" | "Neg" | "Eq" | "Ord"
    )
}

fn type_mentions(ty: &pengu_syntax::ast::Type, name: &str) -> bool {
    match &ty.kind {
        pengu_syntax::ast::TypeKind::Path { segments, args } => {
            segments.last().is_some_and(|segment| segment == name)
                || args.iter().any(|arg| type_mentions(arg, name))
        }
        pengu_syntax::ast::TypeKind::Ref { inner, .. } => type_mentions(inner, name),
        pengu_syntax::ast::TypeKind::Array { elem, .. }
        | pengu_syntax::ast::TypeKind::Slice(elem)
        | pengu_syntax::ast::TypeKind::Ptr(elem) => type_mentions(elem, name),
        pengu_syntax::ast::TypeKind::Tuple(items) => {
            items.iter().any(|item| type_mentions(item, name))
        }
        pengu_syntax::ast::TypeKind::Fn { params, ret } => {
            params.iter().any(|param| type_mentions(param, name)) || type_mentions(ret, name)
        }
        _ => false,
    }
}

fn is_forbidden_operator(name: &str) -> bool {
    matches!(
        name,
        "Index"
            | "IndexMut"
            | "Deref"
            | "DerefMut"
            | "From"
            | "Into"
            | "TryFrom"
            | "TryInto"
            | "Display"
            | "AddAssign"
            | "SubAssign"
            | "MulAssign"
            | "DivAssign"
            | "RemAssign"
            | "BitAnd"
            | "BitOr"
            | "BitXor"
            | "Shl"
            | "Shr"
    )
}

/// Nombres de tipos integrados que admiten funciones asociadas (`Vec.new()`).
fn is_builtin_type_name(name: &str) -> bool {
    matches!(
        name,
        "Vec" | "Map" | "Set" | "Option" | "Result" | "Box" | "Rc" | "Arc" | "Range"
    )
}

/// Argumentos de tipo de un tipo integrado (`Vec[T]` → `[T]`, `Map[K, V]` → `[K, V]`).
fn builtin_args(ty: &Ty) -> Vec<Ty> {
    match ty {
        Ty::Vec(inner) | Ty::Set(inner) | Ty::Option(inner) | Ty::Box(inner) => {
            vec![(**inner).clone()]
        }
        Ty::Map(key, value) | Ty::Result(key, value) => vec![(**key).clone(), (**value).clone()],
        Ty::Rc(inner) | Ty::Arc(inner) => vec![(**inner).clone()],
        Ty::Range(inner) => vec![(**inner).clone()],
        _ => Vec::new(),
    }
}
