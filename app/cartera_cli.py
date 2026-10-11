"""Cartera propia: importar fuentes, cruzar con carpetas y generar alias.

    python cartera_cli.py importar [--escritorio JSON] [--log TXT] [--propios TXT]
    python cartera_cli.py cruzar              # informe, sin tocar carpetas
    python cartera_cli.py cruzar --aplicar    # crea carpetas faltantes y renombra las de solo numero
    python cartera_cli.py cruzar --aplicar --sin-crear   # solo renombra; las nuevas se crean a demanda
    python cartera_cli.py aliases             # genera _SISTEMA/aliases_cartera.json
    python cartera_cli.py quitar 123456/2022 ["123456/2022 bis1/24" ...]   # saca causas de la cartera

Importar solo agrega: para corregir un numero mal cargado se lo saca con "quitar" y se
vuelve a importar el valor correcto.

Los datos viven en <base>/_SISTEMA (numeros de expediente: nunca al repo).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cartera import cargar, fusionar, guardar, normalizar_expte, posibles_erratas  # noqa: E402
from cartera_alias import aliases_desde_cartera  # noqa: E402
from cartera_cruce import aplicar, carpetas_sin_causa, cruzar, reporte_md  # noqa: E402
from cartera_fuentes import desde_escritorio, desde_log_justi, desde_propios_txt  # noqa: E402

from config import BASE  # noqa: E402


def _importar(args, sistema: Path) -> None:
    ruta = sistema / "cartera.json"
    nuevas = []
    if args.escritorio:
        nuevas += desde_escritorio(json.loads(args.escritorio.read_text(encoding="utf-8")))
    if args.log:
        nuevas += desde_log_justi(args.log.read_text(encoding="utf-8"))
    if args.propios:
        causas, invalidas = desde_propios_txt(args.propios.read_text(encoding="utf-8"))
        nuevas += causas
        (sistema / "cartera_invalidas.txt").write_text("\n".join(invalidas), encoding="utf-8")
        for s in invalidas:
            print(f"  [no se pudo leer] {s}")
    causas = fusionar(cargar(ruta) + nuevas)
    guardar(causas, ruta)
    print(f"Cartera: {len(causas)} causas -> {ruta}")


def _cruzar(args, sistema: Path, casos: Path, mapa: dict[str, str] | None) -> None:
    ruta = sistema / "cartera.json"
    causas = cargar(ruta)
    if mapa is None:
        from ingesta import _mapa_exptes
        mapa = _mapa_exptes()
    cruces = cruzar(causas, casos, mapa)
    for x in cruces:
        if x.accion == "ok" and x.carpeta:
            x.causa.carpeta, x.causa.carpeta_prevista = x.carpeta, None
        elif x.accion == "renombrar":
            x.causa.carpeta = x.carpeta
        elif x.accion == "crear":
            x.causa.carpeta_prevista = x.destino
    invalidas_f = sistema / "cartera_invalidas.txt"
    invalidas = invalidas_f.read_text(encoding="utf-8").splitlines() if invalidas_f.exists() else []
    md = reporte_md(cruces, carpetas_sin_causa(casos, cruces), posibles_erratas(causas), invalidas)
    (sistema / "CARTERA_CRUCE.md").write_text(md, encoding="utf-8")
    if args.aplicar:
        a_aplicar = [x for x in cruces if x.accion != "crear"] if args.sin_crear else cruces
        hechos, conflictos = aplicar(a_aplicar, casos, sistema / "CARTERA_APLICADO.csv")
        print(f"Aplicado: {len(hechos)} cambios, {len(conflictos)} conflictos")
        for c in conflictos:
            print(f"  [conflicto] {c}")
    guardar(causas, ruta)
    print(f"Informe: {sistema / 'CARTERA_CRUCE.md'}")


def _quitar(args, sistema: Path) -> None:
    ruta = sistema / "cartera.json"
    causas = cargar(ruta)
    quitar, desconocidas = set(), []
    for n in args.numeros:
        e = normalizar_expte(n)
        if e is None or e.clave_completa not in {c.expte.clave_completa for c in causas}:
            desconocidas.append(n)
        else:
            quitar.add(e.clave_completa)
    if quitar:
        guardar([c for c in causas if c.expte.clave_completa not in quitar], ruta)
    print(f"Quitadas: {len(quitar)}")
    for n in desconocidas:
        print(f"  [no esta en la cartera o no se pudo leer] {n}")


def _aliases(sistema: Path, casos: Path) -> None:
    aliases, ambiguos = aliases_desde_cartera(cargar(sistema / "cartera.json"), casos)
    destino = sistema / "aliases_cartera.json"
    destino.write_text(json.dumps(
        {"_doc": "Generado por cartera_cli.py aliases. No editar a mano.", "aliases": aliases},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(aliases)} aliases -> {destino}")
    if ambiguos:
        print(f"Apellidos repetidos (se distinguen por numero): {', '.join(ambiguos)}")


def main(argv: list[str] | None = None, mapa: dict[str, str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=BASE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("importar")
    imp.add_argument("--escritorio", type=Path)
    imp.add_argument("--log", type=Path)
    imp.add_argument("--propios", type=Path)
    cr = sub.add_parser("cruzar")
    cr.add_argument("--aplicar", action="store_true")
    cr.add_argument("--sin-crear", action="store_true", help="con --aplicar: solo renombra; las carpetas nuevas se crean al llegar el primer archivo")
    sub.add_parser("aliases")
    q = sub.add_parser("quitar")
    q.add_argument("numeros", nargs="+", metavar="NUMERO")
    args = ap.parse_args(argv)

    sistema, casos = args.base / "_SISTEMA", args.base / "01_Expedientes"
    sistema.mkdir(parents=True, exist_ok=True)
    if args.cmd == "importar":
        _importar(args, sistema)
    elif args.cmd == "cruzar":
        _cruzar(args, sistema, casos, mapa)
    elif args.cmd == "quitar":
        _quitar(args, sistema)
    else:
        _aliases(sistema, casos)


if __name__ == "__main__":
    main()
