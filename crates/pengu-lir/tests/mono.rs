use pengu_hir::lower_program;
use pengu_lir::plan_monomorphization;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::check_crate;

fn plan(source: &str) -> pengu_lir::MonoPlan {
    let parsed = parse_program(FileId::new(0), source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(lowered.diagnostics.is_empty(), "{:?}", lowered.diagnostics);
    let types = check_crate(&lowered.krate);
    assert!(types.is_clean(), "{:?}", types.diagnostics);
    plan_monomorphization(&lowered.krate, &types)
}

#[test]
fn monomorphizes_turbofish_call() {
    let p = plan("id = [T](x: T) -> T\n    x\ngrimoire\n    bind n = id[Int](1)\n    return\n");
    assert!(p.diagnostics.is_empty(), "{:?}", p.diagnostics);
    assert_eq!(p.instances.len(), 1);
    assert!(p.instances[0].name.contains("id"));
    assert_eq!(p.instances[0].type_args, vec![pengu_types::Ty::Int]);
}

#[test]
fn monomorphizes_transitively() {
    let p = plan(
        "id = [T](x: T) -> T\n    x\napply = [T](x: T) -> T\n    id[T](x)\ngrimoire\n    bind n = apply[Int](1)\n    return\n",
    );
    assert!(p.diagnostics.is_empty(), "{:?}", p.diagnostics);
    assert_eq!(p.instances.len(), 2, "{:?}", p.instances);
}

fn lower(source: &str) -> pengu_lir::LProgram {
    let parsed = parse_program(FileId::new(0), source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(lowered.diagnostics.is_empty(), "{:?}", lowered.diagnostics);
    let types = check_crate(&lowered.krate);
    assert!(types.is_clean(), "{:?}", types.diagnostics);
    pengu_lir::lower_crate(&lowered.krate, &types)
}

fn calls(function: &pengu_lir::LFunction) -> Vec<(pengu_hir::DefId, Vec<pengu_types::Ty>)> {
    let mut found = Vec::new();
    for block in &function.blocks {
        for stmt in &block.stmts {
            let expr = match stmt {
                pengu_lir::LStmt::Let(_, expr, _)
                | pengu_lir::LStmt::Assign(_, expr, _)
                | pengu_lir::LStmt::Eval(expr, _) => expr,
                pengu_lir::LStmt::SetField(_, _, expr, _) => expr,
                pengu_lir::LStmt::Destructure(_, _, _) => continue,
            };
            collect_calls(expr, &mut found);
        }
        if let pengu_lir::LTerm::Return(Some(expr)) = &block.term {
            collect_calls(expr, &mut found);
        }
    }
    found
}

fn collect_calls(
    expr: &pengu_lir::LExpr,
    found: &mut Vec<(pengu_hir::DefId, Vec<pengu_types::Ty>)>,
) {
    match expr {
        pengu_lir::LExpr::Call(def, args, operands) => {
            found.push((*def, args.clone()));
            for operand in operands {
                collect_calls(operand, found);
            }
        }
        pengu_lir::LExpr::Binary(_, lhs, rhs) => {
            collect_calls(lhs, found);
            collect_calls(rhs, found);
        }
        pengu_lir::LExpr::Unary(_, inner) => collect_calls(inner, found),
        pengu_lir::LExpr::Tuple(items) => {
            for item in items {
                collect_calls(item, found);
            }
        }
        _ => {}
    }
}

#[test]
fn lir_materializes_generic_functions_per_instance() {
    let program = lower(
        "id = [T](x: T) -> T\n    x\napply = [T](x: T) -> T\n    id[T](x)\ngrimoire\n    bind n = apply[Int](1)\n    return\n",
    );
    let names: Vec<_> = program.functions.iter().map(|f| f.name.as_str()).collect();
    assert!(names.contains(&"id__Int"), "{names:?}");
    assert!(
        names.contains(&"apply__Int"),
        "{names:?} diagnostics={:?}",
        program.diagnostics
    );
    assert!(!names.contains(&"id"), "{names:?}");
    assert!(!names.contains(&"apply"), "{names:?}");

    let id = program
        .functions
        .iter()
        .find(|f| f.name == "id__Int")
        .unwrap();
    assert_eq!(id.ret, pengu_types::Ty::Int);
    assert_eq!(id.params[0].ty, pengu_types::Ty::Int);
    assert!(
        id.locals
            .iter()
            .all(|local| !matches!(local.ty, pengu_types::Ty::Generic(_))),
        "{:?}",
        id.locals
    );

    let apply = program
        .functions
        .iter()
        .find(|f| f.name == "apply__Int")
        .unwrap();
    assert!(
        apply
            .locals
            .iter()
            .all(|local| !matches!(local.ty, pengu_types::Ty::Generic(_))),
        "{:?}",
        apply.locals
    );
    let id_calls: Vec<_> = calls(apply)
        .into_iter()
        .filter(|(def, args)| *def == id.def && !args.is_empty())
        .collect();
    assert_eq!(id_calls.len(), 1, "{:?}", calls(apply));
    assert_eq!(id_calls[0].1, vec![pengu_types::Ty::Int]);
}
