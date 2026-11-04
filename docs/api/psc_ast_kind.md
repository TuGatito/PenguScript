# psc.ast.kind

> Source: `src/psc/ast/kind.pengu`

---

### `NodeKind`

> omen NodeKind

```pengu
    NdStart
    NdFile
    NdTopStmt
    NdStmt
    NdBlock
    NdError
    NdImportStmt
    NdDottedPath
    NdIncludeStmt
    NdLinkStmt
    NdLdflagStmt
    NdInsigniaStmt
    NdAttributes
    NdAttribute
    NdAttributeArgs
    NdConstDecl
    NdVarDecl
    NdLetDecl
    NdVarNameList
    NdStaticVarDecl
    NdRuneDecl
    NdEchoDecl
    NdFieldDecl
    NdCyclusKw
    NdShardParams
    NdShardParamRef
    NdWhereClause
    NdWhereBound
    NdDeriveClause
    NdOmenDecl
    NdOmenVariant
    NdOmenField
    NdOmenStringKind
    NdAliasDecl
    NdSealDecl
    NdConceptDecl
    NdConceptMethod
    NdBindDecl
    NdWeaveDecl
    NdWeaveModifier
    NdParamList
    NdParam
    NdEnchantingDecl
    NdAntiquusDecl
    NdDeclareStmt
    NdDeclareParams
    NdTestDecl
    NdWhenTopDecl
    NdWhenTopElsePlain
    NdWhenTopElseWhen
    NdSetStmt
    NdCompoundSetStmt
    NdSetTarget
    NdWithTarget
    NdNormalTarget
    NdEssenceTarget
    NdIfStmt
    NdIfCond
    NdIfCondBinding
    NdUnlessStmt
    NdWhileStmt
    NdForRangeStmt
    NdForInStmt
    NdWhenStmt
    NdWhenElsePlain
    NdWhenElseWhen
    NdElseBlock
    NdWithStmt
    NdUnsafeStmt
    NdDeferStmt
    NdErrdeferStmt
    NdBanishStmt
    NdReturnStmt
    NdBreakStmt
    NdContinueStmt
    NdExprStmt
    NdContinueSimple
    NdBreakSimple
    NdReturnSimple
    NdSetSimple
    NdCompoundSetSimple
    NdSimpleStmt
    NdOrElse
    NdOrReturn
    NdOrBlock
    NdTryExpr
    NdIfExpr
    NdWhenExpr
    NdJudgeExpr
    NdJudgeOverExpr
    NdForComp
    NdWhenClause
    NdWhenPattern
    NdWhenVariant
    NdWhenPayload
    NdWhenField
    NdFieldPattern
    NdFieldTuple
    NdWhenGuard
    NdElseClause
    NdBoolOr
    NdBoolAnd
    NdEq
    NdNe
    NdLt
    NdLe
    NdGt
    NdGe
    NdInExpr
    NdNotInExpr
    NdIsPresent
    NdIsNotPresent
    NdIsTrue
    NdIsFalse
    NdRangeDotdot
    NdToExpr
    NdBitwiseOr
    NdBitwiseAnd
    NdBitwiseXor
    NdShl
    NdShr
    NdAdd
    NdSub
    NdMul
    NdDiv
    NdMod
    NdBitNot
    NdLogNot
    NdNeg
    NdSigilOf
    NdEssenceOf
    NdTransmute
    NdSizeOf
    NdAlignOf
    NdTypeOf
    NdSomeExpr
    NdBanishExpr
    NdOrdExpr
    NdChrExpr
    NdBytesExpr
    NdCallingExpr
    NdChainExpr
    NdMethodStep
    NdPipeStep
    NdGenericArgs
    NdArgList
    NdPosArg
    NdNamedArg
    NdFieldAccess
    NdArrowAccess
    NdAtExpr
    NdSliceAtExpr
    NdLengthExpr
    NdAtAccess
    NdDotAccess
    NdSliceRange
    NdParenExpr
    NdVarRef
    NdSelfRef
    NdIntLit
    NdFloatLit
    NdStringLit
    NdCharLit
    NdTrueLit
    NdFalseLit
    NdNullLit
    NdMaybeNone
    NdErrorLit
    NdDonumExpr
    NdDefinedExpr
    NdStructInit
    NdFieldInit
    NdWithInitExpr
    NdDoExpr
    NdLambdaExpr
    NdLambdaNoParams
    NdLambdaParam
    NdLambdaParamList
    NdListInitExpr
    NdMapInitExpr
    NdArrayInitExpr
    NdArrayLit
    NdMapLit
    NdMapEntry
    NdFieldEntry
    NdIndentLiteral
    NdIndentArray
    NdIndentRow
    NdIndentEntries
    NdTypeOrParam
    NdRefType
    NdFrozenType
    NdFnType
    NdFnParamList
    NdFnParam
    NdArrayType
    NdSliceType
    NdManyType
    NdListType
    NdMapType
    NdMaybeType
    NdResultType
    NdOpaqueType
    NdBaseType
    NdCustomType
    NdTupleType
```

 psc/ast/kind.pengu — inventario de nodos del AST.

 Los nombres de las variantes son `Nd` + PascalCase; `ps_node_kind_name`
 devuelve el nombre de la regla de stage0 que se usa en el dump.

 ## Memoria
 `NodeKind` es un valor puro.

### `ps_node_kind_name`

> **ps_node_kind_name**(kind: NodeKind) -> string

 Nombre de la regla de stage0 asociada a un nodo.

 ## Memoria
 Devuelve un literal estático; no liberar.

