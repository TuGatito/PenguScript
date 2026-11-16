//! Lowering de AST a HIR de nombres (C1).
//!
//! C1 construye el árbol de módulos, declara items, procesa `summon` y resuelve
//! los paths de tipos, patrones y expresiones contra scopes léxicos. No comprueba
//! tipos ni ownership; eso corresponde a C2/C4.

use pengu_diag::Diagnostic;
use pengu_span::{DUMMY_SPAN, Span};
use pengu_syntax::ast::{
    Block, Const, ConstKind, DeclarationFile, Expr, ExprKind, Foreign, Item, ItemKind, Method,
    Pact, Param, Pattern, PatternKind, Program, Receiver, Ritual, RitualItem, Stmt, StmtKind,
    Summon, Type, TypeKind, TypeParam, VariantFields, Visibility,
};

use crate::hir::{
    AdtDef, AdtField, AdtKind, AdtVariant, Binding, Body, Def, DefKind, GenericParam, HirCrate,
    ImplDef, Local, Module, Namespace, PactDef, Primitive, Res, Resolution, Scope, ScopeKind,
    Signature, TestInfo,
};
use crate::ids::{BodyId, DefId, LocalId, ModuleId, ScopeId};

/// Resultado de bajar un programa.
#[derive(Clone, Debug)]
pub struct Lowered {
    /// Crate HIR.
    pub krate: HirCrate,
    /// Diagnósticos de resolución.
    pub diagnostics: Vec<Diagnostic>,
}

/// Baja un `Program` a HIR.
#[must_use]
pub fn lower_program(program: &Program) -> Lowered {
    let program = pengu_std::with_std(program);
    let mut lowerer = Lowerer::new();
    lowerer.build(&program);
    lowerer.finish()
}

/// Baja un programa junto con sus declaraciones `.d.pengu`.
///
/// Cada declaración se convierte en un módulo público con su nombre; sus
/// funciones se registran como `foreign` con el ABI del archivo, de forma que
/// el checker exige `curse` para llamarlas igual que a un `foreign "C"`.
#[must_use]
pub fn lower_program_with_declarations(
    program: &Program,
    declarations: &[(String, DeclarationFile)],
) -> Lowered {
    let program = pengu_std::with_std(program);
    let mut lowerer = Lowerer::new();
    lowerer.build_with_declarations(&program, declarations);
    lowerer.finish()
}

/// Baja un archivo `.d.pengu` a HIR.
#[must_use]
pub fn lower_declaration(file: &DeclarationFile) -> Lowered {
    let mut lowerer = Lowerer::new();
    if file.abi == "pengu" && file.items.is_empty() {
        lowerer.error(
            "PGS-E2024",
            "`abi \"pengu\"` sin implementación declarada",
            file.span,
        );
    }
    lowerer.build_declaration(file);
    lowerer.finish()
}

#[derive(Debug)]
enum Pending {
    Function {
        def: DefId,
        module: ModuleId,
        receiver: Option<Receiver>,
        params: Vec<Param>,
        ret: Type,
        body: Block,
        self_ty: Option<Type>,
        generics: Vec<TypeParam>,
        parent_scope: Option<ScopeId>,
    },
    Const {
        def: DefId,
        module: ModuleId,
        ty: Type,
        value: Option<Expr>,
    },
    Type {
        module: ModuleId,
        ty: Type,
    },
    Signature {
        def: DefId,
        module: ModuleId,
        receiver: Option<Receiver>,
        params: Vec<Param>,
        ret: Type,
        self_ty: Option<Type>,
        parent_scope: Option<ScopeId>,
    },
}

#[derive(Debug)]
struct PendingImport {
    module: ModuleId,
    summon: Summon,
}

fn next_id(len: usize) -> u32 {
    u32::try_from(len).expect("el HIR supera u32 elementos")
}

struct Lowerer {
    krate: HirCrate,
    pending: Vec<Pending>,
    imports: Vec<PendingImport>,
    imported: Vec<(DefId, String, Span)>,
    module_edges: Vec<(ModuleId, ModuleId, Span)>,
    methods: std::collections::HashMap<String, Vec<DefId>>,
    /// `ritual` con pacto que aún no está importado: `(índice en impls,
    /// módulo, ruta, span)`. Se resuelve tras aplicar los `summon`.
    pending_pacts: Vec<(usize, ModuleId, Vec<String>, Span)>,
    /// `true` mientras se baja un archivo `.d.pengu`: esos `rune` describen
    /// memoria C y sí admiten `Ptr[T]` en sus campos.
    in_declaration: bool,
}

impl Lowerer {
    fn new() -> Self {
        let root_scope = Scope {
            id: ScopeId(0),
            parent: None,
            kind: ScopeKind::Module,
            values: std::collections::HashMap::new(),
            types: std::collections::HashMap::new(),
            modules: std::collections::HashMap::new(),
        };
        let root = Module {
            id: ModuleId(0),
            parent: None,
            name: String::new(),
            items: Vec::new(),
            scope: root_scope.id,
            def: None,
            span: DUMMY_SPAN,
        };
        let mut this = Self {
            krate: HirCrate {
                root: root.id,
                modules: vec![root],
                defs: Vec::new(),
                bodies: Vec::new(),
                scopes: vec![root_scope],
                signatures: std::collections::HashMap::new(),
                adts: std::collections::HashMap::new(),
                aliases: std::collections::HashMap::new(),
                pacts: std::collections::HashMap::new(),
                show_pact: None,
                impls: Vec::new(),
                variant_owners: std::collections::HashMap::new(),
                methods: std::collections::HashMap::new(),
                assoc_consts: std::collections::HashMap::new(),
                foreign_fns: std::collections::HashSet::new(),
                foreign_abis: std::collections::HashMap::new(),
                curse_fns: std::collections::HashSet::new(),
                tests: std::collections::HashMap::new(),
                grimoires: std::collections::HashSet::new(),
                consts: std::collections::HashMap::new(),
                diagnostics: Vec::new(),
            },
            pending: Vec::new(),
            imports: Vec::new(),
            imported: Vec::new(),
            module_edges: Vec::new(),
            methods: std::collections::HashMap::new(),
            pending_pacts: Vec::new(),
            in_declaration: false,
        };
        let root_id = this.krate.root;
        let show = this.create_def(
            root_id,
            DefKind::Pact,
            "Show",
            Visibility::Public,
            DUMMY_SPAN,
        );
        this.krate.pacts.insert(
            show,
            crate::hir::PactDef {
                def: show,
                module: root_id,
                superpact: None,
                methods: Vec::new(),
                generics: Vec::new(),
            },
        );
        this.krate.show_pact = Some(show);
        // `Show` es prelude: no se emite como item del módulo, pero se conserva
        // su definición para resolver `ritual T for Show` y validar impls.
        this.krate.modules[root_id.index()]
            .items
            .retain(|item| *item != show);
        let root_scope = this.krate.modules[root_id.index()].scope;
        this.krate.scopes[root_scope.index()].types.remove("Show");
        this
    }

    fn build(&mut self, program: &Program) {
        self.build_with_declarations(program, &[]);
    }

    fn build_with_declarations(
        &mut self,
        program: &Program,
        declarations: &[(String, DeclarationFile)],
    ) {
        let root = self.krate.root;
        let mut tests: std::collections::HashMap<&str, Span> = std::collections::HashMap::new();
        for item in &program.items {
            if let ItemKind::Test(test) = &item.kind {
                if tests.insert(&test.name, test.span).is_some() {
                    self.error(
                        "PGS-E1706",
                        format!("el test `{}` está duplicado", test.name),
                        test.span,
                    );
                }
            }
        }
        let mut grimoires = program
            .items
            .iter()
            .filter(|item| matches!(item.kind, ItemKind::Grimoire(_)))
            .peekable();
        if let Some(first) = grimoires.next() {
            for extra in grimoires {
                self.error(
                    "PGS-E2008",
                    "solo puede existir un `grimoire` por programa",
                    extra.span,
                );
            }
            let _ = first;
        }
        for (name, file) in declarations {
            self.build_declaration_module(root, name, file);
        }
        self.build_items(root, &program.items);
        self.install_module_aliases();
        self.resolve_imports();
        self.resolve_pending();
    }

    /// Registra los alias de módulo de `std` (§32.1 de `docs/STDLIB.md`).
    ///
    /// Los ejemplos de la especificación usan nombres de módulo cortos
    /// (`std::ffi`, `std::env`, `std::fs`…) que la implementación real expone
    /// con nombres latinos (`nexus`, `ambitus`, `via`…). El alias es un binding
    /// de módulo en el scope de `std`, así que se resuelve con la misma maquinaria
    /// que un `scroll` real y no hay casos especiales en `find_module_path`.
    fn install_module_aliases(&mut self) {
        const ALIASES: &[(&str, &str)] = &[
            ("int", "integrum"),
            ("string", "verbum"),
            ("math", "numerus"),
            ("io", "fluxus"),
            ("fs", "via"),
            ("process", "exsecutor"),
            ("env", "ambitus"),
            ("time", "tempus"),
            ("ffi", "nexus"),
            ("cell", "cellula"),
            ("test", "proba"),
            ("ops", "opera"),
            ("iter", "funis"),
            ("toml", "libra"),
            ("json", "iason"),
            ("digest", "digestum"),
            ("semver", "versio"),
            ("term", "terminus"),
            ("glob", "globus"),
            ("archive", "archivum"),
            ("net", "rete"),
            ("tls", "rete"),
            ("http", "rete"),
        ];
        let Some(std) = self
            .krate
            .modules
            .iter()
            .find(|m| m.parent == Some(self.krate.root) && m.name == "std")
            .map(|m| m.id)
        else {
            return;
        };
        let std_scope = self.krate.modules[std.index()].scope;
        for (alias, target) in ALIASES {
            if self.krate.scopes[std_scope.index()]
                .modules
                .contains_key(*alias)
            {
                continue;
            }
            let Some(module) = self
                .krate
                .modules
                .iter()
                .find(|m| m.parent == Some(std) && m.name == *target)
                .map(|m| m.id)
            else {
                continue;
            };
            let Some(def) = self.krate.modules[module.index()].def else {
                continue;
            };
            let span = self.krate.modules[module.index()].span;
            self.krate.scopes[std_scope.index()].modules.insert(
                (*alias).to_string(),
                Binding {
                    res: Res::Def(def),
                    span,
                },
            );
        }
    }

