//! Resumen de lo generado y de lo omitido.

use std::collections::BTreeMap;

use crate::ir::Ir;

/// Totales del archivo generado.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Report {
    /// Funciones generadas.
    pub functions: usize,
    /// Estructuras generadas.
    pub records: usize,
    /// Constantes generadas.
    pub constants: usize,
    /// Omitidos por categoría.
    pub omitted: BTreeMap<&'static str, usize>,
    /// Detalle de cada omisión.
    pub details: Vec<String>,
}

impl Report {
    /// Construye el reporte a partir del modelo.
    #[must_use]
    pub fn from_ir(ir: &Ir) -> Self {
        let mut report = Self {
            functions: ir.functions.len(),
            records: ir.records.len(),
            constants: ir.constants.len(),
            ..Self::default()
        };
        for item in &ir.omitted {
            *report.omitted.entry(item.kind).or_insert(0) += 1;
            report
                .details
                .push(format!("{} {}: {}", item.kind, item.name, item.reason));
        }
        report
    }

    /// Total de omitidos.
    #[must_use]
    pub fn omitted_total(&self) -> usize {
        self.omitted.values().sum()
    }

    /// `true` si no se omitió nada.
    #[must_use]
    pub fn is_complete(&self) -> bool {
        self.omitted_total() == 0
    }

    /// Una línea por categoría, ordenada.
    #[must_use]
    pub fn summary(&self) -> Vec<String> {
        self.omitted
            .iter()
            .map(|(kind, count)| format!("{count} {kind}(s) omitido(s)"))
            .collect()
    }
}
