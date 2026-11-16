//! Unificación e inferencia de tipos.

use crate::ty::Ty;

/// Error de unificación; no lleva datos porque el checker reporta el span.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct UnifyError;

#[derive(Clone, Debug)]
enum Var {
    Unknown,
    Int,
    Float,
    Bound(Ty),
}

/// Contexto de inferencia con union-find simple.
#[derive(Clone, Debug, Default)]
pub struct Infer {
    vars: Vec<Var>,
}

impl Infer {
    /// Crea una variable libre.
    pub fn fresh(&mut self) -> Ty {
        let id = self.vars.len() as u32;
        self.vars.push(Var::Unknown);
        Ty::Infer(id)
    }

    /// Crea una variable de literal entero.
    pub fn fresh_int(&mut self) -> Ty {
        let id = self.vars.len() as u32;
        self.vars.push(Var::Int);
        Ty::IntVar(id)
    }

    /// Crea una variable de literal flotante.
    pub fn fresh_float(&mut self) -> Ty {
        let id = self.vars.len() as u32;
        self.vars.push(Var::Float);
        Ty::FloatVar(id)
    }

    fn var(&self, id: u32) -> &Var {
        &self.vars[id as usize]
    }

    fn set(&mut self, id: u32, value: Ty) {
        self.vars[id as usize] = Var::Bound(value);
    }

    /// Resuelve un tipo hasta su representante actual.
    #[must_use]
    pub fn resolve(&mut self, ty: Ty) -> Ty {
        match ty {
            Ty::Infer(_) | Ty::IntVar(_) | Ty::FloatVar(_) => {
                let mut current = ty;
                loop {
                    let id = match current {
                        Ty::Infer(id) | Ty::IntVar(id) | Ty::FloatVar(id) => id,
                        _ => return current,
                    };
                    match self.var(id).clone() {
                        Var::Bound(next) => current = next,
                        Var::Unknown | Var::Int | Var::Float => return current,
                    }
                }
            }
            Ty::Tuple(items) => {
                Ty::Tuple(items.into_iter().map(|item| self.resolve(item)).collect())
            }
            Ty::Array(elem, len) => Ty::Array(Box::new(self.resolve(*elem)), len),
            Ty::Slice(elem, mutable) => Ty::Slice(Box::new(self.resolve(*elem)), mutable),
            Ty::Ref(inner, mutable) => Ty::Ref(Box::new(self.resolve(*inner)), mutable),
            Ty::Ptr(inner) => Ty::Ptr(Box::new(self.resolve(*inner))),
            Ty::Vec(inner) => Ty::Vec(Box::new(self.resolve(*inner))),
            Ty::Map(key, value) => {
                Ty::Map(Box::new(self.resolve(*key)), Box::new(self.resolve(*value)))
            }
            Ty::Set(inner) => Ty::Set(Box::new(self.resolve(*inner))),
            Ty::Option(inner) => Ty::Option(Box::new(self.resolve(*inner))),
            Ty::Result(ok, err) => {
                Ty::Result(Box::new(self.resolve(*ok)), Box::new(self.resolve(*err)))
            }
            Ty::Box(inner) => Ty::Box(Box::new(self.resolve(*inner))),
            Ty::Rc(inner) => Ty::Rc(Box::new(self.resolve(*inner))),
            Ty::Arc(inner) => Ty::Arc(Box::new(self.resolve(*inner))),
            Ty::Adt(def, args) => {
                Ty::Adt(def, args.into_iter().map(|arg| self.resolve(arg)).collect())
            }
            Ty::Fn(params, ret) => Ty::Fn(
                params
                    .into_iter()
                    .map(|param| self.resolve(param))
                    .collect(),
                Box::new(self.resolve(*ret)),
            ),
            Ty::Range(inner) => Ty::Range(Box::new(self.resolve(*inner))),
            Ty::Iterator(inner) => Ty::Iterator(Box::new(self.resolve(*inner))),
            other => other,
        }
    }

