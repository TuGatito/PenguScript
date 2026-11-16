//! Análisis de vivacidad para generar un state machine SSA por función.

use std::collections::{BTreeSet, HashSet};

use pengu_lir::{DestructureTarget, LBlock, LExpr, LFunction, LStmt, LTerm};

/// Locales vivos a la entrada de cada bloque.
pub fn liveness(function: &LFunction, self_local: Option<usize>) -> Vec<BTreeSet<usize>> {
    let n = function.blocks.len();
    let mut uses = vec![HashSet::new(); n];
    let mut defs = vec![HashSet::new(); n];
    for (i, block) in function.blocks.iter().enumerate() {
        block_uses_defs(block, self_local, &mut uses[i], &mut defs[i]);
    }

    let mut live_in = vec![BTreeSet::new(); n];
    loop {
        let mut changed = false;
        for i in (0..n).rev() {
            let mut out = HashSet::new();
            for succ in successors(&function.blocks[i].term) {
                if let Some(set) = live_in.get(succ) {
                    out.extend(set.iter().copied());
                }
            }
            let mut next = out;
            for def in &defs[i] {
                next.remove(def);
            }
            next.extend(uses[i].iter().copied());
            let next = next.into_iter().collect::<BTreeSet<_>>();
            if next != live_in[i] {
                live_in[i] = next;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    live_in
}

fn successors(term: &LTerm) -> Vec<usize> {
    match term {
        LTerm::Next { some, none, .. } => vec![*some, *none],
        LTerm::Goto(next) => vec![*next],
        LTerm::If(_, then_block, else_block) => vec![*then_block, *else_block],
        LTerm::Return(_) | LTerm::Panic(_) | LTerm::Unreachable => Vec::new(),
    }
}

fn block_uses_defs(
    block: &LBlock,
    self_local: Option<usize>,
    uses: &mut HashSet<usize>,
    defs: &mut HashSet<usize>,
) {
    // `uses` son usos *antes* de la primera definición dentro del bloque.
    for stmt in &block.stmts {
        match stmt {
            LStmt::Let(index, expr, _) | LStmt::Assign(index, expr, _) => {
                expr_uses(expr, self_local, defs, uses);
                defs.insert(*index);
            }
            LStmt::SetField(index, _, value, _) => {
                if self_local != Some(*index) && !defs.contains(index) {
                    uses.insert(*index);
                }
                expr_uses(value, self_local, defs, uses);
            }
            LStmt::Eval(expr, _) => expr_uses(expr, self_local, defs, uses),
            LStmt::Destructure(source, target, _) => {
                expr_uses(source, self_local, defs, uses);
                target_defs(target, defs);
            }
        }
    }
    match &block.term {
        LTerm::Next { iter, item, .. } => {
            if self_local != Some(*iter) && !defs.contains(iter) {
                uses.insert(*iter);
            }
            defs.insert(*item);
        }
        LTerm::Goto(_) => {}
        LTerm::If(cond, _, _) => expr_uses(cond, self_local, defs, uses),
        LTerm::Return(Some(expr)) => expr_uses(expr, self_local, defs, uses),
        LTerm::Return(None) | LTerm::Unreachable => {}
        LTerm::Panic(expr) => expr_uses(expr, self_local, defs, uses),
    }
}

fn target_defs(target: &DestructureTarget, defs: &mut HashSet<usize>) {
    match target {
        DestructureTarget::Local(index) => {
            defs.insert(*index);
        }
        DestructureTarget::Tuple(items) => {
            for item in items {
                target_defs(item, defs);
            }
        }
        DestructureTarget::Ignore => {}
    }
}

fn expr_uses(
    expr: &LExpr,
    self_local: Option<usize>,
    defined: &HashSet<usize>,
    uses: &mut HashSet<usize>,
) {
    match expr {
        LExpr::Local(index) if self_local != Some(*index) && !defined.contains(index) => {
            uses.insert(*index);
        }
        LExpr::Local(_) => {}
        LExpr::Field(inner, _) | LExpr::Cast(inner, _) | LExpr::Try(inner) => {
            expr_uses(inner, self_local, defined, uses)
        }
        LExpr::IsVariant(inner, _)
        | LExpr::VariantField(inner, _, _)
        | LExpr::IsBuiltin(inner, _)
        | LExpr::BuiltinField(inner, _) => expr_uses(inner, self_local, defined, uses),
        LExpr::Interpolate(parts) => {
            for part in parts {
                if let pengu_lir::LStringPart::Expr(expr) = part {
                    expr_uses(expr, self_local, defined, uses);
                }
            }
        }
        LExpr::Index(base, index) => {
            expr_uses(base, self_local, defined, uses);
            expr_uses(index, self_local, defined, uses);
        }
        LExpr::Array(items) | LExpr::Vector(items) | LExpr::Set(items) | LExpr::Tuple(items) => {
            for item in items {
                expr_uses(item, self_local, defined, uses);
            }
        }
        LExpr::ArrayRepeat(value, _) => expr_uses(value, self_local, defined, uses),
        LExpr::Map(entries) => {
            for (key, value) in entries {
                expr_uses(key, self_local, defined, uses);
                expr_uses(value, self_local, defined, uses);
            }
        }
        LExpr::Record { fields, base, .. } => {
            for (_, value) in fields {
                expr_uses(value, self_local, defined, uses);
            }
            if let Some(base) = base {
                expr_uses(base, self_local, defined, uses);
            }
        }
        LExpr::Variant(_, values) => {
            if let Some(values) = values {
                for value in values {
                    expr_uses(value, self_local, defined, uses);
                }
            }
        }
        LExpr::FuncRef(_) | LExpr::ConstRef(_) => {}
        LExpr::CStringNew(arg) => expr_uses(arg, self_local, defined, uses),
        LExpr::Primitive(_, args) | LExpr::Call(_, _, args) => {
            for arg in args {
                expr_uses(arg, self_local, defined, uses);
            }
        }
        LExpr::Ref(_, inner) => expr_uses(inner, self_local, defined, uses),
        LExpr::Range(start, end, _) => {
            expr_uses(start, self_local, defined, uses);
            if let Some(end) = end {
                expr_uses(end, self_local, defined, uses);
            }
        }
        LExpr::Binary(_, lhs, rhs) => {
            expr_uses(lhs, self_local, defined, uses);
            expr_uses(rhs, self_local, defined, uses);
        }
        LExpr::Unary(_, inner) => expr_uses(inner, self_local, defined, uses),
        LExpr::TraitCall { args, .. } => {
            for arg in args {
                expr_uses(arg, self_local, defined, uses);
            }
        }
        LExpr::Method { receiver, args, .. } => {
            expr_uses(receiver, self_local, defined, uses);
            for arg in args {
                expr_uses(arg, self_local, defined, uses);
            }
        }
        LExpr::Closure { captures, .. } => {
            for (_, local) in captures {
                if self_local != Some(*local) && !defined.contains(local) {
                    uses.insert(*local);
                }
            }
        }
        LExpr::ClosureCall(callee, args) => {
            expr_uses(callee, self_local, defined, uses);
            for arg in args {
                expr_uses(arg, self_local, defined, uses);
            }
        }
        LExpr::CollectVec(inner) | LExpr::IntoIter(inner) | LExpr::IterCloned(inner) => {
            expr_uses(inner, self_local, defined, uses)
        }
        LExpr::VecAdapter { base, args, .. } => {
            expr_uses(base, self_local, defined, uses);
            for arg in args {
                expr_uses(arg, self_local, defined, uses);
            }
        }
        LExpr::Unit
        | LExpr::Bool(_)
        | LExpr::Int(_)
        | LExpr::Float(_)
        | LExpr::Str(_)
        | LExpr::Char(_)
        | LExpr::ByteChar(_) => {}
    }
}
