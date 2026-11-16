//! Renderizado de tipos y firmas para hover, completion y símbolos.

use pengu_hir::Signature;
use pengu_syntax::ast::{Type, TypeKind};

/// Renderiza un tipo del AST en sintaxis `PenguScript`.
#[must_use]
pub fn type_text(ty: &Type) -> String {
    match &ty.kind {
        TypeKind::Unit => "()".to_owned(),
        TypeKind::Option(inner) => format!("?{}", type_text(inner)),
        TypeKind::Ref { mutable, inner } => {
            if *mutable {
                format!("&mut {}", type_text(inner))
            } else {
                format!("&{}", type_text(inner))
            }
        }
        TypeKind::Array { elem, .. } => format!("[{}; N]", type_text(elem)),
        TypeKind::Slice(elem) => format!("[{}]", type_text(elem)),
        TypeKind::Tuple(types) => {
            let parts: Vec<String> = types.iter().map(type_text).collect();
            format!("({})", parts.join(", "))
        }
        TypeKind::Path { segments, args } => {
            let mut text = segments.join("::");
            if !args.is_empty() {
                let parts: Vec<String> = args.iter().map(type_text).collect();
                text.push('[');
                text.push_str(&parts.join(", "));
                text.push(']');
            }
            text
        }
        TypeKind::Ptr(inner) => format!("Ptr[{}]", type_text(inner)),
        TypeKind::Fn { params, ret } => {
            let parts: Vec<String> = params.iter().map(type_text).collect();
            format!("({}) -> {}", parts.join(", "), type_text(ret))
        }
        TypeKind::SelfType => "Self".to_owned(),
    }
}

/// Renderiza la firma de una función o método.
#[must_use]
pub fn signature_text(name: &str, signature: &Signature) -> String {
    let mut params = Vec::new();
    if let Some(receiver) = signature.receiver {
        params.push(receiver_text(receiver));
    }
    params.extend(signature.params.iter().map(type_text));
    format!(
        "fn {name}({}) -> {}",
        params.join(", "),
        type_text(&signature.ret)
    )
}

fn receiver_text(receiver: pengu_syntax::ast::Receiver) -> String {
    match receiver {
        pengu_syntax::ast::Receiver::Ref => "@".to_owned(),
        pengu_syntax::ast::Receiver::Mut => "@mut".to_owned(),
        pengu_syntax::ast::Receiver::Own => "@own".to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pengu_span::DUMMY_SPAN;

    fn path(name: &str) -> Type {
        Type {
            kind: TypeKind::Path {
                segments: vec![name.to_owned()],
                args: Vec::new(),
            },
            span: DUMMY_SPAN,
        }
    }

    #[test]
    fn renderiza_tipos_compuestos() {
        let ty = Type {
            kind: TypeKind::Ref {
                mutable: false,
                inner: Box::new(path("Str")),
            },
            span: DUMMY_SPAN,
        };
        assert_eq!(type_text(&ty), "&Str");
        let tuple = Type {
            kind: TypeKind::Tuple(vec![path("Int"), path("Str")]),
            span: DUMMY_SPAN,
        };
        assert_eq!(type_text(&tuple), "(Int, Str)");
        let generic = Type {
            kind: TypeKind::Path {
                segments: vec!["Vec".to_owned()],
                args: vec![path("Int")],
            },
            span: DUMMY_SPAN,
        };
        assert_eq!(type_text(&generic), "Vec[Int]");
    }
}