    /// Unifica dos tipos. Devuelve el representante común o `Err(())`.
    pub fn unify(&mut self, left: Ty, right: Ty) -> Result<Ty, UnifyError> {
        let left = self.resolve(left);
        let right = self.resolve(right);
        if left == right {
            return Ok(left);
        }
        match (left, right) {
            (Ty::Never, other) | (other, Ty::Never) => Ok(other),
            // `&[T; N]` (y el propio `&[T]`) encajan donde se espera el slice `[T]`.
            (Ty::Slice(left, mutable), Ty::Ref(right, _))
                if matches!(&*right, Ty::Array(..) | Ty::Slice(..)) =>
            {
                let elem = match &*right {
                    Ty::Array(elem, _) | Ty::Slice(elem, _) => (**elem).clone(),
                    _ => return Err(UnifyError),
                };
                let _ = self.unify((*left).clone(), elem);
                Ok(Ty::Slice(left, mutable))
            }
            (Ty::Ref(left, _), Ty::Slice(right, mutable))
                if matches!(&*left, Ty::Array(..) | Ty::Slice(..)) =>
            {
                let elem = match &*left {
                    Ty::Array(elem, _) | Ty::Slice(elem, _) => (**elem).clone(),
                    _ => return Err(UnifyError),
                };
                let _ = self.unify((*right).clone(), elem);
                Ok(Ty::Slice(right, mutable))
            }
            // Coerción implícita de préstamo: pasar `T` donde se espera `&T`
            // o `&mut T` es válido (los receptores `@`/`@mut` ya funcionan así).
            (Ty::Ref(inner, _), other) | (other, Ty::Ref(inner, _))
                if !matches!(other, Ty::Ref(..)) =>
            {
                self.unify(*inner, other)
            }
            // `&CString` se convierte en `&CStr`: `CString` desreferencia a `CStr`.
            (Ty::Ref(inner, _), Ty::Ref(other, _))
                if matches!(
                    (&*inner, &*other),
                    (Ty::CString, Ty::CStr) | (Ty::CStr, Ty::CString)
                ) =>
            {
                Ok(Ty::Ref(Box::new(Ty::CStr), false))
            }
            // Un array prestado se ve como slice: `&[T; N]` encaja en `&[T]`.
            (Ty::Ref(left, _), Ty::Ref(right, _))
                if matches!((&*left, &*right), (Ty::Array(..), Ty::Slice(..))) =>
            {
                Ok(Ty::Ref(right, false))
            }
            (Ty::Ref(left, _), Ty::Ref(right, _))
                if matches!((&*left, &*right), (Ty::Slice(..), Ty::Array(..))) =>
            {
                Ok(Ty::Ref(left, false))
            }
            (Ty::CString, Ty::CStr) | (Ty::CStr, Ty::CString) => Ok(Ty::CStr),
            (Ty::Error, other) | (other, Ty::Error) => Ok(other),
            (Ty::Int, Ty::I32) | (Ty::I32, Ty::Int) => Ok(Ty::I32),
            (Ty::Float, Ty::F64) | (Ty::F64, Ty::Float) => Ok(Ty::F64),
            (Ty::Infer(id), other) | (other, Ty::Infer(id)) => {
                self.set(id, other.clone());
                Ok(other)
            }
            (Ty::IntVar(left_id), Ty::IntVar(right_id)) => {
                self.set(left_id, Ty::IntVar(right_id));
                Ok(Ty::IntVar(right_id))
            }
            (Ty::IntVar(id), other) | (other, Ty::IntVar(id)) if other.is_integer() => {
                self.set(id, other.clone());
                Ok(other)
            }
            (Ty::FloatVar(left_id), Ty::FloatVar(right_id)) => {
                self.set(left_id, Ty::FloatVar(right_id));
                Ok(Ty::FloatVar(right_id))
            }
            (Ty::FloatVar(id), other) | (other, Ty::FloatVar(id)) if other.is_float() => {
                self.set(id, other.clone());
                Ok(other)
            }
            (Ty::Tuple(left_items), Ty::Tuple(right_items)) => {
                if left_items.len() != right_items.len() {
                    return Err(UnifyError);
                }
                let mut items = Vec::with_capacity(left_items.len());
                for (left, right) in left_items.into_iter().zip(right_items) {
                    items.push(self.unify(left, right)?);
                }
                Ok(Ty::Tuple(items))
            }
            (Ty::Array(left_elem, left_len), Ty::Array(right_elem, right_len)) => {
                if left_len != right_len {
                    return Err(UnifyError);
                }
                Ok(Ty::Array(
                    Box::new(self.unify(*left_elem, *right_elem)?),
                    left_len,
                ))
            }
            (Ty::Slice(left_elem, left_mut), Ty::Slice(right_elem, right_mut)) => {
                if left_mut != right_mut {
                    return Err(UnifyError);
                }
                Ok(Ty::Slice(
                    Box::new(self.unify(*left_elem, *right_elem)?),
                    left_mut,
                ))
            }
            (Ty::Ref(left_inner, left_mut), Ty::Ref(right_inner, right_mut)) => {
                if left_mut != right_mut {
                    return Err(UnifyError);
                }
                Ok(Ty::Ref(
                    Box::new(self.unify(*left_inner, *right_inner)?),
                    left_mut,
                ))
            }
            (Ty::Ptr(left_inner), Ty::Ptr(right_inner)) => {
                Ok(Ty::Ptr(Box::new(self.unify(*left_inner, *right_inner)?)))
            }
            (Ty::Vec(left_inner), Ty::Vec(right_inner)) => {
                Ok(Ty::Vec(Box::new(self.unify(*left_inner, *right_inner)?)))
            }
            (Ty::Map(left_key, left_value), Ty::Map(right_key, right_value)) => Ok(Ty::Map(
                Box::new(self.unify(*left_key, *right_key)?),
                Box::new(self.unify(*left_value, *right_value)?),
            )),
            (Ty::Set(left_inner), Ty::Set(right_inner)) => {
                Ok(Ty::Set(Box::new(self.unify(*left_inner, *right_inner)?)))
            }
            (Ty::Option(left_inner), Ty::Option(right_inner)) => {
                Ok(Ty::Option(Box::new(self.unify(*left_inner, *right_inner)?)))
            }
            (Ty::Result(left_ok, left_err), Ty::Result(right_ok, right_err)) => Ok(Ty::Result(
                Box::new(self.unify(*left_ok, *right_ok)?),
                Box::new(self.unify(*left_err, *right_err)?),
            )),
            (Ty::Box(left_inner), Ty::Box(right_inner)) => {
                Ok(Ty::Box(Box::new(self.unify(*left_inner, *right_inner)?)))
            }
            (Ty::Rc(left_inner), Ty::Rc(right_inner)) => {
                Ok(Ty::Rc(Box::new(self.unify(*left_inner, *right_inner)?)))
            }
            (Ty::Arc(left_inner), Ty::Arc(right_inner)) => {
                Ok(Ty::Arc(Box::new(self.unify(*left_inner, *right_inner)?)))
            }
            (Ty::Adt(left_def, left_args), Ty::Adt(right_def, right_args)) => {
                if left_def != right_def || left_args.len() != right_args.len() {
                    return Err(UnifyError);
                }
                let mut args = Vec::with_capacity(left_args.len());
                for (left, right) in left_args.into_iter().zip(right_args) {
                    args.push(self.unify(left, right)?);
                }
                Ok(Ty::Adt(left_def, args))
            }
            (Ty::Generic(left_def), Ty::Generic(right_def)) if left_def == right_def => {
                Ok(Ty::Generic(left_def))
            }
            (Ty::Fn(left_params, left_ret), Ty::Fn(right_params, right_ret)) => {
                if left_params.len() != right_params.len() {
                    return Err(UnifyError);
                }
                let mut params = Vec::with_capacity(left_params.len());
                for (left, right) in left_params.into_iter().zip(right_params) {
                    params.push(self.unify(left, right)?);
                }
                Ok(Ty::Fn(params, Box::new(self.unify(*left_ret, *right_ret)?)))
            }
            (Ty::Range(left_inner), Ty::Range(right_inner)) => {
                Ok(Ty::Range(Box::new(self.unify(*left_inner, *right_inner)?)))
            }
            (Ty::Iterator(left_inner), Ty::Iterator(right_inner)) => Ok(Ty::Iterator(Box::new(
                self.unify(*left_inner, *right_inner)?,
            ))),
            _ => Err(UnifyError),
        }
    }

