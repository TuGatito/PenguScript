# Bootstrap de PSC (F5)

Diagrama T:

```
stage0 (Python 3.0.3)  ->  stage1 (PSC compilado por stage0)
stage1                 ->  stage2
stage2                 ->  stage3
stage3                 ->  stage4
```

El criterio de aceptación es el **punto fijo**: el C normalizado emitido por
stage3 y stage4 debe ser byte-idéntico. En la práctica también lo es para
stage2/stage3.

## Ejecutar

```bash
# stage1 ya construido por stage0:
python psc/tools/bootstrap.py

# o indicando el binario:
python psc/tools/bootstrap.py --stage1 psc/build/psc

# sin TCC (sólo desarrollo; el gate Linux lo exige):
python psc/tools/bootstrap.py --no-tcc
```

El script:

1. construye stage2 con stage1;
2. construye stage3 con stage2;
3. construye stage4 con stage3;
4. emite `stage3.c` y `stage4.c` y falla si difieren;
5. ejecuta el preflight de TCC.

Los artefactos quedan en `psc/build/bootstrap/check/` (ignorado por git).

## Comparar bundles

```bash
python psc/tools/compare_bundles.py a.c b.c
```

Normaliza las líneas `#line` (las rutas absolutas no afectan al punto fijo).

## Preflight de self-compile

```bash
python psc/tools/selfhost_preflight.py --psc psc/build/psc --smoke
python psc/tools/selfhost_preflight.py --cc build/tcc-dist/tcc-dist/bin/tcc
```

## CI

El job `psc-selfhost` compila stage1 con stage0, ejecuta el preflight con
gcc/clang/TCC y, en nightly, `test_f5_bootstrap.py` con `PSC_BOOTSTRAP=1`.