    /// Crea el módulo de una declaración `.d.pengu` y registra sus firmas como
    /// `foreign` con el ABI del archivo.
    fn build_declaration_module(&mut self, parent: ModuleId, name: &str, file: &DeclarationFile) {
        let def = self.create_def(parent, DefKind::Module, name, Visibility::Public, file.span);
        let module = self.new_module(parent, name, file.span);
        self.krate.modules[module.index()].def = Some(def);
        let mut signatures = Vec::new();
        let previous = self.in_declaration;
        self.in_declaration = true;
        for item in &file.items {
            if let ItemKind::FunctionSig(sig) = &item.kind {
                signatures.push(sig.clone());
            } else {
                self.build_item(module, item);
            }
        }
        self.in_declaration = previous;
        if !signatures.is_empty() {
            let foreign = Foreign {
                abi: file.abi.clone(),
                items: signatures,
                span: file.span,
            };
            self.build_foreign(module, &foreign);
        }
    }

    fn build_declaration(&mut self, file: &DeclarationFile) {
        let root = self.krate.root;
        for item in &file.items {
            self.build_item(root, item);
        }
        self.resolve_imports();
        self.resolve_pending();
    }

    fn finish(mut self) -> Lowered {
        self.krate.methods = self.methods;
        let mut used = std::collections::HashSet::new();
        for body in &self.krate.bodies {
            for resolution in &body.resolutions {
                if let Res::Def(def) = resolution.res {
                    used.insert(def);
                }
            }
        }
        for adt in self.krate.adts.values() {
            for field in &adt.fields {
                for resolution in &field.resolutions {
                    if let Res::Def(def) = resolution.res {
                        used.insert(def);
                    }
                }
            }
        }
        for import in &self.imported {
            if !used.contains(&import.0) {
                self.krate.diagnostics.push(Diagnostic::warning(
                    "PGS-W2001",
                    format!("el import `{}` no se usa", import.1),
                    import.2,
                ));
            }
        }
        let diagnostics = self.krate.diagnostics.clone();
        Lowered {
            krate: self.krate,
            diagnostics,
        }
    }

    fn error(&mut self, code: &'static str, message: impl Into<String>, span: Span) {
        self.krate
            .diagnostics
            .push(Diagnostic::error(code, message, span));
    }

    fn new_scope(&mut self, parent: Option<ScopeId>, kind: ScopeKind) -> ScopeId {
        let id = ScopeId(next_id(self.krate.scopes.len()));
        self.krate.scopes.push(Scope {
            id,
            parent,
            kind,
            values: std::collections::HashMap::new(),
            types: std::collections::HashMap::new(),
            modules: std::collections::HashMap::new(),
        });
        id
    }

    fn new_module(&mut self, parent: ModuleId, name: &str, span: Span) -> ModuleId {
        let id = ModuleId(next_id(self.krate.modules.len()));
        let scope = self.new_scope(None, ScopeKind::Module);
        self.krate.modules.push(Module {
            id,
            parent: Some(parent),
            name: name.to_owned(),
            items: Vec::new(),
            scope,
            def: None,
            span,
        });
        id
    }

    fn create_def(
        &mut self,
        module: ModuleId,
        kind: DefKind,
        name: &str,
        vis: Visibility,
        span: Span,
    ) -> DefId {
        let id = DefId(next_id(self.krate.defs.len()));
        let ns = kind.namespace();
        let scope = self.krate.modules[module.index()].scope;
        let duplicate = match ns {
            Namespace::Value => self.krate.scopes[scope.index()].values.contains_key(name),
            Namespace::Type => self.krate.scopes[scope.index()].types.contains_key(name),
            Namespace::Module => self.krate.scopes[scope.index()].modules.contains_key(name),
        };
        let module_type_collision = matches!(ns, Namespace::Type | Namespace::Module)
            && (if ns == Namespace::Type {
                self.krate.scopes[scope.index()].modules.contains_key(name)
            } else {
                self.krate.scopes[scope.index()].types.contains_key(name)
            });
        if module_type_collision {
            self.error(
                "PGS-E2005",
                format!("`{name}` no puede ser módulo y tipo a la vez en este ámbito"),
                span,
            );
        }
        if duplicate {
            let code = if ns == Namespace::Module {
                "PGS-E2013"
            } else {
                "PGS-E2005"
            };
            self.error(
                code,
                format!("`{name}` ya está definido en este ámbito"),
                span,
            );
        }
        self.krate.defs.push(Def {
            id,
            kind,
            name: name.to_owned(),
            vis,
            span,
            module,
        });
        self.krate.modules[module.index()].items.push(id);
        let binding = Binding {
            res: Res::Def(id),
            span,
        };
        let scope_ref = &mut self.krate.scopes[scope.index()];
        match ns {
            Namespace::Value => {
                scope_ref.values.insert(name.to_owned(), binding);
            }
            Namespace::Type => {
                scope_ref.types.insert(name.to_owned(), binding);
            }
            Namespace::Module => {
                scope_ref.modules.insert(name.to_owned(), binding);
            }
        }
        id
    }

    fn create_aux_def(
        &mut self,
        module: ModuleId,
        kind: DefKind,
        name: &str,
        vis: Visibility,
        span: Span,
    ) -> DefId {
        let id = DefId(next_id(self.krate.defs.len()));
        self.krate.defs.push(Def {
            id,
            kind,
            name: name.to_owned(),
            vis,
            span,
            module,
        });
        id
    }

    fn build_items(&mut self, module: ModuleId, items: &[Item]) {
        for item in items {
            self.build_item(module, item);
        }
    }