    /// Aplica los valores por defecto: literales enteros -> `Int`, flotantes -> `Float`.
    pub fn apply_defaults(&mut self, ty: Ty) -> Ty {
        let ty = self.resolve(ty);
        match ty {
            Ty::IntVar(_) => Ty::Int,
            Ty::FloatVar(_) => Ty::Float,
            Ty::Tuple(items) => Ty::Tuple(
                items
                    .into_iter()
                    .map(|item| self.apply_defaults(item))
                    .collect(),
            ),
            Ty::Array(elem, len) => Ty::Array(Box::new(self.apply_defaults(*elem)), len),
            Ty::Slice(elem, mutable) => Ty::Slice(Box::new(self.apply_defaults(*elem)), mutable),
            Ty::Ref(inner, mutable) => Ty::Ref(Box::new(self.apply_defaults(*inner)), mutable),
            Ty::Ptr(inner) => Ty::Ptr(Box::new(self.apply_defaults(*inner))),
            Ty::Vec(inner) => Ty::Vec(Box::new(self.apply_defaults(*inner))),
            Ty::Map(key, value) => Ty::Map(
                Box::new(self.apply_defaults(*key)),
                Box::new(self.apply_defaults(*value)),
            ),
            Ty::Set(inner) => Ty::Set(Box::new(self.apply_defaults(*inner))),
            Ty::Option(inner) => Ty::Option(Box::new(self.apply_defaults(*inner))),
            Ty::Result(ok, err) => Ty::Result(
                Box::new(self.apply_defaults(*ok)),
                Box::new(self.apply_defaults(*err)),
            ),
            Ty::Box(inner) => Ty::Box(Box::new(self.apply_defaults(*inner))),
            Ty::Rc(inner) => Ty::Rc(Box::new(self.apply_defaults(*inner))),
            Ty::Arc(inner) => Ty::Arc(Box::new(self.apply_defaults(*inner))),
            Ty::Adt(def, args) => Ty::Adt(
                def,
                args.into_iter()
                    .map(|arg| self.apply_defaults(arg))
                    .collect(),
            ),
            Ty::Fn(params, ret) => Ty::Fn(
                params
                    .into_iter()
                    .map(|param| self.apply_defaults(param))
                    .collect(),
                Box::new(self.apply_defaults(*ret)),
            ),
            Ty::Range(inner) => Ty::Range(Box::new(self.apply_defaults(*inner))),
            Ty::Iterator(inner) => Ty::Iterator(Box::new(self.apply_defaults(*inner))),
            other => other,
        }
    }

    /// `true` si queda una variable sin resolver.
    #[must_use]
    pub fn has_unresolved(&mut self, ty: Ty) -> bool {
        match self.resolve(ty) {
            Ty::Infer(_) | Ty::IntVar(_) | Ty::FloatVar(_) => true,
            Ty::Tuple(items) => items.into_iter().any(|item| self.has_unresolved(item)),
            Ty::Array(elem, _)
            | Ty::Slice(elem, _)
            | Ty::Ref(elem, _)
            | Ty::Ptr(elem)
            | Ty::Vec(elem)
            | Ty::Set(elem)
            | Ty::Option(elem)
            | Ty::Box(elem)
            | Ty::Rc(elem)
            | Ty::Arc(elem)
            | Ty::Range(elem)
            | Ty::Iterator(elem) => self.has_unresolved(*elem),
            Ty::Map(key, value) | Ty::Result(key, value) => {
                self.has_unresolved(*key) || self.has_unresolved(*value)
            }
            Ty::Adt(_, args) => args.into_iter().any(|arg| self.has_unresolved(arg)),
            Ty::Fn(params, ret) => {
                params.into_iter().any(|param| self.has_unresolved(param))
                    || self.has_unresolved(*ret)
            }
            _ => false,
        }
    }
}