    #[allow(clippy::too_many_lines)]
    fn build_item(&mut self, module: ModuleId, item: &Item) {
        let vis = item.visibility;
        match &item.kind {
            ItemKind::Scroll(scroll) => {
                let def = self.create_def(module, DefKind::Module, &scroll.name, vis, scroll.span);
                let child = self.new_module(module, &scroll.name, scroll.span);
                self.krate.modules[child.index()].def = Some(def);
                self.build_items(child, &scroll.items);
            }
            ItemKind::Summon(summon) => {
                self.imports.push(PendingImport {
                    module,
                    summon: summon.clone(),
                });
            }
            ItemKind::Rune(rune) => {
                let type_def = self.create_def(module, DefKind::Type, &rune.name, vis, rune.span);
                let module_scope = self.krate.modules[module.index()].scope;
                let adt_scope = self.new_scope(Some(module_scope), ScopeKind::Body);
                let mut scratch = Body {
                    id: BodyId(0),
                    owner: type_def,
                    params: Vec::new(),
                    locals: Vec::new(),
                    resolutions: Vec::new(),
                    self_ty: None,
                    ast: None,
                    self_local: None,
                };
                let generic_params =
                    self.bind_generics(module, adt_scope, &rune.params, &mut scratch);
                let mut fields = Vec::with_capacity(rune.fields.len());
                for field in &rune.fields {
                    if matches!(field.ty.kind, TypeKind::Ref { .. }) {
                        self.krate.diagnostics.push(Diagnostic::error(
                            "PGS-E3006",
                            "una referencia no puede guardarse en un campo",
                            field.ty.span,
                        ));
                    }
                    if matches!(&field.ty.kind, TypeKind::Ptr(_)) && !self.in_declaration {
                        self.krate.diagnostics.push(Diagnostic::error(
                            "PGS-E2025",
                            "`Ptr[T]` solo puede usarse en `.d.pengu`, `foreign` o `curse`",
                            field.ty.span,
                        ));
                    }
                    let field_vis = if field.unveil {
                        Visibility::Public
                    } else {
                        Visibility::Private
                    };
                    let field_def = self.create_aux_def(
                        module,
                        DefKind::Field,
                        &field.name,
                        field_vis,
                        field.span,
                    );
                    let resolutions = self.type_resolutions_in_scope(module, adt_scope, &field.ty);
                    fields.push(AdtField {
                        def: field_def,
                        name: field.name.clone(),
                        ty: field.ty.clone(),
                        vis: field_vis,
                        resolutions,
                    });
                }
                let adt = AdtDef {
                    def: type_def,
                    module,
                    kind: AdtKind::Record,
                    fields,
                    variants: Vec::new(),
                    generics: generic_params,
                    is_copy: item.derives.iter().any(|derive| derive == "Copy"),
                    derives: item.derives.clone(),
                };
                self.krate.adts.insert(type_def, adt);
                let self_ty = Type {
                    kind: TypeKind::Path {
                        segments: vec![rune.name.clone()],
                        args: Vec::new(),
                    },
                    span: rune.span,
                };
                for method in &rune.methods {
                    let scope = self.krate.modules[module.index()].scope;
                    self.pending_method(module, scope, method, Some(self_ty.clone()));
                }
            }
            ItemKind::Enchanting(enchanting) => {
                let type_def = self.create_def(
                    module,
                    DefKind::Type,
                    &enchanting.name,
                    vis,
                    enchanting.span,
                );
                let module_scope = self.krate.modules[module.index()].scope;
                let adt_scope = self.new_scope(Some(module_scope), ScopeKind::Body);
                let mut scratch = Body {
                    id: BodyId(0),
                    owner: type_def,
                    params: Vec::new(),
                    locals: Vec::new(),
                    resolutions: Vec::new(),
                    self_ty: None,
                    ast: None,
                    self_local: None,
                };
                let generic_params =
                    self.bind_generics(module, adt_scope, &enchanting.params, &mut scratch);
                let mut variants = Vec::with_capacity(enchanting.variants.len());
                let mut seen_variants = std::collections::HashSet::new();
                for variant in &enchanting.variants {
                    if !seen_variants.insert(variant.name.as_str()) {
                        self.krate.diagnostics.push(Diagnostic::error(
                            "PGS-E8004",
                            format!("variante `{}` duplicada", variant.name),
                            variant.span,
                        ));
                    }
                    let variant_def =
                        self.create_def(module, DefKind::Variant, &variant.name, vis, variant.span);
                    self.bind_variant_value(module, &variant.name, variant_def, variant.span);
                    self.krate.variant_owners.insert(variant_def, type_def);
                    let (fields, tuple) = match &variant.fields {
                        VariantFields::Tuple(types) => {
                            let mut fields = Vec::with_capacity(types.len());
                            for (index, ty) in types.iter().enumerate() {
                                let name = index.to_string();
                                let field_def = self.create_aux_def(
                                    module,
                                    DefKind::Field,
                                    &name,
                                    Visibility::Private,
                                    ty.span,
                                );
                                let resolutions =
                                    self.type_resolutions_in_scope(module, adt_scope, ty);
                                fields.push(AdtField {
                                    def: field_def,
                                    name,
                                    ty: ty.clone(),
                                    vis: Visibility::Private,
                                    resolutions,
                                });
                            }
                            (fields, true)
                        }
                        VariantFields::Named(named) => {
                            let mut fields = Vec::with_capacity(named.len());
                            for field in named {
                                let field_vis = if field.unveil {
                                    Visibility::Public
                                } else {
                                    Visibility::Private
                                };
                                let field_def = self.create_aux_def(
                                    module,
                                    DefKind::Field,
                                    &field.name,
                                    field_vis,
                                    field.span,
                                );
                                let resolutions =
                                    self.type_resolutions_in_scope(module, adt_scope, &field.ty);
                                fields.push(AdtField {
                                    def: field_def,
                                    name: field.name.clone(),
                                    ty: field.ty.clone(),
                                    vis: field_vis,
                                    resolutions,
                                });
                            }
                            (fields, false)
                        }
                        VariantFields::Unit => (Vec::new(), false),
                    };
                    variants.push(AdtVariant {
                        def: variant_def,
                        name: variant.name.clone(),
                        fields,
                        tuple,
                    });
                }
                let adt = AdtDef {
                    def: type_def,
                    module,
                    kind: AdtKind::Sum,
                    fields: Vec::new(),
                    variants,
                    generics: generic_params,
                    is_copy: item.derives.iter().any(|derive| derive == "Copy"),
                    derives: item.derives.clone(),
                };
                self.krate.adts.insert(type_def, adt);
            }
            ItemKind::Pact(pact) => {
                let pact_def = self.create_def(module, DefKind::Pact, &pact.name, vis, pact.span);
                self.build_pact(module, pact, pact_def);
            }
            ItemKind::Ritual(ritual) => {
                if let Some(name) = type_path_name(&ritual.ty)
                    && matches!(
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
                            | "String"
                    )
                    && !self.in_std(module)
                {
                    self.error(
                        "PGS-E1210",
                        "los rituales inherentes sobre primitivos solo se permiten en `std`",
                        ritual.ty.span,
                    );
                }
                let impl_def = self.create_aux_def(
                    module,
                    DefKind::Impl,
                    "<ritual>",
                    Visibility::Private,
                    ritual.span,
                );
                self.build_ritual(module, ritual, impl_def);
            }
            ItemKind::Essence(essence) => {
                if type_path_name(&essence.ty) == Some(essence.name.as_str()) {
                    self.error(
                        "PGS-E3009",
                        "un alias no puede referirse a sí mismo",
                        essence.ty.span,
                    );
                }
                let def = self.create_def(module, DefKind::Type, &essence.name, vis, essence.span);
                self.krate.aliases.insert(def, essence.ty.clone());
                self.pending.push(Pending::Type {
                    module,
                    ty: essence.ty.clone(),
                });
            }
            ItemKind::Foreign(foreign) => self.build_foreign(module, foreign),
            ItemKind::Function(function) => {
                let def = self.create_def(
                    module,
                    DefKind::Function,
                    &function.name,
                    vis,
                    function.span,
                );
                if function.curse {
                    self.krate.curse_fns.insert(def);
                }
                self.pending.push(Pending::Function {
                    def,
                    module,
                    receiver: None,
                    params: function.params.clone(),
                    ret: function.ret.clone(),
                    body: function.body.clone(),
                    self_ty: None,
                    generics: function.type_params.clone(),
                    parent_scope: None,
                });
            }
            ItemKind::Const(constant) => self.build_const(module, constant),
            ItemKind::Grimoire(grimoire) => {
                let def = self.create_def(module, DefKind::Function, "main", vis, grimoire.span);
                self.krate.grimoires.insert(def);
                let unit = Type {
                    kind: TypeKind::Unit,
                    span: grimoire.span,
                };
                self.pending.push(Pending::Function {
                    def,
                    module,
                    receiver: None,
                    params: Vec::new(),
                    ret: grimoire.ret.clone().unwrap_or(unit),
                    body: grimoire.body.clone(),
                    self_ty: None,
                    generics: Vec::new(),
                    parent_scope: None,
                });
            }
            ItemKind::Test(test) => {
                let def = self.create_def(module, DefKind::Function, &test.name, vis, test.span);
                let mut info = TestInfo::default();
                for option in &test.options {
                    match option.name.as_str() {
                        "should_panic" => info.should_panic = Some(option.message.clone()),
                        "ignore" => info.ignore = Some(option.message.clone()),
                        _ => {}
                    }
                }
                self.krate.tests.insert(def, info);
                self.pending.push(Pending::Function {
                    def,
                    module,
                    receiver: None,
                    params: Vec::new(),
                    ret: test.ret.clone(),
                    body: test.body.clone(),
                    self_ty: None,
                    generics: Vec::new(),
                    parent_scope: None,
                });
            }
            ItemKind::FunctionSig(sig) => {
                let _ = self.create_def(module, DefKind::Function, &sig.name, vis, sig.span);
                self.pending_types(
                    module,
                    &sig.params.iter().map(|p| p.ty.clone()).collect::<Vec<_>>(),
                );
                self.pending.push(Pending::Type {
                    module,
                    ty: sig.ret.clone(),
                });
            }
        }
    }

    fn type_resolutions_in_scope(
        &mut self,
        module: ModuleId,
        scope: ScopeId,
        ty: &Type,
    ) -> Vec<Resolution> {
        let mut scratch = Body {
            id: BodyId(0),
            owner: DefId(0),
            params: Vec::new(),
            locals: Vec::new(),
            resolutions: Vec::new(),
            self_ty: None,
            ast: None,
            self_local: None,
        };
        self.resolve_type(ty, module, scope, None, &mut scratch);
        scratch.resolutions
    }

    fn bind_variant_value(&mut self, module: ModuleId, name: &str, def: DefId, span: Span) {
        let scope = self.krate.modules[module.index()].scope;
        if self.krate.scopes[scope.index()].values.contains_key(name) {
            self.error("PGS-E2005", format!("`{name}` ya está declarado"), span);
            return;
        }
        self.krate.scopes[scope.index()].values.insert(
            name.to_owned(),
            Binding {
                res: Res::Def(def),
                span,
            },
        );
    }

    fn pending_types(&mut self, module: ModuleId, types: &[Type]) {
        for ty in types {
            self.pending.push(Pending::Type {
                module,
                ty: ty.clone(),
            });
        }
    }

    fn is_ffi_type(ty: &Type) -> bool {
        match &ty.kind {
            TypeKind::Unit | TypeKind::Ptr(_) => true,
            TypeKind::Ref { inner, .. } => {
                matches!(&inner.kind, TypeKind::Path { segments, .. }
                    if segments.last().is_some_and(|s| s == "CStr"))
            }
            TypeKind::Path { segments, .. } => {
                // Escalares y `rune`/`enchanting` declarados (todos `#[repr(C)]`).
                // Los tipos gestionados por el runtime no cruzan la frontera.
                !matches!(
                    segments.last().map(String::as_str),
                    Some(
                        "String"
                            | "Str"
                            | "Vec"
                            | "Map"
                            | "Set"
                            | "Option"
                            | "Result"
                            | "Box"
                            | "Rc"
                            | "Arc"
                            | "Iter"
                            | "Iterator"
                            | "CString"
                            | "NulError"
                            | "Fn"
                    )
                )
            }
            _ => false,
        }
    }

    /// Comprueba si `module` es `std` o desciende de él.
    ///
    /// La stdlib se organiza en submódulos (`std::integrum`), así que la regla
    /// "los rituales sobre primitivos solo se permiten en `std`" mira todo el
    /// árbol y no solo el módulo raíz (D3 de `scratch/STDLIB_PLAN.md`).
    fn in_std(&self, module: ModuleId) -> bool {
        let mut current = Some(module);
        while let Some(id) = current {
            let data = &self.krate.modules[id.index()];
            if data.name == "std" {
                return true;
            }
            current = data.parent;
        }
        false
    }

    fn build_foreign(&mut self, module: ModuleId, foreign: &Foreign) {
        let pengu = foreign.abi == "pengu";
        if pengu && !self.in_std(module) {
            self.error(
                "PGS-E1210",
                "`abi \"pengu\"` solo se permite en `std`",
                foreign.span,
            );
        }
        if !pengu && !matches!(foreign.abi.as_str(), "C" | "system") {
            let code = if foreign.abi == "js" {
                "PGS-E2022"
            } else {
                "PGS-E1605"
            };
            self.error(
                code,
                format!("ABI `{}` no soportada", foreign.abi),
                foreign.span,
            );
        }
        for sig in &foreign.items {
            if !pengu {
                for param in &sig.params {
                    if !Self::is_ffi_type(&param.ty) {
                        self.error("PGS-E1604", "tipo no representable en C", param.ty.span);
                    }
                }
                if !Self::is_ffi_type(&sig.ret) {
                    self.error("PGS-E1604", "tipo no representable en C", sig.ret.span);
                }
            }
            let def = self.create_def(
                module,
                DefKind::Function,
                &sig.name,
                Visibility::Public,
                sig.span,
            );
            self.krate.foreign_fns.insert(def);
            self.krate.foreign_abis.insert(def, foreign.abi.clone());
            let (scope, generics) = self.type_scope(module, &sig.generics);
            self.krate.signatures.insert(
                def,
                crate::hir::Signature {
                    params: sig.params.iter().map(|p| p.ty.clone()).collect(),
                    ret: sig.ret.clone(),
                    receiver: None,
                    generics,
                },
            );
            self.pending.push(Pending::Signature {
                def,
                module,
                receiver: None,
                params: sig.params.clone(),
                ret: sig.ret.clone(),
                self_ty: None,
                parent_scope: Some(scope),
            });
        }
    }

    fn type_scope(
        &mut self,
        module: ModuleId,
        params: &[TypeParam],
    ) -> (ScopeId, Vec<GenericParam>) {
        let module_scope = self.krate.modules[module.index()].scope;
        let scope = self.new_scope(Some(module_scope), ScopeKind::Block);
        let mut scratch = Body {
            id: BodyId(0),
            owner: DefId(0),
            params: Vec::new(),
            locals: Vec::new(),
            resolutions: Vec::new(),
            self_ty: None,
            ast: None,
            self_local: None,
        };
        let generics = self.bind_generics(module, scope, params, &mut scratch);
        (scope, generics)
    }

    fn type_scope_for_impl(
        &mut self,
        module: ModuleId,
        params: &[TypeParam],
        ty: &Type,
    ) -> (ScopeId, Vec<GenericParam>) {
        let module_scope = self.krate.modules[module.index()].scope;
        let adt = if let TypeKind::Path { segments, .. } = &ty.kind {
            segments.last().and_then(|name| {
                self.lookup_type(module_scope, name)
                    .and_then(|binding| match binding.res {
                        Res::Def(def) => self.krate.adt(def).cloned(),
                        _ => None,
                    })
            })
        } else {
            None
        };
        let Some(adt) = adt else {
            return self.type_scope(module, params);
        };
        if adt.generics.len() != params.len() {
            return self.type_scope(module, params);
        }
        let scope = self.new_scope(Some(module_scope), ScopeKind::Block);
        for (generic, param) in adt.generics.iter().zip(params) {
            let _ = self.bind_in_scope(
                scope,
                Namespace::Type,
                &generic.name,
                Res::Def(generic.def),
                param.span,
            );
        }
        (scope, adt.generics)
    }

    fn build_pact(&mut self, module: ModuleId, pact: &Pact, pact_def: DefId) {
        let (pact_scope, generics) = self.type_scope(module, &pact.params);
        let args = pact
            .params
            .iter()
            .map(|param| Type {
                kind: TypeKind::Path {
                    segments: vec![param.name.clone()],
                    args: Vec::new(),
                },
                span: param.span,
            })
            .collect();
        let self_ty = Type {
            kind: TypeKind::Path {
                segments: vec![pact.name.clone()],
                args,
            },
            span: pact.span,
        };
        let superpact = pact
            .supertrait
            .as_ref()
            .and_then(|path| self.resolve_pact_ref(module, path, pact.span));
        let mut methods = Vec::new();
        for method in &pact.methods {
            methods.push(self.pending_method(module, pact_scope, method, Some(self_ty.clone())));
        }
        self.krate.pacts.insert(
            pact_def,
            PactDef {
                def: pact_def,
                module,
                superpact,
                methods,
                generics,
            },
        );
    }

    fn build_ritual(&mut self, module: ModuleId, ritual: &Ritual, impl_def: DefId) {
        let (ritual_scope, generics) = self.type_scope_for_impl(module, &ritual.params, &ritual.ty);
        let pact = ritual.trait_path.as_ref().and_then(|path| {
            if let Some(def) = self.pact_def(module, path) {
                Some(def)
            } else {
                // Puede ser un pacto importado con un `summon` posterior:
                // se reintenta en `resolve_pending_pacts`.
                self.pending_pacts.push((
                    self.krate.impls.len(),
                    module,
                    path.clone(),
                    ritual.span,
                ));
                None
            }
        });
        let resolutions = self.type_resolutions_in_scope(module, ritual_scope, &ritual.ty);
        if let pengu_syntax::ast::TypeKind::Path { segments, .. } = &ritual.ty.kind {
            if segments.len() == 1 && generics.iter().any(|generic| generic.name == segments[0]) {
                self.error(
                    "PGS-E1207",
                    "un `ritual` no puede ser blanket sobre un parámetro genérico",
                    ritual.span,
                );
            }
        }
        let mut methods = Vec::new();
        let mut functions = Vec::new();
        let mut consts = Vec::new();
        for item in &ritual.items {
            match item {
                RitualItem::Method(method) => {
                    methods.push(self.pending_method(
                        module,
                        ritual_scope,
                        method,
                        Some(ritual.ty.clone()),
                    ));
                }
                RitualItem::Const(constant) => {
                    let kind = match constant.kind {
                        ConstKind::Sigil => DefKind::Const,
                        ConstKind::Relic => DefKind::Static,
                    };
                    // Visibilidad pública: las constantes asociadas se usan
                    // desde otros módulos (`Int.MAX` en un `grimoire`), y el
                    // codegen las emite como `const` del módulo dueño.
                    let def = self.create_aux_def(
                        module,
                        kind,
                        &constant.name,
                        Visibility::Public,
                        constant.span,
                    );
                    consts.push(def);
                    self.pending.push(Pending::Const {
                        def,
                        module,
                        ty: constant.ty.clone(),
                        value: constant.value.clone(),
                    });
                }
                RitualItem::Function(function) => {
                    let def = self.create_aux_def(
                        module,
                        DefKind::Function,
                        &function.name,
                        Visibility::Private,
                        function.span,
                    );
                    functions.push(def);
                    self.pending.push(Pending::Function {
                        def,
                        module,
                        receiver: None,
                        params: function.params.clone(),
                        ret: function.ret.clone(),
                        body: function.body.clone(),
                        self_ty: Some(ritual.ty.clone()),
                        generics: function.type_params.clone(),
                        parent_scope: Some(ritual_scope),
                    });
                }
            }
        }
        if let Some(name) = type_path_name(&ritual.ty) {
            // Las funciones asociadas (`String.from`, `Point.origin`) se
            // resuelven por el mismo mapa que los métodos: `Tipo.nombre(args)`.
            // Se registran en `self.methods` porque `finish` vuelca ese mapa
            // sobre `krate.methods`.
            let entry = self.methods.entry(name.to_owned()).or_default();
            entry.extend(methods.iter().copied());
            entry.extend(functions.iter().copied());
            let consts_entry = self.krate.assoc_consts.entry(name.to_owned()).or_default();
            consts_entry.extend(consts.iter().copied());
        }
        let mut all_methods = methods.clone();
        all_methods.extend(functions.iter().copied());
        self.krate.impls.push(ImplDef {
            def: impl_def,
            module,
            ty: ritual.ty.clone(),
            resolutions,
            pact,
            methods: all_methods,
            consts,
            generics,
        });
    }

    fn pending_method(
        &mut self,
        module: ModuleId,
        parent_scope: ScopeId,
        method: &Method,
        self_ty: Option<Type>,
    ) -> DefId {
        let def = self.create_aux_def(
            module,
            DefKind::Function,
            &method.name,
            Visibility::Public,
            method.span,
        );
        if let Some(owner) = self_ty.as_ref().and_then(type_name) {
            if method.body.is_some() {
                self.methods.entry(owner).or_default().push(def);
            }
        }
        if let Some(body) = &method.body {
            self.pending.push(Pending::Function {
                def,
                module,
                receiver: Some(method.receiver),
                params: method.params.clone(),
                ret: method.ret.clone(),
                body: body.clone(),
                self_ty,
                generics: Vec::new(),
                parent_scope: Some(parent_scope),
            });
        } else {
            self.pending.push(Pending::Signature {
                def,
                module,
                receiver: Some(method.receiver),
                params: method.params.clone(),
                ret: method.ret.clone(),
                self_ty,
                parent_scope: Some(parent_scope),
            });
        }
        def
    }

    fn resolve_pact_ref(&mut self, module: ModuleId, path: &[String], span: Span) -> Option<DefId> {
        let resolved = self.pact_def(module, path);
        if resolved.is_none() {
            self.error(
                "PGS-E1303",
                format!("`{}` no es un pact", path.join("::")),
                span,
            );
        }
        resolved
    }

    /// Busca el `DefId` de un pacto sin emitir diagnóstico: primero en el
    /// espacio de tipos del módulo (un `summon` lo deja ahí) y, si la ruta es
    /// multi-segmento, recorriendo los módulos (`std::opera::Add`).
    fn pact_def(&self, module: ModuleId, path: &[String]) -> Option<DefId> {
        let scope = self.krate.modules[module.index()].scope;
        let res = if path.len() == 1 {
            if path[0] == "Show" {
                self.krate.show_pact.map(Res::Def)
            } else {
                self.lookup_type(scope, &path[0]).map(|binding| binding.res)
            }
        } else {
            let (prefix, last) = path.split_at(path.len() - 1);
            self.find_module_path(module, prefix)
                .and_then(|target| self.lookup_in_module(target, &last[0]))
                .map(|binding| binding.res)
        };
        match res {
            Some(Res::Def(def)) if self.krate.defs[def.index()].kind == DefKind::Pact => Some(def),
            _ => None,
        }
    }

    fn build_const(&mut self, module: ModuleId, constant: &Const) {
        let kind = match constant.kind {
            ConstKind::Sigil => DefKind::Const,
            ConstKind::Relic => DefKind::Static,
        };
        let vis = if constant.unveil {
            Visibility::Public
        } else {
            Visibility::Private
        };
        let def = self.create_def(module, kind, &constant.name, vis, constant.span);
        self.pending.push(Pending::Const {
            def,
            module,
            ty: constant.ty.clone(),
            value: constant.value.clone(),
        });
    }

    fn resolve_imports(&mut self) {
        let imports = std::mem::take(&mut self.imports);
        for import in imports {
            self.resolve_import(&import);
        }
        self.resolve_pending_pacts();
        self.detect_module_cycles();
    }

    /// Segunda pasada de los `ritual … for Pacto` cuyo pacto se importó con
    /// `summon` después de bajar el item.
    fn resolve_pending_pacts(&mut self) {
        let pending = std::mem::take(&mut self.pending_pacts);
        for (index, module, path, span) in pending {
            match self.pact_def(module, &path) {
                Some(def) => self.krate.impls[index].pact = Some(def),
                None => self.error(
                    "PGS-E1303",
                    format!("`{}` no es un pact", path.join("::")),
                    span,
                ),
            }
        }
    }

    fn detect_module_cycles(&mut self) {
        fn visit(
            node: ModuleId,
            adjacency: &[Vec<(ModuleId, Span)>],
            colors: &mut [u8],
            diagnostics: &mut Vec<Diagnostic>,
        ) {
            colors[node.index()] = 1;
            for (next, span) in &adjacency[node.index()] {
                match colors[next.index()] {
                    0 => visit(*next, adjacency, colors, diagnostics),
                    1 => diagnostics.push(Diagnostic::error(
                        "PGS-E2012",
                        "ciclo de módulos detectado",
                        *span,
                    )),
                    _ => {}
                }
            }
            colors[node.index()] = 2;
        }

        let mut adjacency: Vec<Vec<(ModuleId, Span)>> = vec![Vec::new(); self.krate.modules.len()];
        for (from, to, span) in &self.module_edges {
            adjacency[from.index()].push((*to, *span));
        }

        let mut colors = vec![0u8; self.krate.modules.len()];
        for module in &self.krate.modules {
            if colors[module.id.index()] == 0 {
                visit(
                    module.id,
                    &adjacency,
                    &mut colors,
                    &mut self.krate.diagnostics,
                );
            }
        }
    }

    fn resolve_import(&mut self, import: &PendingImport) {
        let module = import.module;
        let path = &import.summon.path;
        let span = import.summon.span;

        let target = if let Some(target_module) = self.find_module_path(module, path) {
            self.krate.modules[target_module.index()]
                .def
                .map_or(Res::Error, Res::Def)
        } else if path.is_empty() {
            Res::Error
        } else {
            let (prefix, last) = path.split_at(path.len() - 1);
            let Some(target_module) = self.find_module_path(module, prefix) else {
                if prefix.is_empty() {
                    self.error(
                        "PGS-E2004",
                        format!("no se encuentra `{}`", path.join("::")),
                        span,
                    );
                } else {
                    self.error(
                        "PGS-E2003",
                        format!("no se encuentra el módulo `{}`", prefix.join("::")),
                        span,
                    );
                }
                return;
            };
            let Some(binding) = self.lookup_in_module(target_module, &last[0]) else {
                // Los tipos integrados viven en `std` de forma nominal:
                // `summon std::ffi::CString` importa el tipo del núcleo.
                if let Some(res) = primitive_type(&last[0]) {
                    return self.bind_import(import, res);
                }
                self.error(
                    "PGS-E2004",
                    format!("no se encuentra `{}`", path.join("::")),
                    span,
                );
                return;
            };
            if let Res::Def(def) = binding.res {
                if !self.can_access(module, def) {
                    self.error("PGS-E2006", format!("`{}` es privado", last[0]), span);
                    return;
                }
            }
            binding.res
        };

        self.bind_import(import, target);
    }

    fn bind_import(&mut self, import: &PendingImport, target: Res) {
        let module = import.module;
        let path = &import.summon.path;
        let span = import.summon.span;
        // Tipos integrados importados a través de `std`: `std::ffi::CString`.
        if let Res::Primitive(_) = target {
            let name = import
                .summon
                .alias
                .clone()
                .unwrap_or_else(|| path.last().cloned().unwrap_or_default());
            let scope = self.krate.modules[module.index()].scope;
            self.krate.scopes[scope.index()]
                .types
                .insert(name, Binding { res: target, span });
            return;
        }
        let Some((namespace, target_module)) = self.import_namespace(target) else {
            self.error(
                "PGS-E2004",
                format!("no se encuentra `{}`", path.join("::")),
                span,
            );
            return;
        };
        self.module_edges.push((module, target_module, span));
        let name = import
            .summon
            .alias
            .clone()
            .unwrap_or_else(|| path.last().cloned().unwrap_or_default());
        let scope = self.krate.modules[module.index()].scope;
        let map = match namespace {
            Namespace::Value => &mut self.krate.scopes[scope.index()].values,
            Namespace::Type => &mut self.krate.scopes[scope.index()].types,
            Namespace::Module => &mut self.krate.scopes[scope.index()].modules,
        };
        if map.contains_key(&name) {
            self.error("PGS-E2005", format!("`{name}` ya está importado"), span);
            return;
        }
        if namespace != Namespace::Module {
            if let Res::Def(def) = target {
                self.imported.push((def, name.clone(), span));
            }
        }
        map.insert(name, Binding { res: target, span });
    }

    fn import_namespace(&self, res: Res) -> Option<(Namespace, ModuleId)> {
        match res {
            Res::Def(def) => {
                let definition = &self.krate.defs[def.index()];
                let target_module = if definition.kind == DefKind::Module {
                    self.krate
                        .modules
                        .iter()
                        .find(|module| module.def == Some(def))
                        .map_or(definition.module, |module| module.id)
                } else {
                    definition.module
                };
                Some((definition.kind.namespace(), target_module))
            }
            _ => None,
        }
    }

    fn resolve_pending(&mut self) {
        let pending = std::mem::take(&mut self.pending);
        for item in pending {
            match item {
                Pending::Type { module, ty } => {
                    let scope = self.krate.modules[module.index()].scope;
                    let mut scratch = Body {
                        id: BodyId(0),
                        owner: DefId(0),
                        params: Vec::new(),
                        locals: Vec::new(),
                        resolutions: Vec::new(),
                        self_ty: None,
                        ast: None,
                        self_local: None,
                    };
                    self.resolve_type(&ty, module, scope, None, &mut scratch);
                }
                Pending::Const {
                    def,
                    module,
                    ty,
                    value,
                } => {
                    let scope = self.krate.modules[module.index()].scope;
                    let mut body = Body {
                        id: BodyId(next_id(self.krate.bodies.len())),
                        owner: def,
                        params: Vec::new(),
                        locals: Vec::new(),
                        resolutions: Vec::new(),
                        self_ty: None,
                        ast: None,
                        self_local: None,
                    };
                    self.resolve_type(&ty, module, scope, None, &mut body);
                    if let Some(value) = &value {
                        self.resolve_expr(value, module, scope, None, &mut body);
                    }
                    self.krate.bodies.push(body);
                    self.krate.consts.insert(
                        def,
                        crate::hir::ConstDef {
                            def,
                            module,
                            ty,
                            value,
                        },
                    );
                }
                Pending::Function {
                    def,
                    module,
                    receiver,
                    params,
                    ret,
                    body,
                    self_ty,
                    generics,
                    parent_scope,
                } => {
                    self.resolve_function(
                        def,
                        module,
                        receiver.as_ref(),
                        &params,
                        &ret,
                        &body,
                        self_ty.as_ref(),
                        &generics,
                        parent_scope,
                    );
                }
                Pending::Signature {
                    def,
                    module,
                    receiver,
                    params,
                    ret,
                    self_ty,
                    parent_scope,
                } => {
                    self.resolve_signature(
                        def,
                        module,
                        receiver.as_ref(),
                        &params,
                        &ret,
                        self_ty.as_ref(),
                        parent_scope,
                    );
                }
            }
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn resolve_signature(
        &mut self,
        def: DefId,
        module: ModuleId,
        receiver: Option<&Receiver>,
        params: &[Param],
        ret: &Type,
        self_ty: Option<&Type>,
        parent_scope: Option<ScopeId>,
    ) {
        let module_scope = self.krate.modules[module.index()].scope;
        let parent = parent_scope.unwrap_or(module_scope);
        let body_scope = self.new_scope(Some(parent), ScopeKind::Body);
        let mut body = Body {
            id: BodyId(next_id(self.krate.bodies.len())),
            owner: def,
            params: Vec::new(),
            locals: Vec::new(),
            resolutions: Vec::new(),
            self_ty: None,
            ast: None,
            self_local: None,
        };

        if let Some(self_ty) = self_ty {
            let res = self.resolve_type_res(self_ty, module, body_scope, None, &mut body);
            body.self_ty = Some(res);
            let mutable = matches!(
                receiver,
                Some(pengu_syntax::ast::Receiver::Mut | pengu_syntax::ast::Receiver::Own)
            );
            let local = Self::new_local(&mut body, "self", mutable, self_ty.span);
            body.self_local = Some(local);
        }

        for param in params {
            self.resolve_type(&param.ty, module, body_scope, body.self_ty, &mut body);
            let local = Self::new_local(&mut body, &param.name, false, param.span);
            if !self.bind_in_scope(
                body_scope,
                Namespace::Value,
                &param.name,
                Res::Local(local),
                param.span,
            ) {
                self.error(
                    "PGS-E1102",
                    format!("`{}` ya está declarado en este bloque", param.name),
                    param.span,
                );
            }
            body.params.push(local);
            body.resolutions.push(Resolution {
                span: param.span,
                res: Res::Local(local),
            });
        }

        self.resolve_type(ret, module, body_scope, body.self_ty, &mut body);
        self.krate.bodies.push(body);
        self.krate.signatures.insert(
            def,
            Signature {
                params: params.iter().map(|param| param.ty.clone()).collect(),
                ret: ret.clone(),
                receiver: receiver.copied(),
                generics: Vec::new(),
            },
        );
    }

    #[allow(clippy::too_many_arguments)]
    fn resolve_function(
        &mut self,
        def: DefId,
        module: ModuleId,
        receiver: Option<&Receiver>,
        params: &[Param],
        ret: &Type,
        block: &Block,
        self_ty: Option<&Type>,
        generics: &[TypeParam],
        parent_scope: Option<ScopeId>,
    ) {
        let module_scope = self.krate.modules[module.index()].scope;
        let parent = parent_scope.unwrap_or(module_scope);
        let body_scope = self.new_scope(Some(parent), ScopeKind::Body);
        let mut body = Body {
            id: BodyId(next_id(self.krate.bodies.len())),
            owner: def,
            params: Vec::new(),
            locals: Vec::new(),
            resolutions: Vec::new(),
            self_ty: None,
            ast: None,
            self_local: None,
        };

        if let Some(self_ty) = self_ty {
            let res = self.resolve_type_res(self_ty, module, body_scope, None, &mut body);
            body.self_ty = Some(res);
            let mutable = matches!(
                receiver,
                Some(pengu_syntax::ast::Receiver::Mut | pengu_syntax::ast::Receiver::Own)
            );
            let local = Self::new_local(&mut body, "self", mutable, self_ty.span);
            body.self_local = Some(local);
        }

        let generic_params = self.bind_generics(module, body_scope, generics, &mut body);

        for param in params {
            self.resolve_type(&param.ty, module, body_scope, body.self_ty, &mut body);
            let local = Self::new_local(&mut body, &param.name, false, param.span);
            if !self.bind_in_scope(
                body_scope,
                Namespace::Value,
                &param.name,
                Res::Local(local),
                param.span,
            ) {
                self.error(
                    "PGS-E1102",
                    format!("`{}` ya está declarado en este bloque", param.name),
                    param.span,
                );
            }
            body.params.push(local);
            body.resolutions.push(Resolution {
                span: param.span,
                res: Res::Local(local),
            });
        }

        self.resolve_type(ret, module, body_scope, body.self_ty, &mut body);
        self.resolve_block(block, module, body_scope, &mut body);
        body.ast = Some(block.clone());
        self.krate.bodies.push(body);
        self.krate.signatures.insert(
            def,
            Signature {
                params: params.iter().map(|param| param.ty.clone()).collect(),
                ret: ret.clone(),
                receiver: receiver.copied(),
                generics: generic_params,
            },
        );
    }

    fn bind_generics(
        &mut self,
        module: ModuleId,
        scope: ScopeId,
        params: &[TypeParam],
        body: &mut Body,
    ) -> Vec<GenericParam> {
        let mut out = Vec::with_capacity(params.len());
        for param in params {
            let def = DefId(next_id(self.krate.defs.len()));
            self.krate.defs.push(Def {
                id: def,
                kind: DefKind::Generic,
                name: param.name.clone(),
                vis: Visibility::Private,
                span: param.span,
                module,
            });
            if !self.bind_in_scope(
                scope,
                Namespace::Type,
                &param.name,
                Res::Def(def),
                param.span,
            ) {
                self.error(
                    "PGS-E1102",
                    format!("`{}` ya está declarado en este bloque", param.name),
                    param.span,
                );
            }
            out.push(GenericParam {
                def,
                name: param.name.clone(),
                bounds: Vec::new(),
            });
        }
        for (param, generic) in params.iter().zip(&mut out) {
            for bound in &param.bounds {
                // Los pactos integrados (`Ord`, `Eq`, `Show`, …) están siempre
                // disponibles: los módulos de `std` no pueden importarse entre sí
                // (N42), así que sin este atajo `[T: Ord]` no se puede escribir
                // dentro de la propia stdlib (N65).
                let res = match self.builtin_pact(bound) {
                    Some(def) => Res::Def(def),
                    None => self.resolve_type_path(bound, module, scope, param.span, body),
                };
                match res {
                    Res::Def(def) if self.krate.defs[def.index()].kind == DefKind::Pact => {
                        generic.bounds.push(def);
                    }
                    Res::Error => {}
                    _ => {
                        self.error(
                            "PGS-E1303",
                            format!("`{}` no es un pact", bound.join("::")),
                            param.span,
                        );
                    }
                }
            }
        }
        out
    }

    /// Resuelve un pacto integrado por nombre (`Ord`, `Eq`, `Show`, `Clone`),
    /// sin depender de que el módulo que lo declara esté importado.
    fn builtin_pact(&self, path: &[String]) -> Option<DefId> {
        if path.len() != 1 {
            return None;
        }
        let name = path[0].as_str();
        if !matches!(name, "Ord" | "Eq" | "Show" | "Clone" | "Hash") {
            return None;
        }
        self.krate
            .pacts
            .keys()
            .copied()
            .find(|def| self.krate.defs[def.index()].name == name)
    }

    fn new_local(body: &mut Body, name: &str, mutable: bool, span: Span) -> LocalId {
        let id = LocalId(next_id(body.locals.len()));
        body.locals.push(Local {
            id,
            name: name.to_owned(),
            mutable,
            span,
        });
        id
    }

    fn resolve_block(&mut self, block: &Block, module: ModuleId, parent: ScopeId, body: &mut Body) {
        let scope = self.new_scope(Some(parent), ScopeKind::Block);
        for stmt in &block.stmts {
            self.resolve_stmt(stmt, module, scope, body);
        }
    }

    fn resolve_stmt(&mut self, stmt: &Stmt, module: ModuleId, scope: ScopeId, body: &mut Body) {
        match &stmt.kind {
            StmtKind::Bind {
                mutable,
                pattern,
                ty,
                value,
                else_block,
            } => {
                if let Some(ty) = ty {
                    self.resolve_type(ty, module, scope, body.self_ty, body);
                }
                self.resolve_expr(value, module, scope, body.self_ty, body);
                if let Some(else_block) = else_block {
                    self.resolve_block(else_block, module, scope, body);
                }
                self.bind_pattern(pattern, module, scope, body, *mutable);
            }
            StmtKind::Assign { target, value } => {
                self.resolve_expr(target, module, scope, body.self_ty, body);
                self.resolve_expr(value, module, scope, body.self_ty, body);
            }
            StmtKind::Expr(expr) => self.resolve_expr(expr, module, scope, body.self_ty, body),
            StmtKind::While {
                cond,
                body: loop_body,
            } => {
                self.resolve_expr(cond, module, scope, body.self_ty, body);
                self.resolve_block(loop_body, module, scope, body);
            }
            StmtKind::For {
                pattern,
                iter,
                body: loop_body,
            } => {
                self.resolve_expr(iter, module, scope, body.self_ty, body);
                let for_scope = self.new_scope(Some(scope), ScopeKind::For);
                self.bind_pattern(pattern, module, for_scope, body, false);
                self.resolve_block(loop_body, module, for_scope, body);
            }
            StmtKind::Return(expr) | StmtKind::Break(expr) => {
                if let Some(expr) = expr {
                    self.resolve_expr(expr, module, scope, body.self_ty, body);
                }
            }
            StmtKind::Continue => {}
        }
    }

    #[allow(clippy::match_same_arms, clippy::too_many_lines)]
    fn bind_pattern(
        &mut self,
        pattern: &Pattern,
        module: ModuleId,
        scope: ScopeId,
        body: &mut Body,
        mutable: bool,
    ) {
        match &pattern.kind {
            PatternKind::Path(path) if path.len() == 1 => {
                if let Some(res) = primitive_value(&path[0]) {
                    body.resolutions.push(Resolution {
                        span: pattern.span,
                        res,
                    });
                } else if path[0].starts_with(|c: char| c.is_ascii_uppercase()) {
                    // Una variante unitaria (`when Zero`) se busca primero en el
                    // espacio de valores; solo si no hay variante se interpreta
                    // como un tipo.
                    let variant = self
                        .lookup_value(scope, &path[0])
                        .map(|binding| binding.res)
                        .filter(|res| match res {
                            Res::Def(def) => self.krate.variant_owner(*def).is_some(),
                            _ => false,
                        })
                        .or_else(|| self.unqualified_variant(&path[0]).map(Res::Def));
                    let res = match variant {
                        Some(res) => res,
                        None => {
                            self.resolve_type_path(&path[..], module, scope, pattern.span, body)
                        }
                    };
                    body.resolutions.push(Resolution {
                        span: pattern.span,
                        res,
                    });
                } else {
                    if self.lookup_value(scope, &path[0]).is_some() {
                        self.krate.diagnostics.push(Diagnostic::warning(
                            "PGS-W1102",
                            format!("`{}` sombrea un binding anterior", path[0]),
                            pattern.span,
                        ));
                    }
                    let local = Self::new_local(body, &path[0], mutable, pattern.span);
                    body.resolutions.push(Resolution {
                        span: pattern.span,
                        res: Res::Local(local),
                    });
                    if !self.bind_in_scope(
                        scope,
                        Namespace::Value,
                        &path[0],
                        Res::Local(local),
                        pattern.span,
                    ) {
                        self.error(
                            "PGS-E1102",
                            format!("`{}` ya está declarado en este bloque", path[0]),
                            pattern.span,
                        );
                    }
                }
            }
            PatternKind::Path(path) => {
                let variant = if path.len() == 2 {
                    self.qualified_variant(scope, &path[0], &path[1])
                } else if path.len() == 1 {
                    self.unqualified_variant(&path[0])
                } else {
                    None
                };
                let res = match variant {
                    Some(variant) => Res::Def(variant),
                    None => self.resolve_type_path(path, module, scope, pattern.span, body),
                };
                body.resolutions.push(Resolution {
                    span: pattern.span,
                    res,
                });
            }
            PatternKind::Bind { name, pattern } => {
                let local = Self::new_local(body, name, mutable, pattern.span);
                body.resolutions.push(Resolution {
                    span: pattern.span,
                    res: Res::Local(local),
                });
                if !self.bind_in_scope(
                    scope,
                    Namespace::Value,
                    name,
                    Res::Local(local),
                    pattern.span,
                ) {
                    self.error(
                        "PGS-E1102",
                        format!("`{name}` ya está declarado en este bloque"),
                        pattern.span,
                    );
                }
                self.bind_pattern(pattern, module, scope, body, mutable);
            }
            PatternKind::Tuple(patterns) | PatternKind::Slice(patterns) => {
                for pattern in patterns {
                    self.bind_pattern(pattern, module, scope, body, mutable);
                }
            }
            PatternKind::Variant { path, args, named } => {
                if let Some(variant) = if path.len() == 2 {
                    self.qualified_variant(scope, &path[0], &path[1])
                } else {
                    None
                } {
                    body.resolutions.push(Resolution {
                        span: pattern.span,
                        res: Res::Def(variant),
                    });
                } else if path.len() == 1 {
                    if let Some(res) = primitive_value(&path[0]) {
                        body.resolutions.push(Resolution {
                            span: pattern.span,
                            res,
                        });
                    } else {
                        // `when some(value)`: el nombre de la variante vive en el
                        // espacio de valores, no en el de tipos.
                        let variant = self
                            .lookup_value(scope, &path[0])
                            .map(|binding| binding.res)
                            .filter(|res| match res {
                                Res::Def(def) => self.krate.variant_owner(*def).is_some(),
                                _ => false,
                            })
                            .or_else(|| self.unqualified_variant(&path[0]).map(Res::Def));
                        let res = match variant {
                            Some(res) => res,
                            None => self.resolve_type_path(path, module, scope, pattern.span, body),
                        };
                        body.resolutions.push(Resolution {
                            span: pattern.span,
                            res,
                        });
                    }
                } else {
                    let res = self.resolve_type_path(path, module, scope, pattern.span, body);
                    body.resolutions.push(Resolution {
                        span: pattern.span,
                        res,
                    });
                }
                for pattern in args {
                    self.bind_pattern(pattern, module, scope, body, mutable);
                }
                for (_, pattern) in named {
                    self.bind_pattern(pattern, module, scope, body, mutable);
                }
            }
            PatternKind::Or(patterns) => {
                if let Some(first) = patterns.first() {
                    self.bind_pattern(first, module, scope, body, mutable);
                }
            }
            PatternKind::Range { start, end, .. } => {
                self.bind_pattern(start, module, scope, body, mutable);
                if let Some(end) = end {
                    self.bind_pattern(end, module, scope, body, mutable);
                }
            }
            PatternKind::Literal(expr) => {
                self.resolve_expr(expr, module, scope, body.self_ty, body);
            }
            PatternKind::Wildcard | PatternKind::Rest => {}
        }
    }

    #[allow(clippy::too_many_lines)]
    fn resolve_expr(
        &mut self,
        expr: &Expr,
        module: ModuleId,
        scope: ScopeId,
        self_ty: Option<Res>,
        body: &mut Body,
    ) {
        match &expr.kind {
            ExprKind::Path(path) => {
                let res = self.resolve_path_value(path, module, scope, expr.span, body);
                body.resolutions.push(Resolution {
                    span: expr.span,
                    res,
                });
            }
            ExprKind::Record { path, fields, base } => {
                let res = self.resolve_type_path(path, module, scope, expr.span, body);
                body.resolutions.push(Resolution {
                    span: expr.span,
                    res,
                });
                if let Some(base) = base {
                    self.resolve_expr(base, module, scope, self_ty, body);
                }
                for (_, value) in fields {
                    self.resolve_expr(value, module, scope, self_ty, body);
                }
            }
            ExprKind::Tuple(exprs)
            | ExprKind::Array(exprs)
            | ExprKind::Vector(exprs)
            | ExprKind::Set(exprs) => {
                for expr in exprs {
                    self.resolve_expr(expr, module, scope, self_ty, body);
                }
            }
            ExprKind::ArrayRepeat { value, count } => {
                self.resolve_expr(value, module, scope, self_ty, body);
                self.resolve_expr(count, module, scope, self_ty, body);
            }
            ExprKind::Map(entries) => {
                for (key, value) in entries {
                    self.resolve_expr(key, module, scope, self_ty, body);
                    self.resolve_expr(value, module, scope, self_ty, body);
                }
            }
            ExprKind::Unary { expr, .. } | ExprKind::Try(expr) | ExprKind::Ref { expr, .. } => {
                self.resolve_expr(expr, module, scope, self_ty, body);
            }
            ExprKind::Binary { lhs, rhs, .. } => {
                self.resolve_expr(lhs, module, scope, self_ty, body);
                self.resolve_expr(rhs, module, scope, self_ty, body);
            }
            ExprKind::Range { start, end, .. } => {
                self.resolve_expr(start, module, scope, self_ty, body);
                if let Some(end) = end {
                    self.resolve_expr(end, module, scope, self_ty, body);
                }
            }
            ExprKind::Cast { expr, ty } => {
                self.resolve_expr(expr, module, scope, self_ty, body);
                self.resolve_type(ty, module, scope, self_ty, body);
            }
            ExprKind::Call { callee, args } => {
                self.resolve_expr(callee, module, scope, self_ty, body);
                for arg in args {
                    self.resolve_expr(arg, module, scope, self_ty, body);
                }
            }
            ExprKind::Index { base, index } => {
                self.resolve_expr(base, module, scope, self_ty, body);
                let generic_callee = matches!(&base.kind, ExprKind::Path(_))
                    && body.resolutions.iter().rev().any(|resolution| {
                        resolution.span == base.span
                            && matches!(
                                resolution.res,
                                Res::Def(def)
                                    if self.krate.defs[def.index()].kind == DefKind::Function
                                        && self.krate.signature(def).is_some_and(|sig| !sig.generics.is_empty())
                            )
                    });
                if !generic_callee {
                    self.resolve_expr(index, module, scope, self_ty, body);
                }
            }
            ExprKind::Field { base, name } => {
                if let ExprKind::Path(path) = &base.kind {
                    if path.len() == 1 {
                        if let Some(variant) = self.qualified_variant(scope, &path[0], name) {
                            body.resolutions.push(Resolution {
                                span: expr.span,
                                res: Res::Def(variant),
                            });
                            self.resolve_expr(base, module, scope, self_ty, body);
                            return;
                        }
                    }
                    // `modulo.item`: un módulo importado con `summon` cualifica
                    // funciones y constantes (`fs.read_to_string`, `env.args`).
                    if let Some(target) = self.find_module_path(module, path) {
                        if let Some(binding) = self.lookup_in_module(target, name) {
                            if let Res::Def(def) = binding.res {
                                if !self.can_access(module, def) {
                                    self.error(
                                        "PGS-E2006",
                                        format!("`{name}` es privado"),
                                        expr.span,
                                    );
                                }
                            }
                            body.resolutions.push(Resolution {
                                span: expr.span,
                                res: binding.res,
                            });
                            return;
                        }
                    }
                }
                self.resolve_expr(base, module, scope, self_ty, body);
            }
            ExprKind::If {
                cond,
                then_branch,
                else_branch,
                ..
            } => {
                self.resolve_expr(cond, module, scope, self_ty, body);
                self.resolve_block(then_branch, module, scope, body);
                if let Some(else_branch) = else_branch {
                    self.resolve_block(else_branch, module, scope, body);
                }
            }
            ExprKind::Match { scrutinee, arms } => {
                self.resolve_expr(scrutinee, module, scope, self_ty, body);
                for arm in arms {
                    let arm_scope = self.new_scope(Some(scope), ScopeKind::MatchArm);
                    if let Some(pattern) = &arm.pattern {
                        self.bind_pattern(pattern, module, arm_scope, body, false);
                    }
                    if let Some(guard) = &arm.guard {
                        self.resolve_expr(guard, module, arm_scope, self_ty, body);
                    }
                    self.resolve_block(&arm.body, module, arm_scope, body);
                }
            }
            ExprKind::Do(block) | ExprKind::Loop(block) | ExprKind::Curse(block) => {
                self.resolve_block(block, module, scope, body);
            }
            ExprKind::Lambda {
                params,
                body: lambda_body,
            } => {
                let lambda_scope = self.new_scope(Some(scope), ScopeKind::Lambda);
                for param in params {
                    self.resolve_type(&param.ty, module, lambda_scope, self_ty, body);
                    let local = Self::new_local(body, &param.name, false, param.span);
                    body.resolutions.push(crate::Resolution {
                        span: param.span,
                        res: Res::Local(local),
                    });
                    if !self.bind_in_scope(
                        lambda_scope,
                        Namespace::Value,
                        &param.name,
                        Res::Local(local),
                        param.span,
                    ) {
                        self.error(
                            "PGS-E1102",
                            format!("`{}` ya está declarado en este bloque", param.name),
                            param.span,
                        );
                    }
                }
                self.resolve_block(lambda_body, module, lambda_scope, body);
            }
            ExprKind::String(lit) => {
                for part in &lit.parts {
                    if let pengu_syntax::ast::StringPart::Expr(inner) = part {
                        self.resolve_expr(inner, module, scope, self_ty, body);
                    }
                }
            }
            ExprKind::Unit
            | ExprKind::Bool(_)
            | ExprKind::None
            | ExprKind::Int(_)
            | ExprKind::Float(_)
            | ExprKind::Char(_)
            | ExprKind::ByteChar(_)
            | ExprKind::SelfValue => {}
        }
    }

    fn resolve_type(
        &mut self,
        ty: &Type,
        module: ModuleId,
        scope: ScopeId,
        self_ty: Option<Res>,
        body: &mut Body,
    ) {
        let res = self.resolve_type_res(ty, module, scope, self_ty, body);
        body.resolutions.push(Resolution { span: ty.span, res });
    }

    fn resolve_type_res(
        &mut self,
        ty: &Type,
        module: ModuleId,
        scope: ScopeId,
        self_ty: Option<Res>,
        body: &mut Body,
    ) -> Res {
        match &ty.kind {
            TypeKind::Unit => Res::Primitive(Primitive::Unit),
            TypeKind::Option(inner) | TypeKind::Slice(inner) | TypeKind::Ptr(inner) => {
                self.resolve_type(inner, module, scope, self_ty, body);
                match ty.kind {
                    TypeKind::Option(_) => Res::Primitive(Primitive::Option),
                    TypeKind::Slice(_) => Res::Primitive(Primitive::Slice),
                    _ => Res::Primitive(Primitive::Ptr),
                }
            }
            TypeKind::Ref { inner, .. } => {
                self.resolve_type(inner, module, scope, self_ty, body);
                Res::Primitive(Primitive::Ref)
            }
            TypeKind::Array { elem, len } => {
                self.resolve_type(elem, module, scope, self_ty, body);
                self.resolve_expr(len, module, scope, self_ty, body);
                Res::Primitive(Primitive::Array)
            }
            TypeKind::Tuple(types) => {
                for ty in types {
                    self.resolve_type(ty, module, scope, self_ty, body);
                }
                Res::Primitive(Primitive::Tuple)
            }
            TypeKind::Fn { params, ret } => {
                for ty in params {
                    self.resolve_type(ty, module, scope, self_ty, body);
                }
                self.resolve_type(ret, module, scope, self_ty, body);
                Res::Primitive(Primitive::Fn)
            }
            TypeKind::Path { segments, args } => {
                for arg in args {
                    self.resolve_type(arg, module, scope, self_ty, body);
                }
                self.resolve_type_path(segments, module, scope, ty.span, body)
            }
            TypeKind::SelfType => self_ty.unwrap_or_else(|| {
                self.error("PGS-E1209", "`Self` fuera de un `pact` o `ritual`", ty.span);
                Res::Error
            }),
        }
    }

    fn resolve_type_path(
        &mut self,
        segments: &[String],
        module: ModuleId,
        scope: ScopeId,
        span: Span,
        body: &mut Body,
    ) -> Res {
        if segments.len() == 1 {
            if let Some(res) = primitive_type(&segments[0]) {
                return res;
            }
            if let Some(binding) = self.lookup_type(scope, &segments[0]) {
                return binding.res;
            }
            self.error(
                "PGS-E2004",
                format!("no se encuentra el tipo `{}`", segments[0]),
                span,
            );
            return Res::Error;
        }
        if segments.is_empty() {
            self.error("PGS-E2004", "se esperaba un path de tipo", span);
            return Res::Error;
        }
        let (prefix, last) = segments.split_at(segments.len() - 1);
        let Some(target_module) = self.find_module_path(module, prefix) else {
            self.error(
                "PGS-E2004",
                format!("no se encuentra `{}`", segments.join("::")),
                span,
            );
            return Res::Error;
        };
        let binding = self.krate.scopes[self.krate.modules[target_module.index()].scope.index()]
            .types
            .get(&last[0])
            .cloned();
        let Some(binding) = binding else {
            self.error(
                "PGS-E2004",
                format!("no se encuentra el tipo `{}`", segments.join("::")),
                span,
            );
            return Res::Error;
        };
        if let Res::Def(def) = binding.res {
            if !self.can_access(module, def) {
                self.error("PGS-E2006", format!("`{}` es privado", last[0]), span);
                return Res::Error;
            }
        }
        let _ = body;
        binding.res
    }

    fn resolve_path_value(
        &mut self,
        path: &[String],
        module: ModuleId,
        scope: ScopeId,
        span: Span,
        body: &mut Body,
    ) -> Res {
        if path.is_empty() {
            return Res::Error;
        }
        if path.len() == 1 {
            if let Some(binding) = self.lookup_value(scope, &path[0]) {
                return binding.res;
            }
            if let Some(res) = primitive_value(&path[0]) {
                return res;
            }
            if let Some(binding) = self.lookup_type(scope, &path[0]) {
                return binding.res;
            }
            if let Some(res) = primitive_type(&path[0]) {
                return res;
            }
            self.error("PGS-E2004", format!("no se encuentra `{}`", path[0]), span);
            return Res::Error;
        }
        let (prefix, last) = path.split_at(path.len() - 1);
        let Some(target_module) = self.find_module_path(module, prefix) else {
            self.error(
                "PGS-E2004",
                format!("no se encuentra `{}`", path.join("::")),
                span,
            );
            return Res::Error;
        };
        let Some(binding) = self.lookup_in_module(target_module, &last[0]) else {
            self.error(
                "PGS-E2004",
                format!("no se encuentra `{}`", path.join("::")),
                span,
            );
            return Res::Error;
        };
        if let Res::Def(def) = binding.res {
            if !self.can_access(module, def) {
                self.error("PGS-E2006", format!("`{}` es privado", last[0]), span);
                return Res::Error;
            }
        }
        let _ = body;
        binding.res
    }

    fn lookup_value(&self, scope: ScopeId, name: &str) -> Option<Binding> {
        let mut current = Some(scope);
        while let Some(id) = current {
            let scope = &self.krate.scopes[id.index()];
            if let Some(binding) = scope.values.get(name) {
                return Some(binding.clone());
            }
            current = scope.parent;
        }
        None
    }

    fn lookup_type(&self, scope: ScopeId, name: &str) -> Option<Binding> {
        let mut current = Some(scope);
        while let Some(id) = current {
            let scope = &self.krate.scopes[id.index()];
            if let Some(binding) = scope.types.get(name) {
                return Some(binding.clone());
            }
            current = scope.parent;
        }
        None
    }

    /// `Tipo.Variante`: variante unitaria de un `enchanting` visible por nombre.
    fn qualified_variant(
        &self,
        scope: ScopeId,
        adt_name: &str,
        variant_name: &str,
    ) -> Option<DefId> {
        let Res::Def(adt_def) = self.lookup_type(scope, adt_name)?.res else {
            return None;
        };
        let adt = self.krate.adt(adt_def)?;
        adt.variants
            .iter()
            .find(|variant| self.krate.def(variant.def).name == variant_name)
            .map(|variant| variant.def)
    }

    /// Variante unitaria `Nombre` visible sin calificar en una suma única.
    fn unqualified_variant(&self, name: &str) -> Option<DefId> {
        let mut found = None;
        for adt in self.krate.adts.values() {
            for variant in &adt.variants {
                if self.krate.def(variant.def).name == name {
                    if found.is_some() {
                        // Ambiguo: no se adivina.
                        return None;
                    }
                    found = Some(variant.def);
                }
            }
        }
        found
    }

    fn lookup_in_module(&self, module: ModuleId, name: &str) -> Option<Binding> {
        let scope = self.krate.modules[module.index()].scope;
        self.krate.scopes[scope.index()]
            .types
            .get(name)
            .or_else(|| self.krate.scopes[scope.index()].values.get(name))
            .or_else(|| self.krate.scopes[scope.index()].modules.get(name))
            .cloned()
    }

    fn find_module_path(&self, current: ModuleId, path: &[String]) -> Option<ModuleId> {
        if path.is_empty() {
            return Some(current);
        }
        let mut module = current;
        let mut index = 0;
        match path[0].as_str() {
            "crate" => {
                module = self.krate.root;
                index = 1;
            }
            "super" => {
                module = self.krate.modules[module.index()].parent?;
                index = 1;
            }
            "self" => index = 1,
            _ => {}
        }
        for segment in &path[index..] {
            let scope = self.krate.modules[module.index()].scope;
            let binding = self.krate.scopes[scope.index()].modules.get(segment)?;
            let Res::Def(def) = binding.res else {
                return None;
            };
            module = self.krate.modules.iter().find(|m| m.def == Some(def))?.id;
        }
        Some(module)
    }

    fn bind_in_scope(
        &mut self,
        scope: ScopeId,
        namespace: Namespace,
        name: &str,
        res: Res,
        span: Span,
    ) -> bool {
        let binding = Binding { res, span };
        let map = match namespace {
            Namespace::Value => &mut self.krate.scopes[scope.index()].values,
            Namespace::Type => &mut self.krate.scopes[scope.index()].types,
            Namespace::Module => &mut self.krate.scopes[scope.index()].modules,
        };
        if map.contains_key(name) {
            return false;
        }
        map.insert(name.to_owned(), binding);
        true
    }

    fn can_access(&self, from: ModuleId, def: DefId) -> bool {
        let def = &self.krate.defs[def.index()];
        if def.module == from {
            return true;
        }
        match def.vis {
            Visibility::Public | Visibility::Tome => true,
            Visibility::Private => false,
            Visibility::Scroll => {
                let Some(parent) = self.krate.modules[def.module.index()].parent else {
                    return false;
                };
                let mut current = Some(from);
                while let Some(module) = current {
                    if module == parent {
                        return true;
                    }
                    current = self.krate.modules[module.index()].parent;
                }
                false
            }
        }
    }
}

fn primitive_value(name: &str) -> Option<Res> {
    let primitive = match name {
        "print" => Primitive::Print,
        "format" => Primitive::Format,
        "assert" => Primitive::Assert,
        "panic" => Primitive::Panic,
        "assert_eq" => Primitive::AssertEq,
        "assert_ne" => Primitive::AssertNe,
        "some" | "Some" => Primitive::Some,
        "none" | "None" => Primitive::None,
        "ok" | "Ok" => Primitive::Ok,
        "err" | "Err" => Primitive::Err,
        "Less" | "Ordering.Less" => Primitive::OrderingLess,
        "Equal" | "Ordering.Equal" => Primitive::OrderingEqual,
        "Greater" | "Ordering.Greater" => Primitive::OrderingGreater,
        _ => return None,
    };
    Some(Res::Primitive(primitive))
}

fn primitive_type(name: &str) -> Option<Res> {
    let primitive = match name {
        "Bool" => Primitive::Bool,
        "Int" => Primitive::Int,
        "I8" => Primitive::I8,
        "I16" => Primitive::I16,
        "I32" => Primitive::I32,
        "I64" => Primitive::I64,
        "Isize" => Primitive::Isize,
        "U8" => Primitive::U8,
        "U16" => Primitive::U16,
        "U32" | "UInt" => Primitive::U32,
        "U64" => Primitive::U64,
        "Usize" => Primitive::Usize,
        "F32" => Primitive::F32,
        "F64" => Primitive::F64,
        "Float" => Primitive::Float,
        "Char" => Primitive::Char,
        "String" => Primitive::String,
        "Str" => Primitive::Str,
        "Unit" => Primitive::Unit,
        "Never" => Primitive::Never,
        "Vec" => Primitive::Vec,
        "Map" => Primitive::Map,
        "Set" => Primitive::Set,
        "Option" => Primitive::Option,
        "Result" => Primitive::Result,
        "Box" => Primitive::Box,
        "Rc" => Primitive::Rc,
        "Arc" => Primitive::Arc,
        "Ptr" => Primitive::Ptr,
        "CStr" => Primitive::CStr,
        "CString" => Primitive::CString,
        "Ordering" => Primitive::Ordering,
        "Range" => Primitive::Range,
        _ => return None,
    };
    Some(Res::Primitive(primitive))
}

fn type_name(ty: &Type) -> Option<String> {
    match &ty.kind {
        pengu_syntax::ast::TypeKind::Path { segments, .. } => segments.last().cloned(),
        _ => None,
    }
}

fn type_path_name(ty: &Type) -> Option<&str> {
    match &ty.kind {
        TypeKind::Path { segments, .. } => segments.last().map(String::as_str),
        _ => None,
    }
}
