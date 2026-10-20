#!/usr/bin/env python3
"""Run real Windows Computer Usage tasks through a private LlamaCode daemon."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import winreg
import zipfile
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[4]
TASK = ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261016-CU-20-E2E"
APP = ROOT / "build/Debug/LlamaCode.exe"
MODEL_ID = "sys-vram-8-gemma"
RUNTIME_PIN = "b9763"
BASE_AGENT_ID = "agent-intermedio"
PORT = 8898
BASE = f"http://127.0.0.1:{PORT}"
ISOLATED_PROFILES_ROOT = TASK / "runtime/profiles-headless"
WORKSPACE_ROOT = TASK / "workspace"
EDGE_TEST_ROOT = pathlib.Path(tempfile.gettempdir()) / "LlamaCode-CU20"
SETTINGS_KEY = r"Software\LlamaCode\LlamaCode"
EXCEL_EXE = pathlib.Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE")
EXCEL_LAUNCH_APP = pathlib.Path(r"C:\PROGRA~2\MICROS~2\root\Office16\EXCEL.EXE")
CASE_IDS = [f"CU{i:02d}" for i in range(1, 21)] + [
    "DIAG_READONLY", "DIAG_SAVE_CU13", "DIAG_CLOSE_TEST_EDGE",
    "DIAG_DISCARD_TEST_EXCEL", "DIAG_CLOSE_TEST_EXCEL",
    "DIAG_CLOSE_TEST_NOTEPAD"]
CLIPBOARD_MARKER = "CU20-CLIPBOARD-7K9-PRESERVE"
CU14_LINE = "CU14-EXACT-9F2B"
CASE_TOOL_ALLOWLIST = {
    "CU19": {
        "desktop_click_element", "desktop_controls", "desktop_focus", "desktop_key",
        "desktop_launch", "desktop_read_text", "desktop_type", "desktop_windows",
    },
}


def cu19_document_paths(workspace: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    suffix = re.sub(r"[^A-Za-z0-9_-]+", "-", workspace.name).strip("-")
    return (
        workspace / f"CU19-alpha-{suffix}.txt",
        workspace / f"CU19-beta-{suffix}.txt",
    )


def tools_for_case(case_id: str, desktop_tools: list[str]) -> list[str]:
    allowlist = CASE_TOOL_ALLOWLIST.get(case_id)
    if allowlist is None:
        return sorted(desktop_tools)
    missing = allowlist.difference(desktop_tools)
    if missing:
        raise RuntimeError(f"Faltan tools requeridas para {case_id}: {sorted(missing)!r}")
    return sorted(allowlist)


def request_json(url: str, body: dict | None = None, timeout: float = 20) -> dict:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def prop(name: str) -> object:
    return request_json(f"{BASE}/prop?name={urllib.parse.quote(name)}")["value"]


def invoke(method: str, args: list | None = None, target: str = "") -> dict:
    url = f"{BASE}/invoke"
    if target:
        url += "?target=" + urllib.parse.quote(target, safe="")
    return request_json(url, {"method": method, "args": args or []}, timeout=45)


def setprop(name: str, value: object) -> dict:
    return request_json(f"{BASE}/setprop", {"name": name, "value": value})


def wait_until(predicate, label: str, timeout_sec: float, interval: float = 1.0):
    deadline = time.monotonic() + timeout_sec
    last = None
    while time.monotonic() < deadline:
        try:
            last = predicate()
            if last:
                return last
        except (OSError, urllib.error.URLError, TimeoutError, KeyError, ValueError):
            pass
        time.sleep(interval)
    raise TimeoutError(f"Timeout esperando {label}; último estado={last!r}")


def start_fresh_agent_session(previous_message_count: int, invoke_method=None,
                              read_property=None, wait_for=None) -> dict:
    """Start a clean agent context between CU18's copy and paste phases."""
    invoke_method = invoke_method or invoke
    read_property = read_property or prop
    wait_for = wait_for or wait_until
    if previous_message_count <= 0:
        raise ValueError("CU18 necesita una conversación previa para poder aislar la continuación")
    response = invoke_method("newOpencodeSession", [])
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError(f"No se pudo abrir una sesión nueva del agente: {response!r}")
    wait_for(lambda: isinstance(read_property("agentMessages"), list)
             and len(read_property("agentMessages")) == 0,
             "contexto de agente limpio para CU18", 15)
    return {"method": "newOpencodeSession", "messages_before": previous_message_count,
            "messages_after": 0, "clean_context": True}


def save_json(path: pathlib.Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def console_json_line(payload: object) -> str:
    """Serialize console summaries using ASCII escapes for legacy Windows code pages."""
    return json.dumps(payload, ensure_ascii=True)


def edge_shortcut_arguments() -> str:
    # Reuse the signed-in user's normal Edge profile, but open a dedicated
    # window so the case never navigates or closes an existing user tab.
    return "--new-window --no-first-run"


def create_edge_shortcut(shortcut_path: pathlib.Path, edge_exe: str) -> None:
    import win32com.client

    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    shortcut = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = edge_exe
    shortcut.Arguments = edge_shortcut_arguments()
    shortcut.WorkingDirectory = str(pathlib.Path(edge_exe).parent)
    shortcut.Description = "LlamaCode CU20 Edge test window using the current user profile"
    shortcut.Save()


def case_prompt(case_id: str, workspace: pathlib.Path,
                edge_shortcut: pathlib.Path | None = None,
                diagnostic_target_id: str | None = None,
                diagnostic_target_pid: str | None = None,
                diagnostic_target_file: str | None = None) -> str:
    workbook = workspace / "cu20-computer-usage.xlsx"
    excel_app = "'" + str(EXCEL_EXE) + "'"
    excel_book = "'" + str(workbook) + "'"
    exact_excel_args = '/x "' + str(workbook) + '"'
    if case_id == "DIAG_READONLY":
        if not diagnostic_target_id:
            raise ValueError("DIAG_READONLY requiere el target_id observado para la ventana exacta")
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage para una inspección de solo lectura. "
            "No abras ni cierres ventanas; no hagas clic, no escribas y no pulses teclas. El target_id "
            "" + diagnostic_target_id + " corresponde al HWND del PID ya verificado cuya command line abre "
            "el libro exacto " + str(workbook) + ". Ejecuta desktop_read_text dos veces con ese target_id: "
            "primero sin filtro y luego query='final-v25-suite-CU13' para comprobar la ruta de destino. "
            "Después llama desktop_controls seis veces, en este orden y siempre con el mismo target_id: "
            "query='Sí', query='No', query='Nombre de archivo', query='Guardar como', "
            "query='Guardar' y query='Cancelar'. Sólo informa nombres, roles, valores y estados "
            "habilitados que devuelvan. No pulses ningún control. No uses desktop_windows y termina "
            "tras esas ocho lecturas sin realizar ninguna acción.")
    if case_id == "DIAG_SAVE_CU13":
        if not diagnostic_target_id:
            raise ValueError("DIAG_SAVE_CU13 requiere el target_id observado para el libro exacto")
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage para guardar el libro sintético "
            "exacto " + str(workbook) + ". El usuario autorizó guardar y sobrescribir este libro de "
            "prueba como parte de CU13, pero no autorizó descartarlo. El target_id " + diagnostic_target_id + " "
            "pertenece al PID verificado cuya command line abre esa ruta. Ejecuta desktop_read_text una vez "
            "con ese target_id. Si no ves el diálogo superior Guardar como y el libro "
            "cu20-computer-usage.xlsx, termina sin actuar. En Guardar como consulta "
            "desktop_controls query='Nombre de archivo'; elige el único control role=edit y usa "
            "desktop_control_action action='read' con sus control_id, target_id y snapshot_id. Luego usa "
            "desktop_control_action action='set_value' una sola vez en ese edit con value='" + str(workbook) + "' "
            "para fijar la ruta exacta. Continúa sólo si la lectura de retorno confirma exactamente ese path; "
            "si falla o difiere, detente. Consulta desktop_controls "
            "query='Guardar' y haz un único click en el botón exacto Guardar habilitado de la ventana "
            "Guardar como, con IDs recientes. Si el siguiente diálogo pregunta literalmente "
            "'¿Desea reemplazarlo?' para este mismo nombre, consulta desktop_controls query='Sí' y haz "
            "un único click en el botón exacto Sí habilitado. No pulses No, No guardar, Cancelar, Enter "
            "ni la X. Si el diálogo o el botón no coincide, detente. Tras el último click, lee una vez "
            "con el target_id indicado; si ya no existe, termina de inmediato sin reenumerar ventanas "
            "ni repetir acciones. No toques otra ventana.")
    if case_id == "DIAG_CLOSE_TEST_EDGE":
        if not diagnostic_target_id:
            raise ValueError("DIAG_CLOSE_TEST_EDGE requiere el target_id exacto de la ventana creada por la prueba")
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage para cerrar la ventana de Edge que "
            "creó esta corrida. El usuario autorizó cerrar las ventanas de prueba de esta campaña. El "
            "target_id exacto " + diagnostic_target_id + " proviene de desktop_launch y el runner confirmó "
            "que era una ventana nueva de Edge abierta con --new-window; puede compartir el PID del Edge "
            "normal del usuario. Lee una vez desktop_read_text con ese target_id y query='Título de ventana', "
            "max=2; no leas el contenido de la página ni otras ventanas. El ID proviene del launch "
            "nuevo ya validado; no exijas que el título contenga 'Microsoft Edge', porque puede variar "
            "por idioma y página. Si la lectura muestra Guest/Invitado, InPrivate o un diálogo/modal, "
            "detente sin actuar. Ejecuta "
            "desktop_focus una vez con ese "
            "target_id exacto y espera confirmación; luego pulsa desktop_key key='F4', modifiers=['ALT'] "
            "una sola vez. Inmediatamente después ejecuta desktop_windows exactamente una vez; no hagas "
            "ninguna lectura posterior, aunque la respuesta indique pérdida de foco o HWND reemplazado, "
            "porque Windows puede reciclar ese ID para otra ventana de Edge. "
            "compara sólo los IDs: si falta " + diagnostic_target_id + ", termina inmediatamente sin "
            "otra tool. Si sigue listado, detente sin actuar. No leas otra fila, no elijas otro target, "
            "no repitas desktop_windows y no navegues ni cierres ninguna ventana/pestaña previa del usuario.")
    if case_id == "DIAG_DISCARD_TEST_EXCEL":
        if not diagnostic_target_id or not diagnostic_target_pid:
            raise ValueError("DIAG_DISCARD_TEST_EXCEL requiere PID y target_id del libro exacto")
        target_file = diagnostic_target_file or "cu20-computer-usage.xlsx"
        if target_file not in {"cu20-computer-usage.xlsx", "clipboard-paste.xlsx"}:
            raise ValueError("DIAG_DISCARD_TEST_EXCEL sólo admite libros sintéticos de esta suite")
        target_book = workspace / target_file
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage para cerrar el workbook sintético "
            "que abrió esta corrida y quedó sin guardar. El usuario autorizó descartar los cambios de los "
            "archivos de prueba creados por esta campaña para poder cerrar sus ventanas. El PID "
            + diagnostic_target_pid + " y el target_id " + diagnostic_target_id + " pertenecen al proceso "
            "que abrió exactamente " + str(target_book) + ". Ejecuta desktop_read_text una vez con ese "
            "target_id. Continúa sólo si el título identifica " + target_file + " en Excel y la "
            "lectura muestra literalmente el diálogo '¿Guardar los cambios en este archivo?'. Si no "
            "coinciden, detente sin actuar. Consulta desktop_controls query='No guardar' en ese mismo "
            "target_id; exige un único botón exacto habilitado y usa desktop_click_element una sola vez "
            "con su control_id, target_id y snapshot_id recientes. Después ejecuta desktop_windows una "
            "vez y confirma que el PID " + diagnostic_target_pid + " ya no tiene una ventana. No pulses "
            "Guardar, Cancelar, Enter ni la X, no uses WM_CLOSE de nuevo y no toques otra ventana.")
    if case_id == "DIAG_CLOSE_TEST_EXCEL":
        if not diagnostic_target_pid:
            raise ValueError("DIAG_CLOSE_TEST_EXCEL requiere el PID exacto creado por la corrida")
        target_file = diagnostic_target_file or "cu20-computer-usage.xlsx"
        if target_file not in {"cu20-computer-usage.xlsx", "clipboard-paste.xlsx"}:
            raise ValueError("DIAG_CLOSE_TEST_EXCEL sólo admite libros sintéticos de esta suite")
        target_book = workspace / target_file
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage para cerrar este Excel de prueba. "
            "El usuario autorizó descartar cambios no guardados en libros sintéticos creados por esta campaña. "
            "El PID " + diagnostic_target_pid + " fue verificado por command line como el proceso que abrió "
            "el archivo sintético exacto " + str(target_book) + ". Ejecuta desktop_windows una vez y "
            "selecciona una única ventana de ese PID cuyo título identifique " + target_file + " - Excel; "
            "usa el target_id devuelto. Lee una vez esa ventana y continúa sólo si confirma ese libro exacto. "
            "Enfoca ese target_id y pulsa desktop_key key='F4', modifiers=['ALT'] una sola vez; no guardes "
            "ni pulses Ctrl+S. Ejecuta desktop_windows y comprueba si el PID sigue visible. Si aparece "
            "literalmente el diálogo '¿Guardar los cambios en este archivo?' para ese workbook, consulta "
            "desktop_controls query='No guardar' en el diálogo y exige un único botón exacto habilitado; "
            "púlsalo una sola vez con control_id, target_id y snapshot_id recientes. Luego ejecuta "
            "desktop_windows una vez más y confirma que el PID " + diagnostic_target_pid + " ya no tiene "
            "ventana. Si no aparece ese diálogo exacto, no pulses ningún botón y detente. No uses WM_CLOSE "
            "ni interactúes con otro PID o documento.")
    if case_id == "DIAG_CLOSE_TEST_NOTEPAD":
        if not diagnostic_target_id:
            raise ValueError("DIAG_CLOSE_TEST_NOTEPAD requiere el target_id de la pestaña sintética")
        filename = diagnostic_target_file or "notepad-exact-line.txt"
        if filename not in {"notepad-exact-line.txt", "notepad-replace.txt",
                            "notepad-no-duplicate.txt", "clipboard-source.txt"}:
            raise ValueError("DIAG_CLOSE_TEST_NOTEPAD sólo admite archivos sintéticos conocidos")
        notepad_file = workspace / filename
        if not notepad_file.is_file() and diagnostic_target_file is None:
            notepad_file = workspace / "notepad-replace.txt"
        if diagnostic_target_file is not None and not notepad_file.is_file():
            raise ValueError("DIAG_CLOSE_TEST_NOTEPAD requiere el archivo sintético exacto en el workspace")
        filename = notepad_file.name
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage para limpiar la pestaña sintética "
            + filename + " de esta suite. El usuario autorizó cerrar apps de campaña y descartar "
            "cambios no guardados en archivos sintéticos de estas pruebas. El target_id exacto de la ventana "
            "Notepad es " + diagnostic_target_id + " y el archivo del caso es " + str(notepad_file) + ". "
            "Lee una vez con desktop_read_text target_id=" + repr(diagnostic_target_id) + "; continúa sólo "
            "si el título identifica exactamente " + filename + " en Bloc de notas. Si no coincide, detente sin "
            "hacer nada. Enfoca ese target una vez y pulsa desktop_key key='W', modifiers=['CTRL'] una sola vez. "
            "Lee el mismo target inmediatamente. Si el título cambió y ya no identifica " + filename + ", esa "
            "pestaña quedó cerrada: termina ahora y no pulses más teclas aunque el nuevo título parezca otro "
            "archivo sintético. Si aparece un diálogo de guardado para " + filename + ", consulta una vez "
            "desktop_controls query='No guardar' y, sólo si aparece un único botón exacto habilitado, púlsalo "
            "una vez con sus IDs recientes; luego lee el target una vez y termina. No guardes cambios de la "
            "pestaña sintética, no repitas Ctrl+W, no cierres otra pestaña ni interactúes con documentos ajenos.")
    calc_requests = {
        "CU01": ("19+23=", "42"),
        "CU02": ("200-56=", "144"),
        "CU03": ("(8+4)*3=", "36"),
        "CU04": ("200*15/100=", "30"),
    }
    if case_id in calc_requests:
        expression, expected = calc_requests[case_id]
        return ("Usá únicamente las herramientas desktop_* de Computer Usage. Abrí una ventana "
                "de Calculadora de Windows; no abras ni modifiques otros documentos. Una vez "
                f"enfocada, limpia la entrada si hace falta y escribe la expresión completa "
                f"{expression} una sola vez. Deja el visor con el resultado, léelo por UIA/OCR "
                f"y confirma {expected}. No repitas la expresión para comprobarla.")
    if case_id == "CU05":
        if edge_shortcut is None:
            raise ValueError("CU05 requiere un acceso directo de Edge con perfil de usuario existente")
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. Abrí el acceso directo "
            f"temporal {str(edge_shortcut)!r} con desktop_launch en el campo app, sin agregar "
            "args. Abre una ventana nueva del Edge normal usando el perfil existente del usuario; "
            "no abras Guest/Invitado ni InPrivate. Conserva el target_id devuelto por desktop_launch "
            "y úsalo en todas las tools. El acceso directo apunta al Edge normal; usa el ID nuevo "
            "que devuelve desktop_launch sin depender del texto del título. Si el launch dice que la "
            "ventana ya estaba abierta o devuelve un diálogo, detente. Nunca navegues ni cierres pestañas/ventanas que ya estaban "
            "abiertas. "
            "Enfoca la barra con desktop_key key='L', modifiers=['CTRL']; inmediatamente después "
            "ejecuta una desktop_read_text nueva con el target_id literal de Edge para observar el foco. "
            "Luego escribe Apollo 11 landing date una sola vez y ejecuta inmediatamente otra "
            "desktop_read_text con ese target_id y query='Apollo 11 landing date', max=8; presiona "
            "Enter una sola vez únicamente si esa lectura confirma el texto en la barra. Después de "
            "Enter ejecuta inmediatamente desktop_read_text con el mismo target_id, query='Apollo 11', "
            "max=8. Si todavía no hay resultados, usa desktop_wait_for window_title='Apollo 11' "
            "timeout_ms=20000 una vez y lee el resultado visible una vez más con ese target_id. "
            "No respondas antes de una lectura posterior a la búsqueda que muestre el resultado. "
            "No omitas la observación requerida después de Ctrl+L ni después de escribir. "
            "Después de encontrar la ventana de resultados, ejecuta desktop_read_text una vez y no respondas "
            "antes de esa lectura. "
            "Lee el resultado visible y reporta el día, hora y año con el mismo formato de la página, "
            "sin traducir ni responder sólo de memoria. El día/hora y el año pueden estar en frases "
            "cercanas distintas: combínalos sólo si la misma lectura los muestra para Apollo 11. "
            "Si aparece un CAPTCHA, `google.com/sorry` o un aviso de tráfico inusual, detente tras "
            "esa lectura y reporta BLOCKED; no lo resuelvas, esperes ni reintentes. "
            "En la respuesta final menciona explícitamente Apollo 11 junto con la fecha que leíste; "
            "no respondas sólo con fecha u hora. No declares éxito si el resultado visible no "
            "respalda la fecha y el año.")
    if case_id == "CU06":
        if edge_shortcut is None:
            raise ValueError("CU06 requiere un acceso directo de Edge con perfil de usuario existente")
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. Abrí el acceso directo "
            f"temporal {str(edge_shortcut)!r} con desktop_launch app y sin args. Abre una ventana "
            "nueva del Edge normal con el perfil existente del usuario; no uses Guest/Invitado ni "
            "InPrivate. Conserva el target_id exacto de desktop_launch y úsalo en cada tool. El acceso "
            "directo es el Edge normal; no dependas del texto del título. Si el launch dice que la "
            "ventana ya estaba abierta o devuelve un diálogo, detente. No navegues ni cierres "
            "pestañas/ventanas que ya estaban abiertas. Pulsa desktop_key key='L', modifiers=['CTRL'] una vez "
            "e inmediatamente lee desktop_read_text target_id=<Edge>, max=8. Escribe una vez la URL "
            "de búsqueda de Google https://www.google.com/search?q=historia+de+Egipto+en+Wikipedia "
            "y lee de inmediato la barra con desktop_read_text target_id=<Edge>, query="
            "'historia+de+Egipto+en+Wikipedia', max=8. Pulsa Enter una vez sólo si confirma la URL. "
            "Después lee resultados con desktop_read_text target_id=<Edge>, query='Wikipedia', max=12. "
            "Si Google muestra CAPTCHA, `google.com/sorry` o tráfico inusual, detente justo después de "
            "esa lectura y reporta BLOCKED; no lo resuelvas, no esperes ni repitas lecturas/búsquedas. "
            "Localiza en el OCR el resultado que identifica ‘Historia de Egipto’ y Wikipedia; usa el "
            "centro normalizado (x,y) de esa misma línea en desktop_click scope_kind='window', "
            "target_id=<Edge>, una vez. No inventes coordenadas ni pulses un resultado de UIA no "
            "invocable. Luego lee desktop_read_text target_id=<Edge>, query='Historia de Egipto', "
            "max=16. Si la página aún carga, espera desktop_wait ms=1500 una sola vez y vuelve a leer. "
            "Termina sólo si el título identifica Historia de Egipto y Wikipedia. Resume brevemente en "
            "español un dato que hayas visto en el snippet del resultado de Wikipedia o en el texto/"
            "encabezado del artículo; di de cuál lectura sale. No respondas de memoria ni inicies sesión.")
    if case_id == "CU07":
        if edge_shortcut is None:
            raise ValueError("CU07 requiere un acceso directo de Edge con perfil de usuario existente")
        return (
            "Usa sólo desktop_*. Llama una sola vez a desktop_launch con app igual al literal exacto "
            f"{str(edge_shortcut)!r} y args como cadena vacía. Abre una ventana nueva de Microsoft Edge "
            "con el perfil normal existente del usuario, nunca Guest/Invitado ni InPrivate; el acceso "
            "directo ya incluye --new-window. No dependas del texto del título para identificar Edge. "
            "Copia la ruta carácter por carácter; no reconstruyas ni "
            "cambies letras o números. Conserva el target_id exacto y úsalo en cada llamada. "
            "Si el launch dice que la ventana ya estaba abierta o devuelve un diálogo, detente. No cambies ni cierres "
            "ventanas o pestañas preexistentes. "
            "Pulsa desktop_key key='L', modifiers=['CTRL'], target_id=<Edge>; lee max=2. Escribe "
            "desktop_type text='https://en.wikipedia.org/wiki/Apollo_11', target_id=<Edge>; lee "
            "query='wikipedia', max=3. Pulsa desktop_key key='ENTER', target_id=<Edge> una vez; lee "
            "query='Apollo 11', max=4 y confirma Wikipedia. Pulsa desktop_key key='F', "
            "modifiers=['CTRL'], target_id=<Edge>; lee query='Buscar en la página', max=3 y sigue sólo "
            "si aparece el campo. Escribe desktop_type text='July 20, 1969', target_id=<Edge>; lee "
            "query='July 20, 1969', max=4. Si esa lectura ya muestra la coincidencia en el OCR, "
            "no pulses Enter; si todavía no aparece, pulsa desktop_key key='ENTER', target_id=<Edge> "
            "una vez y lee query='July 20, 1969', max=8. Confirma la fecha "
            "en OCR del artículo y resume el contexto visible. Sin clics ni ediciones; si no aparece, "
            "detente sin afirmar éxito.")
    if case_id == "CU08":
        if edge_shortcut is None:
            raise ValueError("CU08 requiere un acceso directo de Edge con perfil de usuario existente")
        return (
            "Usa sólo desktop_*. Llama una vez a desktop_launch con app igual al literal exacto "
            f"{str(edge_shortcut)!r} y args como cadena vacía. Abre una ventana nueva de Microsoft Edge "
            "con el perfil normal existente del usuario, nunca Guest/Invitado ni InPrivate; el acceso "
            "directo ya incluye --new-window. No dependas del texto del título para identificar Edge. "
            "Conserva el target_id exacto que devuelve y úsalo en todas las tools. Si el launch dice que "
            "la ventana ya estaba abierta o devuelve un diálogo, detente. "
            "No cambies ni cierres ventanas o pestañas preexistentes. "
            "Lee desktop_read_text target_id=<Edge>, query='Microsoft Edge', "
            "max=2. Pulsa desktop_key key='L', modifiers=['CTRL'], target_id=<Edge>; lee de nuevo "
            "con desktop_read_text target_id=<Edge>, max=2. Escribe desktop_type text='Apollo 11 "
            "landing date', target_id=<Edge>; lee query='Apollo 11 landing date', max=3. Pulsa "
            "desktop_key key='ENTER', target_id=<Edge> una vez y lee query='Apollo 11', max=3. "
            "Confirma Apollo 11 en la primera pestaña. Pulsa desktop_key key='T', "
            "modifiers=['CTRL'], target_id=<Edge>; lee target_id=<Edge>, max=2 y confirma la pestaña "
            "nueva. Escribe desktop_type text='Apollo 12 landing date', target_id=<Edge>; lee "
            "query='Apollo 12 landing date', max=3. Pulsa desktop_key key='ENTER', target_id=<Edge> "
            "una vez y lee query='Apollo 12', max=3. Confirma Apollo 12 en la segunda pestaña. "
            "Pulsa desktop_key key='TAB', modifiers=['CTRL','SHIFT'], target_id=<Edge> una vez y lee "
            "query='Apollo 11', max=3 para confirmar el regreso. No cierres pestañas ni repitas búsquedas.")
    if case_id == "CU09":
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. El harness preparó un libro "
            "xlsx vacío en " + excel_book + ". Ábrelo en una instancia nueva de Excel "
            "usando desktop_launch con app=" + excel_app + " y args=" + repr(exact_excel_args)
            + ". Valor literal de args para desktop_launch: "
            + repr(exact_excel_args) + ". Copia este valor exactamente; no reconstruyas la ruta "
            "ni reutilices otra carpeta. Primero lee la ventana y confirma por el título que abriste "
            "cu20-computer-usage.xlsx y que la cuadrícula está visible. Si no coincide, detente "
            "sin escribir. En la hoja "
            "llena A1:C4 con estos valores usando tabuladores y saltos de línea: "
            "Producto, Cantidad, Precio; Café, 2, 1250; Té, 3, 800; Agua, 1, 500. "
            "Verifica que las 12 celdas y la ubicación sean exactas con desktop_read_text max=32. "
            "Guarda el libro existente una sola vez: consulta desktop_controls query='Guardar', "
            "selecciona el botón habilitado Guardar de la ventana principal (no el control de un "
            "panel) y pulsa con desktop_click_element usando su control_id, target_id y snapshot_id "
            "recientes. No uses desktop_control_action action='click'. Luego lee el título y las "
            "celdas; el título debe incluir cu20-computer-usage.xlsx y A1:C4 debe permanecer intacto. "
            "No abras Guardar como ni otra ventana. Después de esa lectura final, termina y responde "
            "brevemente.")
    if case_id == "CU10":
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. Abre Excel en instancia "
            "nueva con una sola llamada desktop_launch app=" + repr(str(EXCEL_EXE))
            + " y args=" + repr(exact_excel_args) + ". No uses backticks en los valores. "
            "args debe contener /x seguido de la ruta entre comillas dobles; conserva esas comillas "
            "y no agregues caracteres al valor. "
            "Copia exactamente la ruta indicada; no la reconstruyas ni reutilices otra carpeta. "
            "Trabaja sólo en ese libro y no abras ninguna otra app. Primero usa desktop_read_text y "
            "confirma que el título incluye cu20-computer-usage.xlsx y que se ve la cuadrícula. "
            "Si el título es correcto pero la cuadrícula aún no aparece, espera una sola vez con "
            "desktop_wait_for target_id=<target_id de Excel>, query='D1', role='dataitem', "
            "timeout_ms=30000 y vuelve a leer. Si no aparece la cuadrícula, detente sin escribir. "
            "Selecciona la celda D1 por UI Automation: ejecuta "
            "desktop_controls con query='D1' y el target_id de Excel, identifica la celda exacta cuyo "
            "automationId o nombre sea D1 y usa desktop_click_element con ese control_id, target_id "
            "y el snapshot_id de esa misma lectura. Escribe una sola vez Total cantidades (sin '=') "
            "y pulsa Enter. Luego consulta desktop_controls query='D2', identifica el control D2 y "
            "haz click con desktop_click_element usando su control_id y snapshot_id recientes. "
            "Ejecuta desktop_type con text='=B2+B3+B4' exactamente: el primer carácter es '=', "
            "sin ningún carácter antes ni después. No uses desktop_control_action para editar esta "
            "celda y no llames desktop_type más de una vez. Después pulsa Enter y ejecuta "
            "desktop_read_text query='D2'; verifica que D2 muestre 6. Sólo si muestra 6, guarda "
            "con el botón UIA cuyo nombre exacto sea Guardar: consulta desktop_controls "
            "query='Guardar' y ejecuta desktop_click_element con su control_id, target_id y "
            "snapshot_id recientes. Luego lee desktop_read_text query='cu20-computer-usage.xlsx' "
            "para confirmar el libro. Si no existe un botón exacto Guardar, usa una sola vez "
            "desktop_key key='S', modifiers=['CTRL'], target_id=<target_id de Excel> y vuelve a "
            "leer el título. No repitas acciones, no vuelvas a iniciar Excel ni abras otra ventana; "
            "después de esa lectura final, termina y responde brevemente. Si no encuentras la celda "
            "exacta en UIA, termina como no verificado sin escribir.")
    if case_id == "CU11":
        return (
            "Usa sólo desktop_*. Abre una vez Excel con app=" + repr(str(EXCEL_EXE))
            + " y args=" + repr(exact_excel_args) + ". Copia app/args exactamente; no reconstruyas "
            "la ruta ni uses backticks "
            "ni relances Excel. Conserva el target_id del launch; si cambia el HWND, usa el id nuevo. "
            "Si aparece la recuperación de este libro, pulsa el botón exacto No una vez; Ante cualquier "
            "otro diálogo, detente sin responderlo. Lee el libro y confirma B2=2. Selecciona B2: ejecuta "
            "desktop_controls query='Cuadro de nombres'; exige un único combobox o edit y usa sus "
            "control_id, target_id y snapshot_id recientes en desktop_control_action "
            "action='set_value', value='B2'. Esa acción deja el foco en el cuadro de nombres: la "
            "siguiente llamada DEBE ser desktop_key key='ENTER', target_id=<Excel>. No leas ni escribas "
            "antes de ese Enter. Luego ejecuta desktop_read_text query='B2', target_id=<Excel>, "
            "max=8 y confirma 2. Ejecuta desktop_type text='4', target_id=<Excel> una sola vez; "
            "la siguiente tool debe ser desktop_read_text query='B2', target_id=<Excel>, max=8. "
            "Si falla, detente sin reintentar. Pulsa desktop_key key='ENTER', target_id=<Excel> una vez y verifica "
            "B2=4 y D2=8 con desktop_read_text queries separadas. No inspecciones ni edites D2 antes. "
            "Leer D2=8 no termina el caso: la siguiente llamada debe ser desktop_controls "
            "query='Guardar'. Exige un único botón Guardar habilitado en la ventana del libro y "
            "ejecuta desktop_click_element una vez usando control_id, target_id y snapshot_id recientes. "
            "No termines antes de guardar. Después ejecuta "
            "desktop_read_text query='B2' y desktop_read_text query='D2' por separado y confirma 4 y 8. "
            "No repitas acciones. No uses coordenadas, Guardar como ni cierres diálogos.")
    if case_id == "CU12":
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. Abre Excel en instancia "
            "nueva con app=" + excel_app + " y args=" + repr(exact_excel_args) + ". "
            "Copia exactamente la ruta indicada; no la reconstruyas ni reutilices otra carpeta. "
            "Conserva el target_id del launch. Antes de editar, ejecuta desktop_read_text "
            "query='cu20-computer-usage.xlsx', target_id=<Excel>, max=8. Sólo continúa si la lectura "
            "confirma ese nombre exacto en el título. Si todavía no aparece, ejecuta una vez "
            "desktop_wait_for window_title='cu20-computer-usage.xlsx', timeout_ms=30000 y vuelve a "
            "leer el título. Si aún no coincide, detente sin editar. No llames desktop_windows, "
            "desktop_focus ni desktop_controls antes de confirmar el título exacto. Luego lee una vez "
            "encabezados y precios. No edites valores ni fórmulas. Para seleccionar "
            "A1:D1, consulta desktop_controls query='Cuadro de nombres'; usa control_id, target_id "
            "y snapshot_id de esa respuesta en desktop_control_action action='set_value', "
            "value='A1:D1' una sola vez. Inmediatamente lee desktop_read_text query='Cuadro de nombres', "
            "target_id=<Excel>, max=8. La línea 'Cuadro de nombres: A1:D1' confirma la selección "
            "aunque la herramienta también diga 0 renglones; no interpretes 0 renglones como fallo. "
            "Luego pulsa desktop_key key='ENTER', target_id=<Excel> una vez. "
            "Luego consulta desktop_controls query='Negrita' en la misma ventana. Sólo si aparece "
            "exactamente un botón Negrita habilitado con IDs recientes, pulsa "
            "desktop_click_element una vez con esos IDs. No vuelvas a inspeccionar la grilla por texto. "
            "Para seleccionar C2:C4, vuelve a consultar desktop_controls query='Cuadro de nombres' "
            "y ejecuta desktop_control_action action='set_value', value='C2:C4' una vez con IDs "
            "recientes. Inmediatamente lee desktop_read_text query='Cuadro de nombres', "
            "target_id=<Excel>, max=8. La línea 'Cuadro de nombres: C2:C4' confirma la selección "
            "aunque se indiquen 0 renglones; no vuelvas a seleccionar el rango ni a llamar "
            "desktop_windows o desktop_focus por esa respuesta. Pulsa desktop_key key='ENTER' "
            "una sola vez y aplica formato moneda una sola vez con desktop_key key='4', "
            "modifiers=['CTRL','SHIFT'], target_id=<Excel>. No consultes desktop_read_text por "
            "C2:C4 ni intentes verificar los símbolos en la grilla: UIA puede no exponer las celdas. "
            "La validación independiente del archivo guardado comprobará negrita, moneda y persistencia. "
            "Después consulta "
            "desktop_controls query='Guardar'; sólo si hay exactamente un botón Guardar habilitado "
            "en la ventana del libro, púlsalo una vez con sus IDs recientes. Lee el libro una vez "
            "más y termina. Si falta un control, hay varios candidatos o una acción falla, detente "
            "sin repetirla ni sustituirla por coordenadas o tipeo. No uses Ctrl+B ni Ctrl+S; "
            "la validación independiente comprobará ambos formatos y la persistencia del archivo.")
    if case_id == "CU13":
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. El harness preparó el workbook "
            "sintético de sólo lectura. No edites ni guardes sus celdas. Ejecuta desktop_launch una vez "
            "con app=" + repr(str(EXCEL_EXE)) + " y args=" + repr(exact_excel_args) + ". No uses backticks. "
            "Conserva las comillas dobles internas de la ruta; no agregues caracteres ni reconstruyas args. "
            "desktop_launch devuelve un target_id utilizable aunque el título diga 'Abriendo - Excel'. "
            "Llama de inmediato desktop_read_text query='cu20-computer-usage.xlsx' con ese id y luego "
            "desktop_read_text sin query para leer la hoja completa. No llames desktop_windows ni "
            "desktop_focus: no hacen falta y cuentan como acciones extra. Confirma B2=4 y D2=8 si aparecen. "
            "No uses desktop_controls ni hagas más lecturas; termina dejando el libro abierto. El harness lo cerrará "
            "entre turnos y después te pedirá reabrirlo. No guardes ni edites nada.")
    if case_id == "CU14":
        path = workspace / "notepad-exact-line.txt"
        path.touch(exist_ok=True)
        line = CU14_LINE
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. El harness creó el archivo sintético "
            "notepad-exact-line.txt vacío. Abre con desktop_launch app='notepad', args='\"" + str(path) + "\"'. "
            "Copia args exactamente. Espera desktop_wait_for window_title='notepad-exact-line.txt', "
            "timeout_ms=30000 y luego lee desktop_read_text query='notepad-exact-line.txt', max=8 "
            "en el target_id devuelto. Continúa sólo si la ventana confirma ese nombre exacto; "
            "si no, detente sin escribir. Escribe una sola vez " + repr(line) + " con "
            "desktop_type y ese target_id. Guarda con desktop_key key='S', modifiers=['CTRL'] una vez y "
            "lee una vez query=" + repr(line) + ", max=8, en el mismo target. Termina si muestra la línea "
            "exacta una vez. No abras otra app ni repitas la escritura.")
    if case_id == "CU15":
        path = workspace / "notepad-replace.txt"
        path.write_text("The quick brown fox jumps over the sleepy dog.\n", encoding="utf-8")
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. Abre Notepad con desktop_launch app='notepad', "
            "args='\"" + str(path) + "\"'. Conserva el target_id devuelto aunque reutilice una ventana con pestañas, "
            "y pásalo explícitamente a cada tool. Lee el texto visible; confirma el título notepad-replace.txt y la "
            "oración exacta 'The quick brown fox jumps over the sleepy dog.'. Consulta desktop_controls "
            "query='Reemplazar todo' con ese target_id. Si devuelve el botón exacto habilitado, el panel ya está abierto; "
            "si no, ejecuta una sola vez desktop_key key='H', modifiers=['CTRL'], target_id=<target_id> y vuelve a "
            "consultar. Para cambiar campos que ya contienen texto, no uses desktop_type ni Tab: selecciona con "
            "desktop_controls query='Buscar' el control editable exacto (role edit, no botón) y usa "
            "desktop_control_action action='set_value', value='sleepy' con su control_id, target_id y snapshot_id "
            "recientes. Luego consulta desktop_controls query='Reemplazar'; selecciona el control editable exacto "
            "(role edit, no botón) y usa desktop_control_action action='set_value', value='curious' con su control_id, "
            "target_id y snapshot_id recientes. Consulta otra vez desktop_controls query='Reemplazar todo' y pulsa "
            "una sola vez el botón exacto con desktop_click_element usando su control_id, target_id y snapshot_id "
            "de esa consulta. Después del clic ejecuta desktop_read_text para completar cualquier checkpoint "
            "de verificación del runtime. Esa lectura no termina CU15 aunque muestre curious: después guarda con "
            "desktop_key key='S', modifiers=['CTRL'], target_id=<target_id> una vez. Luego haz un readback final "
            "con desktop_read_text y confirma el texto exacto, la ruta notepad-replace.txt y que el título ya no "
            "tiene asterisco de cambios pendientes. No respondas final antes del readback posterior al guardado. "
            "No uses coordenadas "
            "ni edites otra pestaña; si un campo o botón no es inequívoco, detente sin continuar.")
    if case_id == "CU16":
        path = workspace / "paint-rectangle.png"
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. Abre en Paint el PNG sintético existente con "
            "desktop_launch app='mspaint', args='\"" + str(path) + "\"'. Lee con desktop_read_text el target_id "
            "devuelto y confirma que el título incluye paint-rectangle.png. Llama desktop_observe una sola vez con "
            "ese target_id y scope_kind='window'. En esa captura confirma el lienzo en blanco y localiza el icono "
            "Rectángulo; si no puedes confirmar ambos, detente sin dibujar. Haz un único desktop_click "
            "target_id=<ventana>, scope_kind='window', x=0.279, y=0.088 sobre ese icono. No uses UIA ni repitas "
            "el clic. desktop_stroke usa coordenadas de TODA la ventana; el lienzo ocupa aproximadamente "
            "x=0.40..0.60 e y=0.42..0.71. El argumento points DEBE ser una lista de objetos con esta sintaxis "
            "literal: [{\"x\":0.44,\"y\":0.47},{\"x\":0.56,\"y\":0.66}]. NO uses pares internos "
            "[[0.44,0.47],[0.56,0.66]]; la herramienta los rechaza sin dibujar. Si no puedes producir los "
            "dos objetos exactos, detente sin llamar desktop_stroke. Omite scope_kind porque el target_id es "
            "la ventana. Luego llama desktop_focus al mismo target_id, guarda una sola vez con "
            "desktop_key key='S', modifiers=['CTRL'] y lee el título una vez. Termina; el harness comprobará "
            "independientemente que el PNG guardado contenga cuatro lados rectos. No repitas el trazo ni abras "
            "archivos ajenos.")
    if case_id == "CU17":
        target = workspace / "CU20-select-this-file.txt"
        target.write_text("Synthetic selection target.\n", encoding="utf-8")
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. Abre con desktop_launch "
            "app='explorer', args='\"" + str(workspace) + "\"'. Lee esa ventana una vez y confirma "
            "que el título muestra exactamente la carpeta solicitada. Luego llama una sola vez a "
            "desktop_controls con query='" + target.name + "' y max=8 en ese target. Si aparece un "
            "único control cuyo nombre sea exactamente " + repr(target.name) + ", selecciónalo una sola "
            "vez con desktop_control_action action='select' usando su control_id, snapshot_id y "
            "target_id recién devueltos. Después lee esa misma ventana una sola vez y confirma el "
            "título de la carpeta y el archivo exacto. Si el control exacto no aparece o la acción "
            "falla, detente e informa el obstáculo: no hagas clics, no adivines coordenadas, no abras, "
            "edites, muevas ni elimines archivos y no repitas consultas ni acciones.")
    if case_id == "CU18":
        source = workspace / "clipboard-source.txt"
        source.write_text(CLIPBOARD_MARKER, encoding="utf-8")
        return (
            "Usá sólo herramientas desktop_* para esta primera fase de CU18. Abre una vez Notepad con app='notepad', "
            "args=" + repr('"' + str(source) + '"') + ". En la respuesta de desktop_launch, conserva su target_id. "
            "Lee una vez con desktop_read_text query=" + repr(CLIPBOARD_MARKER) + ", target_id=<ese id>; "
            "confirma que el título nombra clipboard-source.txt y que el texto visible contiene exactamente "
            + repr(CLIPBOARD_MARKER) + ". Después enfoca ese mismo target_id con desktop_focus antes de usar teclas. "
            "Si el título o el marcador no aparecen, termina ahora sin pulsar teclas ni abrir Excel. "
            "desktop_key no recibe target_id: usa el foco confirmado. Llama desktop_key key='A', "
            "modifiers=['CTRL'] una vez. "
            "La SIGUIENTE llamada, sin ninguna tool ni respuesta intermedia, DEBE ser "
            "desktop_key key='C', modifiers=['CTRL'] una vez. La llamada inmediatamente posterior DEBE ser "
            "desktop_clipboard op='get'. Sólo si el portapapeles devuelve exactamente " + repr(CLIPBOARD_MARKER) + ", "
            "puedes terminar esta fase; como máximo, haz una única lectura final de sólo lectura del mismo marcador "
            "en Notepad y luego termina. Si devuelve cualquier otro valor, "
            "detente y no abras Excel. No omitas Ctrl+C, no uses desktop_type ni clipboard op='set'.")

    if case_id == "CU19":
        first, second = cu19_document_paths(workspace)
        first.touch(exist_ok=True)
        second.touch(exist_ok=True)
        return (
            "Usá sólo desktop_* de Computer Usage. Abre alfa con desktop_launch app='notepad', args='\""
            + str(first) + "\"'. Inmediatamente lee una vez desktop_read_text sin query con el id devuelto. "
            "Confirma sólo por la línea Título de ventana que contiene exactamente '" + first.name
            + "'; un cuerpo vacío es normal y no bloquea la prueba. No uses el texto del documento "
            "como prueba del título ni edites alfa. Abre beta sólo después de esa lectura, con una "
            "segunda llamada desktop_launch app='notepad', args='\"" + str(second)
            + "\"'; es otra ruta y otro archivo de esta prueba. Inmediatamente lee una vez "
            "desktop_read_text sin query con el id devuelto; confirma por la línea Título de ventana "
            "que contiene exactamente '" + second.name + "'. Después usa desktop_windows una vez "
            "para confirmar que alfa y beta siguen abiertas. Enfoca beta con desktop_focus y continúa "
            "sólo si confirma beta por título. Consulta desktop_controls target_id=beta, "
            "query='Editor de texto', max=4; elige el control principal document o edit con "
            "keyboardFocusable=1 y confirma el foco con un solo desktop_click_element usando "
            "control_id y snapshot_id actuales. Continúa sólo si devuelve keyboardFocusConfirmed=true. "
            "Escribe una sola vez en beta usando desktop_type "
            "text='contenido beta solicitado' y target_id de beta. Lee enseguida con desktop_read_text "
            "query='contenido beta solicitado' y target_id beta; si no coincide exactamente, detente "
            "sin guardar. Si coincide, guarda una sola vez con desktop_key key='S', "
            "modifiers=['CTRL'] y vuelve a leer con desktop_read_text "
            "query='contenido beta solicitado' y el mismo target_id beta. No modifiques alfa, no repitas "
            "escrituras ni lanzamientos, y no respondas final antes del readback posterior al guardado.")
    if case_id == "CU20":
        path = workspace / "notepad-no-duplicate.txt"
        path.touch(exist_ok=True)
        phrase = "CU20-FRASE-UNICA-9F2B"
        return (
            "Usá únicamente herramientas desktop_* de Computer Usage. Abre Notepad con "
            "desktop_launch app='notepad', args='\"" + str(path) + "\"'. Inmediatamente usa "
            "desktop_read_text target_id=<id devuelto> sin query y confirma en el título exactamente '"
            + path.name + "'. Si la ventana ya estaba abierta, elige ese target con desktop_focus "
            "antes de escribir. Escribe la frase " + repr(phrase) + " exactamente una sola vez con "
            "desktop_type text=<frase>, target_id=<id confirmado>. Lee el documento una vez con "
            "desktop_read_text target_id=<mismo id>; continúa sólo si la frase aparece exactamente "
            "una vez. Guarda una sola vez con desktop_key key='S', modifiers=['CTRL'], "
            "target_id=<mismo id> (key lleva 'S', nunca 'CTRL'). Haz una lectura final con "
            "desktop_read_text y confirma que la frase sigue apareciendo una sola vez. Si una "
            "lectura es ambigua, vuelve a observar sin escribir ni guardar de nuevo.")
    raise ValueError(f"Caso no definido: {case_id}")


def cu18_paste_prompt(workspace: pathlib.Path) -> str:
    target_book = workspace / "clipboard-paste.xlsx"
    exact_excel_args = '/x "' + str(target_book) + '"'
    return (
        "Continúa CU18 con herramientas desktop_*; el turno anterior ya confirmó en el portapapeles "
        "CU20-CLIPBOARD-7K9-PRESERVE. Primero ejecuta desktop_clipboard op='get' y continúa sólo si "
        "el texto sigue siendo exactamente CU20-CLIPBOARD-7K9-PRESERVE. Si no, detente sin abrir Excel. "
        "Abre una vez Excel con app="
        + repr(str(EXCEL_EXE)) + " args=" + repr(exact_excel_args)
        + ". Copia los argumentos exactamente; no uses backticks y conserva /x y las comillas de la ruta. "
        "Espera con "
        "desktop_wait_for window_title='clipboard-paste.xlsx - Excel', timeout_ms=30000; usa su windowId "
        "como target_id. Lee el título con desktop_read_text query='clipboard-paste.xlsx' y continúa sólo "
        "si confirma ese libro. Enfócalo. Consulta desktop_controls query='Cuadro de nombres'; exige un único "
        "control editable con rol edit o combobox. Fija A1 con desktop_control_action action='set_value', value='A1' "
        "y los control_id, target_id y snapshot_id recientes. "
        "Confirma que la acción tuvo éxito y pulsa desktop_key key='ENTER' una vez. Después pulsa "
        "desktop_key key='V', modifiers=['CTRL'], target_id=<Excel> una sola vez. Para guardar, "
        "consulta desktop_controls query='Guardar'; exige un único botón Guardar habilitado y púlsalo "
        "una sola vez con desktop_click_element y sus control_id, target_id y snapshot_id recientes. "
        "No uses Ctrl+S. Lee la hoja completa con "
        "desktop_read_text con sólo target_id=<Excel>, sin query; exige la línea "
        "A1: CU20-CLIPBOARD-7K9-PRESERVE y 'Guardado en Este PC'. Si no aparece, "
        "detente sin repetir el pegado. No escribas el marcador ni abras otra app.")


def cu13_reopen_prompt(workspace: pathlib.Path) -> str:
    workbook = workspace / "cu20-computer-usage.xlsx"
    excel_args = f'/x "{workbook}"'
    return (
        "Usá únicamente herramientas desktop_* de Computer Usage. El harness ya cerró la ventana anterior "
        "del workbook sintético de esta prueba. Ignora cualquier target_id previo: ya no existe. Abre de nuevo "
        "el archivo usando desktop_launch con app=" + repr(str(EXCEL_EXE)) + " y args=" + repr(excel_args) + ". "
        "No uses backticks, desktop_windows ni desktop_focus. Usa enseguida el target_id nuevo devuelto: lee una vez desktop_read_text "
        "query='cu20-computer-usage.xlsx' y una vez la hoja completa con desktop_read_text sin query. "
        "Confirma B2=4 y D2=8 si aparecen. No edites ni guardes el libro; termina después de leerlo.")


def cu13_target_continues(title_event: tuple, sheet_event: tuple) -> bool:
    title_target = str(title_event[2].get("target_id", ""))
    sheet_target = str(sheet_event[2].get("target_id", ""))
    if not title_target or not sheet_target:
        return False
    if title_target.casefold() == sheet_target.casefold():
        return True
    replacement = re.search(r"reemplazado por\s+([^\s;]+)", title_event[4], re.IGNORECASE)
    return bool(replacement and replacement.group(1).casefold() == sheet_target.casefold())


def apply_excel_recovery_authorization(case_id: str, prompt: str,
                                       workspace: pathlib.Path | None = None) -> str:
    if case_id not in {"CU09", "CU10", "CU11", "CU12", "CU13", "CU18"}:
        return prompt
    synthetic_books = ["cu20-computer-usage.xlsx", "clipboard-paste.xlsx"]
    exact_workspace = str(workspace) if workspace is not None else "<workspace sintético actual>"
    return (
        "El usuario autorizó cerrar aplicaciones y descartar cambios de libros sintéticos creados por esta campaña. "
        "Este turno creó el workbook en " + exact_workspace + ". Si el cuadro identifica por título/ruta un libro "
        "sintético de esta campaña (nombres esperados: " + ", ".join(synthetic_books) + "), puedes responder "
        "una sola vez No al aviso de recuperación o No guardar al aviso de cambios y comprobar que desapareció. "
        "No descartes documentos ajenos ni respondas a Firewall, permisos u otros diálogos de Windows. "
        + prompt
    )


def clipboard_snapshot() -> dict:
    import win32clipboard

    formats = {13, 16, 1, 7}  # CF_UNICODETEXT, CF_LOCALE, CF_TEXT, CF_OEMTEXT
    snapshot = {"formats": [], "data": {}}
    win32clipboard.OpenClipboard()
    try:
        fmt = 0
        while True:
            fmt = win32clipboard.EnumClipboardFormats(fmt)
            if not fmt:
                break
            snapshot["formats"].append(fmt)
        unsupported = set(snapshot["formats"]) - formats
        if unsupported:
            raise RuntimeError("El portapapeles contiene formatos que no puedo preservar con seguridad")
        for fmt in snapshot["formats"]:
            snapshot["data"][fmt] = win32clipboard.GetClipboardData(fmt)
    finally:
        win32clipboard.CloseClipboard()
    return snapshot


def restore_clipboard_if_unchanged(snapshot: dict) -> str:
    import win32clipboard

    win32clipboard.OpenClipboard()
    try:
        try:
            current = win32clipboard.GetClipboardData(13)
        except Exception:
            current = None
        if not isinstance(current, str) or current.strip() != CLIPBOARD_MARKER:
            return "left-unchanged-by-test-or-user-change-detected"
        win32clipboard.EmptyClipboard()
        for fmt in (16, 13, 1, 7):
            if fmt in snapshot["data"]:
                win32clipboard.SetClipboardData(fmt, snapshot["data"][fmt])
        return "restored-original-formats"
    finally:
        win32clipboard.CloseClipboard()


def validate_cu18_copy_stage(delta: list, expected_workspace: pathlib.Path) -> dict:
    """Gate Excel launch on an exact, observed Notepad-to-clipboard copy."""
    events = [message for message in delta
              if isinstance(message, dict) and message.get("role") == "toolcall"]
    expected_names = ["desktop_launch", "desktop_read_text", "desktop_focus",
                      "desktop_key", "desktop_key", "desktop_clipboard"]
    names = [message.get("name") for message in events]

    def args_of(message: dict) -> dict:
        try:
            value = json.loads(message.get("arguments", "{}"))
            return value if isinstance(value, dict) else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    def norm_path(value: str) -> str:
        return str(value).strip().strip('"').replace("/", "\\").rstrip("\\").casefold()

    optional_readback = names == expected_names + ["desktop_read_text"]
    if names != expected_names and not optional_readback:
        return {"passed": False, "strict_sequence": False,
                "expected_tools": expected_names, "actual_tools": names,
                "excel_not_opened_by_gate": "desktop_launch" not in names[1:]}

    launch, read, focus, select_all, copy, clipboard = events[:6]
    launch_args, read_args, focus_args = args_of(launch), args_of(read), args_of(focus)
    select_args, copy_args, clipboard_args = (
        args_of(select_all), args_of(copy), args_of(clipboard))
    readback = events[6] if optional_readback else None
    match = re.search(r"\bid=([0-9a-f]+)\b", str(launch.get("output", "")), re.IGNORECASE)
    target_id = match.group(1) if match else ""
    marker = CLIPBOARD_MARKER
    source_path = str(expected_workspace / "clipboard-source.txt")
    read_output = str(read.get("output", ""))
    read_ok = (read.get("ok") is True
               and str(read_args.get("target_id", "")) == target_id
               and str(read_args.get("query", "")).casefold() == marker.casefold()
               and "clipboard-source.txt" in read_output.casefold()
               and marker in read_output)
    def chord_ok(message: dict, arguments: dict, key: str) -> bool:
        return (message.get("ok") is True
                and str(arguments.get("key", "")).upper() == key
                and {str(x).upper() for x in arguments.get("modifiers", [])} == {"CTRL"}
                and str(arguments.get("target_id", target_id)) == target_id)

    checks = {
        "source_launch_exact": (launch.get("ok") is True and target_id
                                and str(launch_args.get("app", "")).casefold() == "notepad"
                                and norm_path(str(launch_args.get("args", "")))
                                == norm_path(source_path)),
        "source_title_and_marker_read": read_ok,
        "source_focused_before_keys": (focus.get("ok") is True
                                        and str(focus_args.get("target_id", "")) == target_id
                                        and read.get("ok") is True),
        "ctrl_a_then_ctrl_c": (chord_ok(select_all, select_args, "A")
                               and chord_ok(copy, copy_args, "C")),
        "clipboard_exact": (clipboard.get("ok") is True
                            and str(clipboard_args.get("op", "")).casefold() == "get"
                            and marker in str(clipboard.get("output", ""))),
        "optional_final_source_readback": (readback is None or (
            readback.get("ok") is True
            and str(args_of(readback).get("target_id", "")) == target_id
            and str(args_of(readback).get("query", "")).casefold() == marker.casefold()
            and marker in str(readback.get("output", "")))),
        "all_tools_successful": all(message.get("ok") is True for message in events),
    }
    return {"passed": all(checks.values()), "strict_sequence": True,
            "tool_event_count": len(events), "excel_not_opened_by_gate": True,
            "source_readback_after_copy": optional_readback,
            **checks}


def validate_cu18_sequence(delta: list, expected_workspace: pathlib.Path | None) -> dict:
    """Require a verified Notepad -> clipboard -> Excel paste-and-save sequence."""
    marker = CLIPBOARD_MARKER
    events = [(index, message) for index, message in enumerate(delta)
              if isinstance(message, dict) and message.get("role") == "toolcall"]

    def args_of(message: dict) -> dict:
        try:
            value = json.loads(message.get("arguments", "{}"))
            return value if isinstance(value, dict) else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    def norm_path(value: str) -> str:
        return str(value).strip().strip('"').replace("/", "\\").rstrip("\\").casefold()

    def window_id(message: dict) -> str:
        match = re.search(r"\bid=([0-9a-f]+)\b", str(message.get("output", "")), re.IGNORECASE)
        return match.group(1) if match else ""

    def json_line(message: dict) -> dict:
        match = re.search(r"(?m)^(\{[^\r\n]*\})$", str(message.get("output", "")))
        if not match:
            return {}
        try:
            value = json.loads(match.group(1))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}

    names = [message.get("name") for _, message in events]
    expected_names = [
        "desktop_launch", "desktop_read_text", "desktop_focus", "desktop_key",
        "desktop_key", "desktop_clipboard", "desktop_clipboard", "desktop_launch",
        "desktop_wait_for", "desktop_read_text", "desktop_focus", "desktop_controls",
        "desktop_control_action", "desktop_key", "desktop_key", "desktop_controls",
        "desktop_click_element", "desktop_read_text",
    ]
    optional_readback_names = expected_names[:6] + ["desktop_read_text"] + expected_names[6:]
    source_readback_after_copy = names == optional_readback_names
    sequence_ok = names == expected_names or source_readback_after_copy
    expected_tool_count = len(events) if sequence_ok else len(expected_names)
    tools_ok = sequence_ok and all(message.get("ok") is True for _, message in events)
    if expected_workspace is None:
        return {"passed": False, "strict_sequence": False,
                "reason": "expected_workspace es obligatorio para certificar CU18"}
    if not sequence_ok:
        return {"passed": False, "strict_sequence": False,
                "expected_tool_count": expected_tool_count, "actual_tool_count": len(events),
                "tool_sequence_matches": False}

    source_path = str(expected_workspace / "clipboard-source.txt")
    workbook_path = str(expected_workspace / "clipboard-paste.xlsx")
    by_name = [(index, message, args_of(message)) for index, message in events]
    source_launch_i, source_launch, source_launch_args = by_name[0]
    source_id = window_id(source_launch)
    source_read_i, source_read, source_read_args = by_name[1]
    source_focus_i, source_focus, source_focus_args = by_name[2]
    select_all_i, select_all, select_all_args = by_name[3]
    copy_i, copy, copy_args = by_name[4]
    first_clip_i, first_clip, first_clip_args = by_name[5]
    continuation_cursor = 7 if source_readback_after_copy else 6
    source_verify = by_name[6] if source_readback_after_copy else None
    reset_clip_i, reset_clip, reset_clip_args = by_name[continuation_cursor]
    excel_launch_i, excel_launch, excel_launch_args = by_name[continuation_cursor + 1]
    wait_i, wait_event, wait_args = by_name[continuation_cursor + 2]
    title_i, title_read, title_args = by_name[continuation_cursor + 3]
    excel_focus_i, excel_focus, excel_focus_args = by_name[continuation_cursor + 4]
    controls_i, controls, controls_args = by_name[continuation_cursor + 5]
    set_i, set_action, set_args = by_name[continuation_cursor + 6]
    enter_i, enter_key, enter_args = by_name[continuation_cursor + 7]
    paste_i, paste, paste_args = by_name[continuation_cursor + 8]
    save_query_i, save_query, save_query_args = by_name[continuation_cursor + 9]
    save_click_i, save_click, save_click_args = by_name[continuation_cursor + 10]
    final_i, final_read, final_args = by_name[continuation_cursor + 11]

    source_launch_ok = (source_launch.get("ok") is True
                        and str(source_launch_args.get("app", "")).casefold() == "notepad"
                        and norm_path(str(source_launch_args.get("args", ""))) == norm_path(source_path)
                        and bool(source_id))
    source_read_output = str(source_read.get("output", ""))
    source_read_ok = (source_read.get("ok") is True
                      and str(source_read_args.get("target_id", "")) == source_id
                      and str(source_read_args.get("query", "")).casefold() == marker.casefold()
                      and "clipboard-source.txt" in source_read_output.casefold()
                      and marker in source_read_output)
    source_focus_ok = (source_focus.get("ok") is True
                       and str(source_focus_args.get("target_id", "")) == source_id)
    source_verify_ok = (source_verify is None or (
        source_verify[1].get("ok") is True
        and str(source_verify[2].get("target_id", "")) == source_id
        and str(source_verify[2].get("query", "")).casefold() == marker.casefold()
        and marker in str(source_verify[1].get("output", ""))))
    select_all_ok = (select_all.get("ok") is True
                     and str(select_all_args.get("key", "")).upper() == "A"
                     and {str(x).upper() for x in select_all_args.get("modifiers", [])} == {"CTRL"}
                     and str(select_all_args.get("target_id", source_id)) == source_id)
    copy_ok = (copy.get("ok") is True
               and str(copy_args.get("key", "")).upper() == "C"
               and {str(x).upper() for x in copy_args.get("modifiers", [])} == {"CTRL"}
               and str(copy_args.get("target_id", source_id)) == source_id)

    def clipboard_ok(event: dict, arguments: dict) -> bool:
        output = str(event.get("output", ""))
        return (event.get("ok") is True
                and str(arguments.get("op", "")).casefold() == "get"
                and marker in output)

    expected_excel_args = f'/x "{workbook_path}"'
    excel_launch_ok = (excel_launch.get("ok") is True
                       and str(excel_launch_args.get("app", "")).casefold()
                       == str(EXCEL_EXE).casefold()
                       and norm_path(str(excel_launch_args.get("args", "")))
                       == norm_path(expected_excel_args))
    wait_payload = json_line(wait_event)
    current_excel_id = str(wait_payload.get("windowId", ""))
    wait_ok = (wait_event.get("ok") is True
               and str(wait_args.get("window_title", "")).casefold()
               == "clipboard-paste.xlsx - excel"
               and int(wait_args.get("timeout_ms", 0) or 0) == 30000
               and not wait_args.get("target_id") and not wait_args.get("query")
               and wait_payload.get("found") is True and bool(current_excel_id)
               and "clipboard-paste.xlsx - Excel" in str(wait_payload.get("title", ""))
               and wait_i > excel_launch_i)
    title_ok = (title_read.get("ok") is True and wait_ok and title_i > wait_i
                and str(title_args.get("target_id", "")) == current_excel_id
                and str(title_args.get("query", "")).casefold() == "clipboard-paste.xlsx"
                and "clipboard-paste.xlsx - Excel" in str(title_read.get("output", "")))
    excel_focus_ok = (excel_focus.get("ok") is True and excel_focus_i > title_i
                      and str(excel_focus_args.get("target_id", "")) == current_excel_id)

    controls_output = str(controls.get("output", ""))
    snapshot_match = re.search(r"(?m)^snapshot_id=([^\s]+)\s*$", controls_output)
    name_box_controls = []
    for line in controls_output.splitlines():
        match = re.search(r'^controlId=([^\s]+)\s+\[([^\]]+)\].*"Cuadro de nombres"\s*$', line,
                          re.IGNORECASE)
        if match and any(role in match.group(2).casefold() for role in ("edit", "combobox")):
            name_box_controls.append(match.group(1))
    name_box_id = name_box_controls[0] if len(name_box_controls) == 1 else ""
    controls_ok = (controls.get("ok") is True and controls_i > excel_focus_i
                   and str(controls_args.get("target_id", "")) == current_excel_id
                   and str(controls_args.get("query", "")).casefold() == "cuadro de nombres"
                   and snapshot_match is not None and len(name_box_controls) == 1)
    set_ok = (set_action.get("ok") is True and set_i > controls_i
              and str(set_args.get("target_id", "")) == current_excel_id
              and str(set_args.get("control_id", "")) == name_box_id
              and str(set_args.get("snapshot_id", "")) == (snapshot_match.group(1) if snapshot_match else "")
              and str(set_args.get("action", "")).casefold() == "set_value"
              and str(set_args.get("value", "")) == "A1")
    enter_ok = (enter_key.get("ok") is True and enter_i > set_i
                and str(enter_args.get("key", "")).upper() == "ENTER"
                and not enter_args.get("modifiers")
                and str(enter_args.get("target_id", current_excel_id)) == current_excel_id)
    paste_ok = (paste.get("ok") is True and paste_i > enter_i
                and str(paste_args.get("key", "")).upper() == "V"
                and {str(x).upper() for x in paste_args.get("modifiers", [])} == {"CTRL"}
                and str(paste_args.get("target_id", current_excel_id)) == current_excel_id)
    save_query_output = str(save_query.get("output", ""))
    save_snapshot = re.search(r"(?m)^snapshot_id=([^\s]+)\s*$", save_query_output)
    save_buttons = []
    for line in save_query_output.splitlines():
        match = re.search(r'^controlId=([^\s]+)\s+\[([^\]]+)\].*"Guardar"\s*$', line,
                          re.IGNORECASE)
        if (match and "button" in match.group(2).casefold()
                and "invoke" in line.casefold()
                and not re.search(r"\benabled=0\b", line, re.IGNORECASE)):
            save_buttons.append(match.group(1))
    save_button_id = save_buttons[0] if len(save_buttons) == 1 else ""
    save_query_ok = (save_query.get("ok") is True and save_query_i > paste_i
                     and str(save_query_args.get("target_id", "")) == current_excel_id
                     and str(save_query_args.get("query", "")).casefold() == "guardar"
                     and save_snapshot is not None and len(save_buttons) == 1)
    save_ok = (save_click.get("ok") is True and save_click_i > save_query_i
               and str(save_click_args.get("target_id", "")) == current_excel_id
               and str(save_click_args.get("control_id", "")) == save_button_id
               and str(save_click_args.get("snapshot_id", ""))
               == (save_snapshot.group(1) if save_snapshot else ""))
    trace_match = re.search(r"\btrace=(\{.*\})", str(save_click.get("output", "")))
    try:
        save_trace = json.loads(trace_match.group(1)) if trace_match else {}
    except json.JSONDecodeError:
        save_trace = {}
    save_trace_target = save_trace.get("target", {}) if isinstance(save_trace, dict) else {}
    save_trace_ok = (save_trace.get("action") == "click_element"
                     and str(save_trace_target.get("controlId", "")) == save_button_id
                     and str(save_trace_target.get("name", "")) == "Guardar"
                     and str(save_trace_target.get("role", "")).casefold() == "button"
                     and str(save_trace_target.get("windowTargetId", "")) == current_excel_id)
    save_ok = save_ok and save_trace_ok
    final_output = str(final_read.get("output", ""))
    final_ok = (final_read.get("ok") is True and final_i > save_click_i
                and str(final_args.get("target_id", "")) == current_excel_id
                and not final_args.get("query")
                and re.search(r"A1\s*:\s*" + re.escape(marker), final_output)
                and "guardado en este pc" in final_output.casefold())

    checks = {
        "source_launch_exact": source_launch_ok,
        "source_focus_and_marker_read": source_read_ok and source_focus_ok
            and source_launch_i < source_read_i < source_focus_i,
        "optional_source_readback_after_copy": source_verify_ok,
        "ctrl_a_then_ctrl_c": select_all_ok and copy_ok and source_read_i < select_all_i < copy_i,
        "clipboard_marker_verified_before_and_after_session_reset": (
            clipboard_ok(first_clip, first_clip_args) and clipboard_ok(reset_clip, reset_clip_args)
            and copy_i < by_name[5][0] < reset_clip_i < excel_launch_i),
        "excel_launch_exact": excel_launch_ok,
        "excel_wait_title_then_focus": wait_ok and title_ok and excel_focus_ok,
        "name_box_a1_selected_semantically": controls_ok and set_ok and enter_ok,
        "single_ctrl_v": paste_ok,
        "semantic_save_button_clicked_once": save_query_ok and save_ok,
        "saved_workbook_read_back": final_ok,
        "all_tools_successful": tools_ok,
    }
    return {"passed": all(checks.values()), "strict_sequence": sequence_ok,
            "expected_tool_count": expected_tool_count, "actual_tool_count": len(events),
            **checks}

def validate_cu19_sequence(delta: list, expected_workspace: pathlib.Path | None) -> dict:
    """Require a verified Open-dialog switch from alpha to beta and one write."""
    events = [(index, message) for index, message in enumerate(delta)
              if isinstance(message, dict) and message.get("role") == "toolcall"]

    def args_for(message: dict) -> dict:
        try:
            value = json.loads(message.get("arguments", "{}"))
            return value if isinstance(value, dict) else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    def path_for(value: object) -> str:
        return str(value).strip().strip('"').replace("/", "\\").rstrip("\\").casefold()

    def window_id(message: dict) -> str:
        match = re.search(r"\bid=([0-9a-f]+)\b", str(message.get("output", "")),
                          re.IGNORECASE)
        return match.group(1) if match else ""

    def window_id_for_title(message: dict, title: str) -> str:
        for line in str(message.get("output", "")).splitlines():
            if title.casefold() in line.casefold():
                match = re.search(r"\bid=([0-9a-f]+)\b", line, re.IGNORECASE)
                if match:
                    return match.group(1)
        return ""

    def control_line(output: object, control_id: object) -> str:
        expected = str(control_id or "").strip()
        if not expected:
            return ""
        for line in str(output or "").splitlines():
            if line.startswith("controlId=") and line[len("controlId="):].split()[0] == expected:
                return line
        return ""

    def snapshot_id(message: dict) -> str:
        match = re.search(r"(?m)^snapshot_id=([a-zA-Z0-9_-]+)\s*$",
                          str(message.get("output", "")))
        return match.group(1) if match else ""

    def action_trace(message: dict) -> dict:
        match = re.search(r"trace=(\{.*\})(?:\r?\n|$)",
                          str(message.get("output", "")))
        if not match:
            return {}
        try:
            value = json.loads(match.group(1))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}

    expected_names = ["desktop_launch", "desktop_read_text", "desktop_launch",
                      "desktop_read_text", "desktop_windows", "desktop_focus",
                      "desktop_controls", "desktop_click_element", "desktop_type",
                      "desktop_read_text", "desktop_key", "desktop_read_text"]
    names = [message.get("name") for _, message in events]
    if not expected_workspace:
        return {"passed": False, "strict_sequence": False,
                "reason": "expected_workspace es obligatorio para certificar CU19"}
    if names != expected_names:
        return {"passed": False, "strict_sequence": False,
                "expected_tool_count": len(expected_names), "actual_tool_count": len(events),
                "tool_sequence_matches": False}

    alpha_file, beta_file = cu19_document_paths(expected_workspace)
    alpha_path = str(alpha_file)
    beta_path = str(beta_file)
    alpha_launch_i, alpha_launch = events[0]
    alpha_read_i, alpha_read = events[1]
    beta_launch_i, beta_launch = events[2]
    beta_read_i, beta_read = events[3]
    beta_windows_i, beta_windows = events[4]
    beta_focus_i, beta_focus = events[5]
    editor_controls_i, editor_controls = events[6]
    editor_focus_i, editor_focus = events[7]
    type_i, type_call = events[8]
    typed_read_i, typed_read = events[9]
    save_i, save = events[10]
    final_read_i, final_read = events[11]
    alpha_read_args = args_for(alpha_read)
    beta_read_args = args_for(beta_read)
    beta_id = window_id_for_title(beta_windows, beta_file.name)
    alpha_id = str(alpha_read_args.get("target_id", ""))
    if not beta_id:
        beta_id = str(beta_read_args.get("target_id", ""))
    alpha_args = args_for(alpha_launch)
    beta_args = args_for(beta_launch)
    beta_focus_args = args_for(beta_focus)
    editor_controls_args = args_for(editor_controls)
    editor_focus_args = args_for(editor_focus)
    editor_output = str(editor_controls.get("output", ""))
    editor_control_id = str(editor_focus_args.get("control_id", ""))
    editor_line = control_line(editor_output, editor_control_id)
    alpha_read_output = str(alpha_read.get("output", ""))
    beta_read_output = str(beta_read.get("output", ""))
    type_args = args_for(type_call)
    typed_read_args = args_for(typed_read)
    save_args = args_for(save)
    final_read_args = args_for(final_read)
    alpha_title_ok = (alpha_read.get("ok") is True and alpha_id
                      and alpha_read_i > alpha_launch_i
                      and alpha_read_args.get("target_id") == alpha_id
                      and f"Título de ventana: {alpha_file.name}:" in alpha_read_output)
    beta_title_ok = (beta_read.get("ok") is True and beta_id
                     and beta_read_args.get("target_id") == beta_id
                     and f"Título de ventana: {beta_file.name}:" in beta_read_output
                     and beta_windows.get("ok") is True
                     and window_id_for_title(beta_windows, beta_file.name) == beta_id)
    launch_ok = (alpha_launch.get("ok") is True
                 and str(alpha_args.get("app", "")).casefold() == "notepad"
                 and path_for(alpha_args.get("args", "")) == path_for(alpha_path)
                 and bool(alpha_id) and window_id(alpha_launch) == alpha_id and alpha_title_ok)
    launch_beta_ok = (beta_launch.get("ok") is True
                      and str(beta_args.get("app", "")).casefold() == "notepad"
                      and path_for(beta_args.get("args", "")) == path_for(beta_path)
                      and beta_launch_i > alpha_read_i and beta_title_ok)
    beta_focus_ok = (beta_focus.get("ok") is True
                     and beta_focus_args.get("target_id") == beta_id)
    editor_observed = (editor_controls.get("ok") is True
                       and editor_controls_args.get("target_id") == beta_id
                       and bool(snapshot_id(editor_controls))
                       and bool(re.search(r"\[(?:document|edit)\]", editor_line, re.IGNORECASE))
                       and bool(re.search(r"focusable=1", editor_line, re.IGNORECASE)))
    editor_focus_trace = action_trace(editor_focus)
    editor_focus_ok = (editor_focus.get("ok") is True
                       and editor_focus_args.get("target_id") == beta_id
                       and editor_focus_args.get("snapshot_id") == snapshot_id(editor_controls)
                       and bool(editor_control_id)
                       and editor_focus_trace.get("keyboardFocusConfirmed") is True
                       and editor_focus_trace.get("action") == "click_element")
    write_ok = (type_call.get("ok") is True
                and type_args.get("text") == "contenido beta solicitado"
                and type_args.get("target_id") == beta_id
                and editor_focus_i < type_i)
    typed_read_ok = (typed_read.get("ok") is True
                     and typed_read_args.get("query") == "contenido beta solicitado"
                     and typed_read_args.get("target_id") == beta_id
                     and "contenido beta solicitado" in str(typed_read.get("output", "")))
    save_ok = (save.get("ok") is True and str(save_args.get("key", "")).upper() == "S"
               and {str(value).upper() for value in save_args.get("modifiers", [])} == {"CTRL"})
    readback_ok = (final_read.get("ok") is True
                   and final_read_args.get("query") == "contenido beta solicitado"
                   and final_read_args.get("target_id") == beta_id
                   and "contenido beta solicitado" in str(final_read.get("output", "")))
    tools_ok = all(message.get("ok") is True for _, message in events)
    checks = {"exact_alpha_launch": launch_ok,
              "alpha_title_confirmed_before_beta_launch": bool(alpha_title_ok
                                                               and alpha_launch_i < alpha_read_i < beta_launch_i),
              "different_document_launch_allowed": launch_beta_ok,
              # Notepad puede abrir ambos documentos como pestañas de una ventana. La lectura
              # UIA expone los nombres de pestaña; desktop_windows sólo enumera HWND.
              "both_document_titles_confirmed": bool(
                  beta_title_ok and alpha_file.name.casefold() in beta_read_output.casefold()
                  and beta_file.name.casefold() in beta_read_output.casefold()
                  and alpha_read_i < beta_launch_i < beta_read_i < beta_windows_i),
              "beta_focused_before_write": bool(beta_focus_ok
                                                 and beta_windows_i < beta_focus_i < type_i),
              "editor_focus_confirmed_before_write": bool(editor_observed and editor_focus_ok
                                                          and beta_focus_i < editor_controls_i
                                                          < editor_focus_i < type_i),
              "exact_beta_write_once": write_ok,
              "typed_text_confirmed_before_save": bool(typed_read_ok and type_i < typed_read_i < save_i),
              "saved_once_with_ctrl_s": bool(save_ok and typed_read_i < save_i),
              "beta_read_back_after_save": bool(readback_ok and save_i < final_read_i),
              "all_tools_successful": tools_ok}
    return {"passed": all(checks.values()), "strict_sequence": True,
            "expected_tool_count": len(expected_names), "actual_tool_count": len(events),
            **checks}


def validate_ui_evidence(case_id: str, delta: list,
                         inter_turn_excel_cleanup: dict | None = None,
                         expected_workspace: pathlib.Path | None = None) -> dict | None:
    reads = [str(message.get("output", "")) for message in delta
             if isinstance(message, dict) and message.get("role") == "toolcall"
             and message.get("name") == "desktop_read_text"]
    if case_id in {"CU01", "CU02", "CU03", "CU04"}:
        expected = {"CU01": "42", "CU02": "144", "CU03": "36", "CU04": "30"}[case_id]
        pattern = re.compile(rf"(?<![\d.]){re.escape(expected)}(?:[.,]0+)?(?![\d.])")
        matches = [expected for output in reads if pattern.search(output)]
        return {"passed": bool(matches), "expected_display": expected,
                "observed_display_matches": matches}
    if case_id == "CU13":
        events = []
        for index, message in enumerate(delta):
            if not isinstance(message, dict) or message.get("role") != "toolcall":
                continue
            try:
                arguments = json.loads(message.get("arguments", "{}"))
            except (TypeError, json.JSONDecodeError):
                arguments = {}
            events.append((index, message.get("name"), arguments,
                           message.get("ok") is True, str(message.get("output", ""))))
        launches = [event for event in events if event[1] == "desktop_launch"
                    and "cu20-computer-usage.xlsx" in str(event[2].get("args", "")).casefold()]
        title_reads = [event for event in events if event[1] == "desktop_read_text"
                       and str(event[2].get("query", "")).casefold() == "cu20-computer-usage.xlsx"]
        sheet_reads = [event for event in events
                       if event[1] == "desktop_read_text" and not event[2].get("query")]
        user_turn_count = sum(1 for message in delta
                              if isinstance(message, dict) and message.get("role") == "user")
        unexpected_actions = [event[1] for event in events
                              if event[1] not in {"desktop_launch", "desktop_read_text",
                                                  "desktop_controls"}]
        inter_turn_close_ok = bool(
            isinstance(inter_turn_excel_cleanup, dict)
            and inter_turn_excel_cleanup.get("closed_pids")
            and not inter_turn_excel_cleanup.get("remaining_pids"))
        sequence_ok = False
        if len(launches) == 2 and len(title_reads) >= 2 and len(sheet_reads) >= 2 \
                and user_turn_count == 2:
            first_launch, second_launch = launches
            first_title = next((event for event in title_reads
                                if first_launch[0] < event[0] < second_launch[0]), None)
            second_title = next((event for event in title_reads
                                 if event[0] > second_launch[0]), None)
            first_sheet = next((event for event in sheet_reads
                                if first_title and first_title[0] < event[0] < second_launch[0]), None)
            second_sheet = next((event for event in sheet_reads
                                 if second_title and event[0] > second_title[0]), None)
            required_events = [first_launch, first_title, first_sheet,
                               second_launch, second_title, second_sheet]
            sequence_ok = bool(
                all(required_events)
                and first_launch[0] < first_title[0] < first_sheet[0]
                < second_launch[0] < second_title[0] < second_sheet[0]
                and inter_turn_close_ok
                and not unexpected_actions
                and all(event[3] for event in events)
                and all("se abrió" in event[4].casefold() for event in launches)
                and str(first_launch[2].get("args", "")).casefold()
                == str(second_launch[2].get("args", "")).casefold()
                and str(first_launch[2].get("app", "")).casefold()
                == str(second_launch[2].get("app", "")).casefold()
                and all(bool(event[2].get("target_id"))
                        for event in [first_title, second_title, first_sheet, second_sheet])
                and cu13_target_continues(first_title, first_sheet)
                and cu13_target_continues(second_title, second_sheet))
        return {"passed": sequence_ok, "launch_count": len(launches),
                "title_read_count": len(title_reads), "sheet_read_count": len(sheet_reads),
                "user_turn_count": user_turn_count,
                "unexpected_action_count": len(unexpected_actions),
                "excel_closed_between_turns": inter_turn_close_ok,
                "closed_pids_between_turns": ((inter_turn_excel_cleanup or {}).get("closed_pids", [])),
                "remaining_pids_between_turns": ((inter_turn_excel_cleanup or {}).get("remaining_pids", [])),
                "window_opened_twice": len(launches) == 2 and all(
                    "se abrió" in event[4].casefold() for event in launches)}
    if case_id == "CU05":
        date_pattern = re.compile(
            r"\b(?:20\s+(?:de\s+)?July|July\s+20,?|20\s+(?:de\s+)?julio)\s+"
            r"(?:de\s+)?1969\b", re.IGNORECASE)
        day_month_pattern = re.compile(
            r"\b(?:20\s+(?:de\s+)?July|July\s+20|20\s+(?:de\s+)?julio)\b",
            re.IGNORECASE)
        year_pattern = re.compile(r"\b1969\b")
        landing_pattern = re.compile(r"\b(?:landing|landed|aterrizaje|alunizaje)\b",
                                     re.IGNORECASE)

        def has_landing_date(text: str) -> bool:
            has_full_date = bool(date_pattern.search(text))
            has_split_date = (bool(day_month_pattern.search(text))
                              and bool(year_pattern.search(text))
                              and bool(landing_pattern.search(text)))
            return "apollo 11" in text.casefold() and (has_full_date or has_split_date)

        matching_outputs = [output for output in reads
                            if has_landing_date(output)]
        answers = [str(message.get("content", "")) for message in delta
                   if isinstance(message, dict) and message.get("role") == "assistant"]
        matching_answers = [answer for answer in answers if has_landing_date(answer)]
        return {"passed": bool(matching_outputs and matching_answers),
                "required_terms": ["Apollo 11", "landing day/month", "1969"],
                "matching_read_count": len(matching_outputs),
                "matching_answer_count": len(matching_answers)}
    if case_id == "CU06":
        tool_events = [(index, message) for index, message in enumerate(delta)
                       if isinstance(message, dict) and message.get("role") == "toolcall"]
        def arguments_for(message: dict) -> dict:
            try:
                value = json.loads(message.get("arguments", "{}"))
                return value if isinstance(value, dict) else {}
            except (TypeError, json.JSONDecodeError):
                return {}

        expected_url = "https://www.google.com/search?q=historia+de+egipto+en+wikipedia"
        typed_indices = [index for index, message in tool_events
                         if message.get("name") == "desktop_type"
                         and str(arguments_for(message).get("text", "")).casefold()
                         == expected_url
                         and message.get("ok") is True]
        enter_indices = [index for index, message in tool_events
                         if message.get("name") == "desktop_key"
                         and str(arguments_for(message).get("key", "")).upper() == "ENTER"
                         and message.get("ok") is True]
        typed_index = typed_indices[0] if typed_indices else None
        enter_index = next((index for index in enter_indices
                            if typed_index is not None and index > typed_index), None)
        query_reads = [(index, message) for index, message in tool_events
                       if typed_index is not None and enter_index is not None
                       and typed_index < index < enter_index
                       and message.get("name") == "desktop_read_text"
                       and message.get("ok") is True
                       and "historia+de+egipto+en+wikipedia" in
                       str(arguments_for(message).get("query", "")).casefold()]
        google_reads = [(index, message) for index, message in tool_events
                        if enter_index is not None and index > enter_index
                        and message.get("name") == "desktop_read_text"
                        and message.get("ok") is True
                        and str(arguments_for(message).get("query", "")).casefold() == "wikipedia"
                        and "historia de egipto" in str(message.get("output", "")).casefold()
                        and "google" in str(message.get("output", "")).casefold()]
        result_read_index = google_reads[0][0] if google_reads else None
        observed_result = None
        result_coordinate = None
        result_target = ""
        result_window_observed = False
        for index, message in google_reads:
            args = arguments_for(message)
            target = str(args.get("target_id", ""))
            output = str(message.get("output", ""))
            if target and "desktop_read_text: window" in output.casefold():
                result_window_observed = True
            for line in output.splitlines():
                line_text = line.casefold()
                if not re.search(r"historia de egipto\s*[-–—]\s*wikipedia", line_text):
                    continue
                coordinate = re.search(r"\((0?\.\d+),\s*(0?\.\d+)\)\s*(.*)", line)
                if target and coordinate:
                    observed_result = index
                    result_target = target
                    result_coordinate = (float(coordinate.group(1)),
                                         float(coordinate.group(2)))
                    break
            if observed_result is not None:
                break
        click_match = None
        if observed_result is not None and result_coordinate is not None:
            for index, message in tool_events:
                if index <= observed_result or message.get("name") != "desktop_click" \
                        or message.get("ok") is not True:
                    continue
                args = arguments_for(message)
                try:
                    click_point = (float(args.get("x")), float(args.get("y")))
                except (TypeError, ValueError):
                    continue
                click_scope = str(args.get("scope_kind", "")).casefold()
                if (str(args.get("target_id", "")) == result_target
                        and click_scope in {"", "window"}
                        and all(0.0 <= value <= 1.0 for value in click_point)
                        and all(abs(actual - seen) <= 0.001
                                for actual, seen in zip(click_point, result_coordinate))):
                    click_match = (index, result_target)
                    break
        page_reads = []
        page_read_events = []
        page_title = ""
        page_fact = ""
        if click_match:
            click_index, target = click_match
            for index, message in tool_events:
                if index <= click_index or message.get("name") != "desktop_read_text" \
                        or message.get("ok") is not True:
                    continue
                args = arguments_for(message)
                output = str(message.get("output", ""))
                if (str(args.get("target_id", "")) == target
                        and str(args.get("query", "")).casefold() == "historia de egipto"
                        and "historia de egipto" in output.casefold()
                        and "wikipedia" in output.casefold()):
                    title_match = re.search(r"Título de ventana:\s*([^\r\n]+)", output,
                                            re.IGNORECASE)
                    title = title_match.group(1) if title_match else ""
                    title_casefold = title.casefold()
                    if ("historia de egipto" in title_casefold and "wikipedia" in title_casefold
                            and not any(term in title_casefold for term in
                                        ("search", "búsqueda", "busqueda", "new tab", "nueva pestaña"))):
                        page_reads.append(output)
                        page_read_events.append((index, message))
                        page_title = title

        def normalized(text: str) -> str:
            return (text.casefold().replace("á", "a").replace("é", "e")
                    .replace("í", "i").replace("ó", "o").replace("ú", "u"))

        generic_terms = {
            "acerca", "about", "article", "articulo", "before", "cerca", "como",
            "con", "desde", "despues", "dice", "donde", "egypt", "egipto", "el", "ella",
            "ellos", "esta", "este", "fue", "historia", "history", "hacia", "indica",
            "into", "island", "it", "la", "las", "lectura", "los", "mas", "muestra",
            "pagina", "page", "para", "por", "puede", "que", "segun", "seccion", "sobre",
            "the", "their", "this", "una", "uno", "was", "with", "wikipedia", "years", "anos",
        }

        def fact_terms(text: str) -> set[str]:
            return {term for term in re.findall(r"[a-z0-9]+", normalized(text))
                    if len(term) >= 4 and term not in generic_terms}

        article_evidence = "\n".join(page_reads)
        article_terms = fact_terms(article_evidence)
        matching_answers = []
        for answer_message in (message for message in delta
                               if isinstance(message, dict) and message.get("role") == "assistant"):
            answer = str(answer_message.get("content", ""))
            answer_normalized = normalized(answer)
            answer_time = answer_message.get("completedAt", answer_message.get("createdAt"))
            answer_terms = fact_terms(answer)
            shared_terms = sorted(answer_terms & article_terms)
            shared_numbers = sorted(set(re.findall(r"\b\d{3,4}\b", answer_normalized))
                                    & set(re.findall(r"\b\d{3,4}\b", normalized(article_evidence))))
            grounded_in_visible_text = (len(shared_terms) >= 2
                                        or bool(shared_numbers and shared_terms))
            answered_after_read = any(
                (page_event.get("completedAt", page_event.get("createdAt")) is not None
                 and answer_time is not None
                 and int(page_event.get("completedAt", page_event.get("createdAt")))
                 < int(answer_time))
                or (page_event.get("completedAt", page_event.get("createdAt")) is None
                    and answer_time is None and page_index < next(
                        i for i, message in enumerate(delta) if message is answer_message))
                for page_index, page_event in page_read_events)
            if ("egipto" in answer_normalized and "wikipedia" in answer_normalized
                    and grounded_in_visible_text and answered_after_read):
                matching_answers.append(answer)
                if not page_fact:
                    page_fact = " / ".join(list(dict.fromkeys(
                        shared_numbers + shared_terms))[:4])
        passed = bool(typed_indices and enter_index is not None and query_reads
                      and result_read_index is not None and observed_result is not None
                      and result_window_observed and click_match and page_reads
                      and page_fact and matching_answers)
        return {"passed": passed,
                "google_search_url_typed": bool(typed_indices),
                "query_bar_read_before_enter": bool(query_reads),
                "google_results_read": result_read_index is not None,
                "result_title_and_ocr_coordinate_observed": observed_result is not None,
                "result_was_observed_in_target_window": result_window_observed,
                "result_click_observed": click_match is not None,
                "opened_page_read_count": len(page_reads),
                "opened_page_title": page_title,
                "visible_fact_term": page_fact,
                "matching_answer_count": len(matching_answers)}
    if case_id == "CU07":
        events = []
        for index, message in enumerate(delta):
            if not isinstance(message, dict) or message.get("role") != "toolcall":
                continue
            try:
                arguments = json.loads(message.get("arguments", "{}"))
                if not isinstance(arguments, dict):
                    arguments = {}
            except (TypeError, json.JSONDecodeError):
                arguments = {}
            events.append((index, message.get("name"), arguments,
                           message.get("ok") is True, str(message.get("output", ""))))

        ctrl_f = next((event for event in events
                       if event[1] == "desktop_key" and event[3]
                       and str(event[2].get("key", "")).upper() == "F"
                       and "CTRL" in {str(x).upper() for x in event[2].get("modifiers", [])}), None)
        panel_read = next((event for event in events
                           if ctrl_f and event[0] > ctrl_f[0] and event[1] == "desktop_read_text"
                           and event[3]
                           and any(label in event[4].casefold() for label in
                                   ("buscar en la página", "find on page", "find in page"))), None)
        typed = next((event for event in events
                      if panel_read and event[0] > panel_read[0] and event[1] == "desktop_type"
                      and event[3]
                      and str(event[2].get("text", "")).casefold() == "july 20, 1969"
                      and str(event[2].get("target_id", ""))
                      == str(panel_read[2].get("target_id", ""))), None)
        typed_read = next((event for event in events
                           if typed and event[0] > typed[0] and event[1] == "desktop_read_text"
                           and event[3]
                           and str(event[2].get("target_id", ""))
                           == str(typed[2].get("target_id", ""))
                           and str(event[2].get("query", "")).casefold() == "july 20, 1969"
                           and "july 20, 1969" in event[4].casefold()), None)
        enter = next((event for event in events
                      if typed_read and event[0] > typed_read[0] and event[1] == "desktop_key"
                      and event[3] and str(event[2].get("key", "")).upper() == "ENTER"
                      and str(event[2].get("target_id", ""))
                      == str(typed[2].get("target_id", ""))), None)
        def has_ocr_match(output: str) -> bool:
            marker = re.search(r"(?im)^OCR\s*[—–-]\s*coordenadas[^\r\n]*:\s*",
                               output)
            if not marker:
                return False
            ocr = output[marker.end():]
            if re.search(r"\b0\s+rengl[oó]n(?:es)?\b", ocr, re.IGNORECASE):
                return False
            return "july 20, 1969" in ocr.casefold()

        result_read = next((event for event in events
                            if enter and event[0] > enter[0] and event[1] == "desktop_read_text"
                            and event[3]
                            and str(event[2].get("target_id", ""))
                            == str(typed[2].get("target_id", ""))
                            and has_ocr_match(event[4])), None)
        immediate_visible_match = bool(typed_read and has_ocr_match(typed_read[4]))
        if result_read is None and immediate_visible_match:
            result_read = typed_read
        answers = [str(message.get("content", "")) for message in delta
                   if isinstance(message, dict) and message.get("role") == "assistant"]
        def answers_date_and_article(answer: str) -> bool:
            normalized = answer.casefold()
            localized_date = ("july 20, 1969" in normalized
                              or re.search(r"\b20\s+de\s+julio\s+de\s+1969\b",
                                           normalized) is not None)
            return "apollo 11" in normalized and localized_date

        matching_answers = [answer for answer in answers
                            if answers_date_and_article(answer)]
        return {"passed": bool(ctrl_f and panel_read and typed and typed_read
                                and result_read and (enter or immediate_visible_match)
                                and matching_answers),
                "ctrl_f_observed": ctrl_f is not None,
                "find_panel_observed_before_typing": panel_read is not None,
                "exact_find_query_observed": typed is not None,
                "query_read_before_enter": typed_read is not None,
                "article_ocr_match_visible": result_read is not None,
                "immediate_visible_match_accepted": immediate_visible_match,
                "matching_answer_count": len(matching_answers)}
    if case_id == "CU08":
        search_indices = {}
        enter_indices = []
        new_tab_index = None
        switch_index = None
        read_events = [(index, str(message.get("output", "" )).casefold())
                       for index, message in enumerate(delta)
                       if isinstance(message, dict) and message.get("role") == "toolcall"
                       and message.get("name") == "desktop_read_text"]
        for index, message in enumerate(delta):
            if not isinstance(message, dict) or message.get("role") != "toolcall":
                continue
            try:
                arguments = json.loads(message.get("arguments", "{}"))
            except (TypeError, json.JSONDecodeError):
                arguments = {}
            if message.get("name") == "desktop_type":
                text = str(arguments.get("text", "")).casefold()
                if text == "apollo 11 landing date":
                    search_indices.setdefault("Apollo 11", []).append(index)
                if text == "apollo 12 landing date":
                    search_indices.setdefault("Apollo 12", []).append(index)
            elif message.get("name") == "desktop_key":
                key = str(arguments.get("key", "")).upper()
                modifiers = {str(modifier).upper() for modifier in arguments.get("modifiers", [])}
                if key == "ENTER":
                    enter_indices.append(index)
                if key == "T" and "CTRL" in modifiers:
                    new_tab_index = index
                if key == "TAB" and {"CTRL", "SHIFT"}.issubset(modifiers):
                    switch_index = index
        first_type = search_indices.get("Apollo 11", [])
        second_type = search_indices.get("Apollo 12", [])
        first_enter = next((i for i in enter_indices if first_type and i > first_type[0]), None)
        second_enter = next((i for i in enter_indices if second_type and i > second_type[0]), None)
        first_visible = bool(first_enter is not None and new_tab_index is not None
                             and any(first_enter < i < new_tab_index and "apollo 11" in text
                                     for i, text in read_events))
        second_visible = bool(second_enter is not None
                              and any(second_enter < i
                                      and (switch_index is None or i < switch_index)
                                      and "apollo 12" in text
                                      for i, text in read_events))
        returned_to_first = bool(switch_index is not None
                                 and any(i > switch_index and "apollo 11" in text
                                         for i, text in read_events))
        passed = (len(first_type) == 1 and len(second_type) == 1
                  and new_tab_index is not None and first_enter is not None
                  and second_type[0] > new_tab_index and second_enter is not None
                  and switch_index is not None and second_visible
                  and first_visible and returned_to_first)
        return {"passed": passed,
                "apollo_11_visible_before_new_tab": first_visible,
                "ctrl_t_new_tab_observed": new_tab_index is not None,
                "apollo_12_visible_in_second_tab": second_visible,
                "ctrl_shift_tab_observed": switch_index is not None,
                "apollo_11_visible_after_return": returned_to_first}
    if case_id == "CU17":
        filename = "CU20-select-this-file.txt"
        events = [(index, message) for index, message in enumerate(delta)
                  if isinstance(message, dict) and message.get("role") == "toolcall"]

        def arguments_for(message: dict) -> dict:
            try:
                value = json.loads(message.get("arguments", "{}"))
                return value if isinstance(value, dict) else {}
            except (TypeError, json.JSONDecodeError):
                return {}

        launch_calls = [(index, message, arguments_for(message))
                        for index, message in events if message.get("name") == "desktop_launch"]
        expected_path = (str(expected_workspace).replace("/", "\\").rstrip("\\").casefold()
                         if expected_workspace is not None else "")
        launch_ok = False
        target_id = ""
        if len(launch_calls) == 1:
            launch_index, launch, launch_args = launch_calls[0]
            launch_target = str(launch_args.get("args", "")).strip().strip('"').replace("/", "\\")
            id_match = re.search(r"\bid=([0-9a-f]+)\b", str(launch.get("output", "")),
                                 re.IGNORECASE)
            target_id = id_match.group(1) if id_match else ""
            launch_ok = (launch.get("ok") is True
                         and str(launch_args.get("app", "")).casefold() == "explorer"
                         and bool(expected_path)
                         and launch_target.rstrip("\\").casefold() == expected_path
                         and bool(target_id))
        else:
            launch_index = -1

        reads_by_index = [(index, message, str(message.get("output", "")))
                          for index, message in events
                          if message.get("name") == "desktop_read_text"]
        initial_folder_read = next((output for index, message, output in reads_by_index
                                    if index > launch_index and index < next(
                                        (i for i, event in events
                                         if event.get("name") == "desktop_controls"), 10**9)), "")
        folder_confirmed = bool(expected_path and expected_path in
                                initial_folder_read.replace("/", "\\").casefold())

        exact_control_queries = []
        for index, message in events:
            if message.get("name") != "desktop_controls":
                continue
            args = arguments_for(message)
            if (str(args.get("query", "")).casefold() == filename.casefold()
                    and str(args.get("target_id", "")) == target_id):
                output = str(message.get("output", ""))
                snapshot_match = re.search(r"\bsnapshot_id=([^\s]+)", output)
                control_line = next((line for line in output.splitlines()
                                     if re.search(r'"' + re.escape(filename) + r'"\s*$', line)), "")
                control_match = re.search(r"^controlId=([^\s]+)", control_line)
                if snapshot_match and control_match:
                    exact_control_queries.append((index, message, snapshot_match.group(1),
                                                  control_match.group(1)))

        selection_calls = [(index, message, arguments_for(message))
                           for index, message in events
                           if message.get("name") == "desktop_control_action"]
        semantic_selection = False
        selection_index = -1
        if len(selection_calls) == 1 and len(exact_control_queries) == 1:
            selection_index, selection, selection_args = selection_calls[0]
            query_index, query_message, snapshot_id, control_id = exact_control_queries[0]
            trace_match = re.search(r"\btrace=(\{.*\})", str(selection.get("output", "")))
            trace = {}
            if trace_match:
                try:
                    trace = json.loads(trace_match.group(1))
                except json.JSONDecodeError:
                    trace = {}
            trace_target = trace.get("target", {}) if isinstance(trace, dict) else {}
            semantic_selection = (
                selection.get("ok") is True
                and selection_index > query_index
                and str(selection_args.get("action", "")).casefold() == "select"
                and str(selection_args.get("target_id", "")) == target_id
                and str(selection_args.get("control_id", "")) == control_id
                and str(selection_args.get("snapshot_id", "")) == snapshot_id
                and trace.get("action") == "select"
                and str(trace_target.get("name", "")) == filename
                and str(trace_target.get("controlId", "")) == control_id)

        readback = next((output for index, message, output in reads_by_index
                         if index > selection_index
                         and str(arguments_for(message).get("target_id", "")) == target_id
                         and re.search(r"Nombre:\s*" + re.escape(filename), output,
                                       re.IGNORECASE)
                         and expected_path in output.replace("/", "\\").casefold()), "")
        readback_ok = bool(readback)
        allowed_tools = {"desktop_launch", "desktop_read_text", "desktop_controls",
                         "desktop_control_action"}
        unexpected_tools = [message.get("name") for _, message in events
                            if message.get("name") not in allowed_tools]
        exact_sequence = (len(events) == 5
                          and len(reads_by_index) == 2
                          and len([1 for _, message in events
                                   if message.get("name") == "desktop_controls"]) == 1
                          and len(selection_calls) == 1
                          and not unexpected_tools)
        passed = (launch_ok and folder_confirmed and len(exact_control_queries) == 1
                  and semantic_selection and readback_ok and exact_sequence)
        return {"passed": passed,
                "launch_target_confirmed": launch_ok,
                "folder_confirmed_before_selection": folder_confirmed,
                "exact_target_control_observed": len(exact_control_queries) == 1,
                "unique_semantic_selection": semantic_selection,
                "target_readback_after_selection": readback_ok,
                "unexpected_tool_count": len(unexpected_tools),
                "tool_event_count": len(events)}
    if case_id == "CU19":
        return validate_cu19_sequence(delta, expected_workspace)
    if case_id == "CU14":
        launch_calls = []
        type_calls = []
        key_calls = []
        save_calls = []
        read_calls = []
        path_read_calls = []
        for index, message in enumerate(delta):
            if not isinstance(message, dict) or message.get("role") != "toolcall":
                continue
            name = message.get("name")
            try:
                arguments = json.loads(message.get("arguments", "{}"))
            except (TypeError, json.JSONDecodeError):
                arguments = {}
            output = str(message.get("output", ""))
            if name == "desktop_launch":
                launch_calls.append((index, message.get("ok") is True,
                                    str(arguments.get("app", "")).casefold() == "notepad",
                                    "notepad-exact-line.txt" in str(arguments.get("args", "")),
                                    "id=" in output))
            if name == "desktop_type":
                type_calls.append((index, message.get("ok") is True,
                                   str(arguments.get("text", "")) == CU14_LINE,
                                   str(arguments.get("target_id", ""))))
            if name == "desktop_key":
                key_calls.append(index)
                modifiers = {str(value).upper()
                             for value in arguments.get("modifiers", [])}
                if str(arguments.get("key", "")).upper() == "S" and "CTRL" in modifiers:
                    save_calls.append((index, message.get("ok") is True,
                                       str(arguments.get("target_id", ""))))
            if name == "desktop_read_text":
                query = str(arguments.get("query", ""))
                if query.casefold() == "notepad-exact-line.txt":
                    path_read_calls.append((index, message.get("ok") is True,
                                            str(arguments.get("target_id", ""))))
                if query == CU14_LINE or CU14_LINE in output:
                    read_calls.append((index, message.get("ok") is True,
                                       CU14_LINE in output,
                                       str(arguments.get("target_id", ""))))
        launch_ok = (len(launch_calls) == 1 and launch_calls[0][1]
                     and launch_calls[0][2] and launch_calls[0][3]
                     and launch_calls[0][4])
        calls_valid = (launch_ok and bool(path_read_calls)
                       and len(type_calls) == 1 and len(save_calls) == 1
                       and len(read_calls) == 1)
        filename_confirmations = ([call for call in path_read_calls
                                   if call[1] and call[0] < type_calls[0][0]
                                   and call[2] == type_calls[0][3]]
                                  if type_calls else [])
        sequence_ok = (calls_valid and bool(filename_confirmations)
                       and type_calls[0][3] == read_calls[0][3]
                       and type_calls[0][1] and type_calls[0][2]
                       and len(key_calls) == 1 and save_calls[0][1]
                       and read_calls[0][1] and read_calls[0][2]
                       and launch_calls[0][0] < filename_confirmations[-1][0] < type_calls[0][0] < save_calls[0][0]
                       < read_calls[0][0])
        return {"passed": bool(sequence_ok), "notepad_launch_once": launch_ok,
                "filename_confirmed_before_write": bool(filename_confirmations),
                "exact_write_once": len(type_calls) == 1 and type_calls[0][2],
                "saved_with_ctrl_s": len(save_calls) == 1 and save_calls[0][1],
                "exact_readback_after_save": len(read_calls) == 1 and read_calls[0][2]}
    if case_id == "CU18":
        return validate_cu18_sequence(delta, expected_workspace)
    return None


def validate_cu13_open_turn(delta: list, workspace: pathlib.Path) -> dict:
    events = []
    for index, message in enumerate(delta):
        if not isinstance(message, dict) or message.get("role") != "toolcall":
            continue
        try:
            arguments = json.loads(message.get("arguments", "{}"))
        except (TypeError, json.JSONDecodeError):
            arguments = {}
        events.append((index, message.get("name"), arguments,
                       message.get("ok") is True, str(message.get("output", ""))))
    launches = [event for event in events if event[1] == "desktop_launch"]
    title_reads = [event for event in events if event[1] == "desktop_read_text"
                   and str(event[2].get("query", "")).casefold() == "cu20-computer-usage.xlsx"]
    sheet_reads = [event for event in events if event[1] == "desktop_read_text"
                   and not event[2].get("query")]
    unexpected_actions = [event for event in events
                          if event[1] not in {"desktop_launch", "desktop_read_text",
                                              "desktop_controls"}]
    user_turn_count = sum(1 for message in delta
                          if isinstance(message, dict) and message.get("role") == "user")
    expected_args = f'/x "{workspace / "cu20-computer-usage.xlsx"}"'
    first_title = next((event for event in title_reads
                        if launches and launches[0][0] < event[0]), None)
    first_sheet = next((event for event in sheet_reads
                        if first_title and event[0] > first_title[0]), None)
    passed = bool(
        user_turn_count == 1
        and len(launches) == 1 and first_title and first_sheet
        and not unexpected_actions
        and all(event[3] for event in events)
        and launches[0][0] < first_title[0] < first_sheet[0]
        and "se abrió" in launches[0][4].casefold()
        and str(launches[0][2].get("app", "")).casefold() == str(EXCEL_EXE).casefold()
        and str(launches[0][2].get("args", "")).casefold() == expected_args.casefold()
        and bool(first_title[2].get("target_id"))
        and bool(first_sheet[2].get("target_id"))
        and cu13_target_continues(first_title, first_sheet))
    return {"passed": passed, "launch_count": len(launches),
            "title_read_count": len(title_reads), "sheet_read_count": len(sheet_reads),
            "observation_count": sum(1 for event in events
                                     if event[1] == "desktop_controls"),
            "unexpected_action_count": len(unexpected_actions)}


def validate_artifact(case_id: str, workspace: pathlib.Path, delta: list | None = None,
                      initial_sha256: str | None = None,
                      inter_turn_excel_cleanup: dict | None = None) -> dict:
    ui_validation = validate_ui_evidence(case_id, delta or [], inter_turn_excel_cleanup,
                                         expected_workspace=workspace)
    if case_id == "CU17" and ui_validation is not None:
        path = workspace / "CU20-select-this-file.txt"
        fixture_unchanged = (path.is_file()
                             and path.read_text(encoding="utf-8") == "Synthetic selection target.\n")
        return {**ui_validation,
                "passed": bool(ui_validation.get("passed") and fixture_unchanged),
                "fixture_unchanged": fixture_unchanged}
    if ui_validation is not None and case_id not in {"CU13", "CU14", "CU18", "CU19"}:
        return ui_validation
    if case_id in {"CU09", "CU10", "CU11", "CU12", "CU13", "CU18"}:
        from openpyxl import load_workbook

        path = (workspace / "clipboard-paste.xlsx" if case_id == "CU18"
                else workspace / "cu20-computer-usage.xlsx")
        if not path.is_file():
            return {"passed": False, "reason": f"No existe {path.name}"}
        wb = load_workbook(path, data_only=False)
        ws = wb.active
        if case_id == "CU09":
            expected = [["Producto", "Cantidad", "Precio"], ["Café", 2, 1250],
                        ["Té", 3, 800], ["Agua", 1, 500]]
            actual = [[ws.cell(r, c).value for c in range(1, 4)] for r in range(1, 5)]
            nonempty = sum(1 for row in ws.iter_rows() for cell in row if cell.value is not None)
            exact_shape = ws.max_row == 4 and ws.max_column == 3 and nonempty == 12
            ok = actual == expected and exact_shape
            return {"passed": ok, "actual_A1_C4": actual,
                    "dimensions": [ws.max_row, ws.max_column],
                    "nonempty_cells": nonempty}
        if case_id in {"CU10", "CU11", "CU12", "CU13"}:
            expected_b2 = 2 if case_id == "CU10" else 4
            formula = ws["D2"].value
            cached_wb = load_workbook(path, data_only=True)
            cached_total = cached_wb.active["D2"].value
            cached_wb.close()
            expected_formula = (isinstance(formula, str)
                                and formula.replace(" ", "").upper()
                                in {"=SUM(B2:B4)", "=SUMA(B2:B4)", "=B2+B3+B4"})
            expected_rows = [["Producto", "Cantidad", "Precio"],
                             ["Café", expected_b2, 1250], ["Té", 3, 800], ["Agua", 1, 500]]
            actual_rows = [[ws.cell(row, col).value for col in range(1, 4)]
                           for row in range(1, 5)]
            values_ok = actual_rows == expected_rows
            label_ok = ws["D1"].value == "Total cantidades"
            expected_total = 6 if case_id == "CU10" else 8
            total_ok = cached_total == expected_total
            header_ok = (case_id not in {"CU12", "CU13"}
                         or all(ws.cell(1, col).font.bold for col in range(1, 5)))
            formats = [ws.cell(row, 3).number_format for row in range(2, 5)]
            format_ok = (case_id not in {"CU12", "CU13"}
                         or all("$" in fmt or "[$" in fmt or "€" in fmt for fmt in formats))
            artifact_ok = values_ok and label_ok and expected_formula and total_ok and header_ok and format_ok
            evidence = {"A1_C4": actual_rows, "B2": ws["B2"].value,
                        "D1": ws["D1"].value, "D2_formula": formula,
                        "D2_cached_value": cached_total,
                        "header_bold": [ws.cell(1, col).font.bold for col in range(1, 5)],
                        "price_number_formats": formats}
            wb.close()
            if case_id == "CU13":
                current_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
                unchanged = initial_sha256 is not None and current_sha256 == initial_sha256
                evidence["workbook_unchanged_during_read_only_test"] = unchanged
                evidence["workbook_sha256_after_agent"] = current_sha256
                evidence["ui_reopen_evidence"] = ui_validation or {"passed": False}
                return {"passed": artifact_ok and unchanged
                        and evidence["ui_reopen_evidence"].get("passed") is True,
                        **evidence}
            return {"passed": artifact_ok, **evidence}
        if case_id == "CU18":
            cell = ws["A1"].value
            nonempty = sum(1 for row in ws.iter_rows() for item in row if item.value is not None)
            source_path = workspace / "clipboard-source.txt"
            source_exact = (source_path.is_file()
                            and source_path.read_text(encoding="utf-8") == CLIPBOARD_MARKER)
            evidence = dict(ui_validation or {})
            evidence["source_file_exact"] = source_exact
            ui_passed = bool(evidence.get("passed")) and source_exact
            return {"passed": (ui_passed and isinstance(cell, str)
                               and cell == CLIPBOARD_MARKER and nonempty == 1),
                    "A1": cell, "nonempty_cells": nonempty,
                    "clipboard_ui_evidence": evidence}
    if case_id == "CU14":
        path = workspace / "notepad-exact-line.txt"
        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        expected = CU14_LINE
        evidence = ui_validation or {"passed": False}
        return {"passed": actual == expected and evidence.get("passed") is True,
                "text": actual, "computer_use_evidence": evidence}
    if case_id == "CU15":
        path = workspace / "notepad-replace.txt"
        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        expected = "The quick brown fox jumps over the curious dog.\n"
        return {"passed": actual == expected, "text": actual}
    if case_id == "CU16":
        from PIL import Image

        path = workspace / "paint-rectangle.png"
        if not path.is_file():
            return {"passed": False, "reason": "No existe el PNG"}
        with Image.open(path) as im:
            rgb = im.convert("RGB")
            pixels = rgb.load()
            dark = [(x, y) for y in range(im.height) for x in range(im.width)
                    if min(pixels[x, y]) < 245]
            nonwhite = len(dark)
            if not dark:
                return {"passed": False, "format": im.format, "size": [im.width, im.height],
                        "nonwhite_pixels": 0, "rectangular_outline": False}
            left = min(x for x, _ in dark)
            right = max(x for x, _ in dark)
            top = min(y for _, y in dark)
            bottom = max(y for _, y in dark)
            width = right - left + 1
            height = bottom - top + 1
            band = max(2, round(min(width, height) * 0.025))

            def row_coverage(y0: int, y1: int) -> float:
                return sum(any(min(pixels[x, y]) < 245 for y in range(y0, y1))
                           for x in range(left, right + 1)) / width

            def column_coverage(x0: int, x1: int) -> float:
                return sum(any(min(pixels[x, y]) < 245 for x in range(x0, x1))
                           for y in range(top, bottom + 1)) / height

            sides = {
                "top": row_coverage(top, min(bottom + 1, top + band)),
                "bottom": row_coverage(max(top, bottom - band + 1), bottom + 1),
                "left": column_coverage(left, min(right + 1, left + band)),
                "right": column_coverage(max(left, right - band + 1), right + 1),
            }
            outline = (width >= 20 and height >= 20
                       and min(sides.values()) >= 0.65)
            return {"passed": im.format == "PNG" and im.width >= 100 and im.height >= 100
                    and nonwhite >= 100 and outline, "format": im.format,
                    "size": [im.width, im.height], "nonwhite_pixels": nonwhite,
                    "rectangular_outline": outline, "side_coverage": sides}
    if case_id in {"CU19", "CU20"}:
        if case_id == "CU19":
            first, second = cu19_document_paths(workspace)
            a = first.read_text(encoding="utf-8") if first.is_file() else None
            b = second.read_text(encoding="utf-8") if second.is_file() else None
            evidence = ui_validation or {"passed": False}
            return {"passed": a == "" and b == "contenido beta solicitado"
                    and evidence.get("passed") is True,
                    "alpha": a, "beta": b, "computer_use_evidence": evidence}
        path = workspace / "notepad-no-duplicate.txt"
        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        phrase = "CU20-FRASE-UNICA-9F2B"
        return {"passed": actual is not None and actual.count(phrase) == 1
                and actual.strip() == phrase, "text": actual,
                "phrase_count": actual.count(phrase) if actual is not None else None}
    return {"passed": None, "reason": "requiere revisión de evidencia UI"}


def seed_xlsx_formula_cache(path: pathlib.Path, cell_ref: str, value: str) -> None:
    """Patch a cached formula result into an openpyxl-created OOXML workbook."""
    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    temporary_path = path.with_name(path.stem + ".cached.xlsx")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
            temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as destination:
        found = False
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                root = ET.fromstring(data)
                cell = root.find(f".//{{{namespace}}}c[@r='{cell_ref}']")
                if cell is None or cell.find(f"{{{namespace}}}f") is None:
                    raise RuntimeError(f"La celda {cell_ref} no contiene una fórmula en {path.name}")
                cached_value = cell.find(f"{{{namespace}}}v")
                if cached_value is None:
                    cached_value = ET.SubElement(cell, f"{{{namespace}}}v")
                cached_value.text = value
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                found = True
            destination.writestr(item, data)
        if not found:
            raise RuntimeError(f"No se encontró sheet1.xml en {path.name}")
    os.replace(temporary_path, path)


def prepare_case_fixture(case_id: str, workspace: pathlib.Path) -> dict:
    if case_id == "CU16":
        from PIL import Image

        path = workspace / "paint-rectangle.png"
        if path.exists():
            raise RuntimeError("CU16 requiere workspace nuevo; el PNG ya existe")
        Image.new("RGB", (400, 300), "white").save(path, format="PNG")
        return {"kind": "blank_png", "case_id": case_id, "path": str(path),
                "size": [400, 300],
                "sha256_before_agent": hashlib.sha256(path.read_bytes()).hexdigest()}
    if case_id in {"CU10", "CU11", "CU12", "CU13"}:
        from openpyxl import Workbook
        from openpyxl.styles import Font

        path = workspace / "cu20-computer-usage.xlsx"
        if path.exists():
            raise RuntimeError(f"{case_id} requiere workspace nuevo; el libro ya existe")
        workbook = Workbook()
        sheet = workbook.active
        initial_b2 = 2 if case_id in {"CU10", "CU11"} else 4
        rows = [["Producto", "Cantidad", "Precio"],
                ["Café", initial_b2, 1250], ["Té", 3, 800], ["Agua", 1, 500]]
        for row_index, row in enumerate(rows, start=1):
            for column_index, value in enumerate(row, start=1):
                sheet.cell(row_index, column_index, value)
        if case_id in {"CU11", "CU12", "CU13"}:
            sheet["D1"] = "Total cantidades"
            sheet["D2"] = "=B2+B3+B4"
        if case_id == "CU13":
            for column in range(1, 5):
                sheet.cell(1, column).font = Font(bold=True)
            for row in range(2, 5):
                sheet.cell(row, 3).number_format = '"$"#,##0.00'
        workbook.calculation.calcMode = "auto"
        workbook.calculation.fullCalcOnLoad = case_id != "CU13"
        workbook.calculation.forceFullCalc = case_id != "CU13"
        workbook.save(path)
        workbook.close()
        if case_id == "CU13":
            seed_xlsx_formula_cache(path, "D2", "8")
        return {"kind": "seeded_xlsx", "case_id": case_id, "path": str(path),
                "initial_state": {"B2": initial_b2,
                                  "D1": "Total cantidades" if case_id != "CU10" else None,
                                  "D2_formula": "=B2+B3+B4" if case_id != "CU10" else None,
                                  "headers_bold": case_id == "CU13",
                                  "prices_currency": case_id == "CU13"},
                "sha256_before_agent": hashlib.sha256(path.read_bytes()).hexdigest()}
    filenames = {"CU09": "cu20-computer-usage.xlsx",
                 "CU18": "clipboard-paste.xlsx"}
    filename = filenames.get(case_id)
    if filename is None:
        return {}
    from openpyxl import Workbook, load_workbook

    path = workspace / filename
    if path.exists():
        existing = load_workbook(path, data_only=False)
        has_values = any(cell.value is not None
                         for sheet in existing.worksheets
                         for row in sheet.iter_rows() for cell in row)
        existing.close()
        if has_values:
            raise RuntimeError(f"{case_id} requiere workspace nuevo; el libro ya contiene datos")
    else:
        workbook = Workbook()
        workbook.save(path)
        workbook.close()
    return {"kind": "empty_xlsx", "case_id": case_id, "path": str(path),
            "sha256_before_agent": hashlib.sha256(path.read_bytes()).hexdigest()}


def case_excel_path(case_id: str, workspace: pathlib.Path) -> pathlib.Path | None:
    filenames = {
        "CU09": "cu20-computer-usage.xlsx", "CU10": "cu20-computer-usage.xlsx",
        "CU11": "cu20-computer-usage.xlsx", "CU12": "cu20-computer-usage.xlsx",
        "CU13": "cu20-computer-usage.xlsx", "CU18": "clipboard-paste.xlsx",
    }
    filename = filenames.get(case_id)
    return workspace / filename if filename else None


def is_test_excel_process(process_name: str, command_line: str,
                          workbook_path: pathlib.Path) -> bool:
    normalized_command = os.path.normcase(os.path.normpath(command_line))
    normalized_workbook = os.path.normcase(os.path.normpath(str(workbook_path)))
    return (process_name.casefold() == "excel.exe"
            and re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(normalized_workbook)
                          + r"(?![A-Za-z0-9_.-])", normalized_command) is not None)


def _test_excel_windows(pids: set[int], workbook_name: str, close: bool = False) -> list[tuple[int, int]]:
    """Find visible top-level windows titled for this workbook; optionally post WM_CLOSE."""
    if not pids or os.name != "nt":
        return []

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    enum_windows = user32.EnumWindows
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    enum_windows.argtypes = [callback_type, wintypes.LPARAM]
    enum_windows.restype = wintypes.BOOL
    get_window_thread_process_id = user32.GetWindowThreadProcessId
    get_window_thread_process_id.argtypes = [wintypes.HWND,
                                              ctypes.POINTER(wintypes.DWORD)]
    get_window_thread_process_id.restype = wintypes.DWORD
    get_window = user32.GetWindow
    get_window.argtypes = [wintypes.HWND, wintypes.UINT]
    get_window.restype = wintypes.HWND
    is_window_visible = user32.IsWindowVisible
    is_window_visible.argtypes = [wintypes.HWND]
    is_window_visible.restype = wintypes.BOOL
    get_window_text = user32.GetWindowTextW
    get_window_text.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    get_window_text.restype = ctypes.c_int
    post_message = user32.PostMessageW
    post_message.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                              wintypes.LPARAM]
    post_message.restype = wintypes.BOOL

    matches: list[tuple[int, int]] = []
    expected_title = workbook_name.casefold()

    @callback_type
    def collect(hwnd, _):
        pid = wintypes.DWORD()
        get_window_thread_process_id(hwnd, ctypes.byref(pid))
        # Ignore owned modal prompts; never click or dismiss them automatically.
        if (pid.value in pids and is_window_visible(hwnd)
                and not get_window(hwnd, 4)):  # GW_OWNER
            title = ctypes.create_unicode_buffer(512)
            get_window_text(hwnd, title, len(title))
            if expected_title in title.value.casefold():
                matches.append((int(pid.value), int(hwnd)))
                if close:
                    post_message(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        return True

    enum_windows(collect, 0)
    return matches


def visible_test_excel_window_pids(pids: set[int], workbook_name: str) -> set[int]:
    """Return matching PIDs only while the exact workbook window is visible."""
    return {pid for pid, _ in _test_excel_windows(pids, workbook_name)}


def request_close_test_excel_windows(pids: set[int], workbook_name: str) -> list[int]:
    """Ask only matching workbook windows to close; never dismiss prompts or kill."""
    return [hwnd for _, hwnd in _test_excel_windows(pids, workbook_name, close=True)]


def close_test_excel_processes(case_id: str, workspace: pathlib.Path) -> dict:
    workbook_path = case_excel_path(case_id, workspace)
    if workbook_path is None:
        return {"matched_pids": [], "closed_pids": [], "remaining_pids": []}
    import psutil

    matched = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = str(process.info.get("name") or "")
            command_line = " ".join(process.info.get("cmdline") or [])
            if is_test_excel_process(name, command_line, workbook_path):
                matched.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    matched_pids = {process.pid for process in matched}
    requested_windows = request_close_test_excel_windows(matched_pids, workbook_path.name)
    gone, alive = psutil.wait_procs(matched, timeout=8)
    remaining_workbook_pids = visible_test_excel_window_pids(matched_pids, workbook_path.name)
    return {"workbook_path": str(workbook_path), "matched_pids": sorted(matched_pids),
            "close_requested_windows": requested_windows,
            "closed_pids": [process.pid for process in gone],
            "remaining_pids": sorted(remaining_workbook_pids),
            "processes_alive_after_close": [process.pid for process in alive
                                             if process.is_running()]}


def setting_snapshot(names: list[str]) -> dict:
    values = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY, 0, winreg.KEY_READ) as key:
            for name in names:
                try:
                    value, kind = winreg.QueryValueEx(key, name)
                    values[name] = {"exists": True, "value": value, "kind": kind}
                except FileNotFoundError:
                    values[name] = {"exists": False}
    except FileNotFoundError:
        for name in names:
            values[name] = {"exists": False}
    return values


def restore_settings(snapshot: dict) -> None:
    if not snapshot:
        return
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, SETTINGS_KEY, 0, winreg.KEY_SET_VALUE) as key:
        for name, item in snapshot.items():
            if item["exists"]:
                winreg.SetValueEx(key, name, 0, item["kind"], item["value"])
            else:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass


def desktop_images(value: object, run_dir: pathlib.Path, case_id: str) -> list[dict]:
    # Sólo se conserva evidencia del lienzo sintético de Paint. Capturas de
    # Excel, navegador u otras apps pueden incluir listas o ventanas del usuario.
    if case_id != "CU16":
        return []
    messages = value if isinstance(value, list) else []
    launched_ids = set()
    for message in messages:
        if not isinstance(message, dict) or message.get("name") != "desktop_launch":
            continue
        launched_ids.update(re.findall(r"\bid=([0-9a-fA-F]+)", str(message.get("output", ""))))
    candidates = set()
    for message in messages:
        if not isinstance(message, dict) or message.get("name") not in {"desktop_snapshot", "desktop_observe"}:
            continue
        try:
            arguments = json.loads(message.get("arguments", "{}"))
        except (TypeError, json.JSONDecodeError):
            continue
        if str(arguments.get("target_id", "")) not in launched_ids:
            continue
        output = str(message.get("output", ""))
        candidates.update(re.findall(
            r"(?:image_path|imagePath)\s*[=:]\s*([^\s\"\\]+(?:\\[^\s\"\\]+)*)", output))
        candidates.update(re.findall(r"[A-Za-z]:\\[^\"\r\n]+?\.(?:png|jpe?g)", output, re.IGNORECASE))
    copied = []
    for index, raw in enumerate(sorted(candidates), start=1):
        source = pathlib.Path(raw.rstrip(".,;)]}"))
        try:
            if not source.is_file() or source.stat().st_size > 25_000_000:
                continue
            target = run_dir / "images" / f"{case_id}-{index}{source.suffix.lower()}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append({"source": str(source), "copy": str(target),
                           "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        except OSError:
            continue
    return copied


def sanitize_desktop_observations(delta: list) -> list:
    sanitized = json.loads(json.dumps(delta, ensure_ascii=False))
    for message in sanitized:
        if (not isinstance(message, dict) or message.get("role") != "toolcall"
                or not str(message.get("name", "")).startswith("desktop_")):
            continue
        name = str(message.get("name", ""))
        output = str(message.get("output", ""))
        if name == "desktop_windows":
            match = re.search(r"desktop_windows:\s*(\d+)\s+ventana", output, re.IGNORECASE)
            count = int(match.group(1)) if match else None
            label = f"{count} ventanas" if count is not None else "ventanas"
            summary = (f"[desktop_windows: {label}; títulos e ids omitidos del recibo "
                       "para no retener ventanas ajenas al test]")
        elif name == "desktop_controls":
            match = re.search(r"desktop_controls:\s*(\d+)\s+control", output, re.IGNORECASE)
            count = int(match.group(1)) if match else None
            label = f"{count} controles" if count is not None else "resultado omitido"
            summary = f"[desktop_controls: {label}; nombres, ids y geometría omitidos del recibo]"
        elif name == "desktop_read_text":
            first = output.splitlines()[0] if output else "[desktop_read_text]"
            first = re.sub(r"(?:id|target_id)\s*[=:]\s*[^\s,;]+", "id=[omitido]", first)
            first = re.sub(r'"[^"]*"', '"[texto omitido]"', first)
            first = re.sub(r"'[^']*'", "'[texto omitido]'", first)
            line_count = max(0, len(output.splitlines()) - 1)
            summary = f"{first} [OCR omitido del recibo; lineas={line_count}]"
        elif name in {"desktop_snapshot", "desktop_observe", "desktop_clipboard",
                      "desktop_assert", "desktop_wait_for"}:
            first = output.splitlines()[0] if output else f"[{name}]"
            first = re.sub(r"(?:id|target_id|controlId|snapshot_id)\s*[=:]\s*[^\s,;]+",
                           "id=[omitido]", first)
            first = re.sub(r'"[^"]*"', '"[detalle omitido]"', first)
            first = re.sub(r"'[^']*'", "'[detalle omitido]'", first)
            summary = f"{first} [detalle de escritorio omitido del recibo]"
        else:
            first = output.splitlines()[0] if output else f"[{name}]"
            first = re.sub(r"(?:id|target_id|controlId|snapshot_id)\s*[=:]\s*[^\s,;]+",
                           "id=[omitido]", first)
            first = re.sub(r'"[^"]*"', '"[detalle omitido]"', first)
            first = re.sub(r"'[^']*'", "'[detalle omitido]'", first)
            summary = first
        message["output"] = summary
        try:
            args = json.loads(str(message.get("arguments", "{}")))
            if isinstance(args, dict):
                for key in ("target_id", "control_id", "snapshot_id"):
                    if key in args:
                        args[key] = "[omitido]"
                if name == "desktop_clipboard" and "text" in args:
                    args["text"] = "[omitido]"
                message["arguments"] = json.dumps(args, ensure_ascii=False)
        except (TypeError, ValueError):
            pass
        receipt = message.get("desktopReceipt")
        if isinstance(receipt, dict):
            receipt["detail"] = summary
            receipt["target"] = {}
            receipt["snapshotId"] = ""
    return sanitized


class TurnSafetyError(RuntimeError):
    def __init__(self, message: str, delta: list):
        super().__init__(message)
        self.delta = delta


class TurnTimeoutError(TimeoutError):
    def __init__(self, message: str, delta: list):
        super().__init__(message)
        self.delta = delta


def enforce_edge_user_profile_launch(delta: list, expected_shortcut: pathlib.Path) -> None:
    for message in delta:
        if not isinstance(message, dict) or message.get("role") != "toolcall":
            continue
        if message.get("name") != "desktop_launch" or "receipt_id=" not in str(message.get("output", "")):
            continue
        try:
            arguments = json.loads(message.get("arguments", "{}"))
        except (TypeError, json.JSONDecodeError):
            arguments = {}
        launched_app = str(arguments.get("app", ""))
        raw_args = str(arguments.get("args", ""))
        normalized_shortcut = os.path.normcase(os.path.normpath(str(expected_shortcut)))
        normalized_launched_app = os.path.normcase(os.path.normpath(launched_app))
        output = str(message.get("output", ""))
        # The runner-created shortcut targets Edge's existing user profile and
        # asks for a new window. Titles vary by locale/site, so the exact shortcut
        # and the backend's new-window result are the stable checks.
        if (not message.get("ok", False) or normalized_launched_app != normalized_shortcut
                or raw_args or "id=" not in output.casefold()
                or "la ventana se abrió" not in output.casefold()
                or "ya estaba abierta" in output.casefold()):
            try:
                invoke("stopAgent")
            except Exception:
                pass
            raise TurnSafetyError(
                "Abortado antes de interactuar con el navegador: desktop_launch no confirmó "
                "una ventana nueva del acceso directo Edge del perfil de usuario.", delta
            )


def enforce_no_windows_permission_prompt(delta: list) -> None:
    firewall_prompt = re.compile(
        r"(?:windows defender firewall|firewall de windows).{0,160}"
        r"(?:blocked|bloque[oó]|allow access|permitir acceso|acceder a esta aplicaci[oó]n)",
        re.IGNORECASE | re.DOTALL,
    )
    permission_prompt = re.compile(
        r"(?:do you want to allow|¿quieres permitir que).{0,160}"
        r"(?:access|acceda|acceder|location|camera|microphone|ubicaci[oó]n|c[aá]mara|micr[oó]fono)",
        re.IGNORECASE | re.DOTALL,
    )
    for message in delta:
        if (not isinstance(message, dict) or message.get("role") != "toolcall"
                or not str(message.get("name", "")).startswith("desktop_")):
            continue
        text = re.sub(r"\s+", " ", str(message.get("output", "")))
        if firewall_prompt.search(text) or permission_prompt.search(text):
            try:
                invoke("stopAgent")
            except Exception:
                pass
            raise TurnSafetyError(
                "Abortado al detectar un diálogo de permiso de Windows en la lectura de pantalla; "
                "no se ejecutarán más acciones hasta resolverlo.", delta
            )


def has_terminal_assistant(delta: list) -> bool:
    completed_messages = []
    for message in delta:
        if not isinstance(message, dict):
            continue
        timestamp = message.get("completedAt") or message.get("createdAt")
        if isinstance(timestamp, (int, float)):
            completed_messages.append((timestamp, message))
    if not completed_messages:
        return False
    latest_timestamp = max(timestamp for timestamp, _ in completed_messages)
    latest_messages = [message for timestamp, message in completed_messages
                       if timestamp == latest_timestamp]
    # agentMessages can append a completed desktop read after the final assistant
    # message even when that read's completedAt is earlier. Use event time, not
    # array order, and reject ties so a same-time tool call cannot be hidden.
    if len(latest_messages) != 1:
        return False
    latest = latest_messages[0]
    if latest.get("role") != "assistant" or bool(latest.get("typing", False)):
        return False
    # The backend exposes a pending function call as assistant text before the
    # corresponding toolcall result is appended. That message is not terminal:
    # keep waiting for the tool execution and the assistant's follow-up.
    content = str(latest.get("content", "")).lstrip()
    if content.upper().startswith("TOOL_CALL"):
        return False
    return True


def wait_turn(before_count: int, timeout_sec: int,
              edge_shortcut: pathlib.Path | None = None) -> tuple[list, float]:
    started = time.monotonic()
    deadline = started + timeout_sec
    stable_signature = None
    stable_count = 0
    last_delta = []
    while time.monotonic() < deadline:
        streaming_index = int(prop("agentStreamingIndex"))
        messages = prop("agentMessages")
        delta = messages[before_count:] if isinstance(messages, list) else []
        last_delta = delta
        if edge_shortcut is not None:
            enforce_edge_user_profile_launch(delta, edge_shortcut)
        enforce_no_windows_permission_prompt(delta)
        if streaming_index < 0:
            # Una respuesta assistant anterior no cierra un turno si después llegó
            # una tool call: hay que esperar la observación y la respuesta posterior.
            finished = has_terminal_assistant(delta)
            signature = json.dumps(delta, ensure_ascii=False, sort_keys=True) if finished else None
            if not finished:
                stable_signature = None
                stable_count = 0
                time.sleep(1)
                continue
            if signature == stable_signature:
                stable_count += 1
            else:
                stable_signature = signature
                stable_count = 1
            last_delta = delta
            if stable_count >= 3 and delta:
                return delta, time.monotonic() - started
        else:
            stable_signature = None
            stable_count = 0
        time.sleep(1)
    raise TurnTimeoutError(
        f"turno excedió {timeout_sec}s; mensajes_parciales={len(last_delta)}", last_delta)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace-id", required=True,
                        help="workspace compartido por los casos de una misma ronda")
    parser.add_argument("--case", action="append", required=True, choices=CASE_IDS)
    parser.add_argument("--turn-timeout", type=int, default=900)
    parser.add_argument("--model-timeout", type=int, default=900)
    parser.add_argument("--diagnostic-target-id")
    parser.add_argument("--diagnostic-target-pid")
    parser.add_argument("--diagnostic-target-file")
    args = parser.parse_args()
    if len(args.case) != 1:
        raise SystemExit("Ejecuta exactamente un caso por daemon para mantener turnos independientes")
    case_id = args.case[0]
    if args.diagnostic_target_id and case_id not in {
            "DIAG_READONLY", "DIAG_SAVE_CU13", "DIAG_CLOSE_TEST_EDGE",
            "DIAG_DISCARD_TEST_EXCEL", "DIAG_CLOSE_TEST_NOTEPAD"}:
        raise SystemExit("--diagnostic-target-id sólo aplica a diagnósticos con target UI exacto")
    if args.diagnostic_target_pid and case_id not in {
            "DIAG_DISCARD_TEST_EXCEL", "DIAG_CLOSE_TEST_EXCEL"}:
        raise SystemExit("--diagnostic-target-pid sólo aplica a limpieza de apps de prueba")
    if args.diagnostic_target_file and case_id not in {
            "DIAG_DISCARD_TEST_EXCEL", "DIAG_CLOSE_TEST_EXCEL", "DIAG_CLOSE_TEST_NOTEPAD"}:
        raise SystemExit("--diagnostic-target-file sólo aplica a limpieza de archivos sintéticos")
    if args.diagnostic_target_file:
        allowed_files = {"cu20-computer-usage.xlsx", "clipboard-paste.xlsx",
                         "notepad-exact-line.txt", "notepad-replace.txt",
                         "notepad-no-duplicate.txt", "clipboard-source.txt"}
        if args.diagnostic_target_file not in allowed_files:
            raise SystemExit("--diagnostic-target-file debe ser un archivo sintético conocido")

    if not APP.is_file():
        raise SystemExit(f"No existe el binario Debug: {APP}")
    run_dir = TASK / "receipts/runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    workspace = WORKSPACE_ROOT / args.workspace_id
    workspace.mkdir(parents=True, exist_ok=True)
    excel_cleanup_before = close_test_excel_processes(case_id, workspace)
    if excel_cleanup_before.get("remaining_pids"):
        blocked = {
            "run_id": args.run_id,
            "case_id": case_id,
            "workspace_id": args.workspace_id,
            "workspace": str(workspace),
            "excel_cleanup_before": excel_cleanup_before,
            "error": "Excel de una prueba anterior sigue abierto; no se preparó el libro ni se inició LlamaCode.",
        }
        save_json(run_dir / "RESULT.json", blocked)
        print(console_json_line(blocked), flush=True)
        print(f"RECEIPT={run_dir / 'RESULT.json'}", flush=True)
        return 1
    case_fixture = prepare_case_fixture(case_id, workspace)
    isolated_profiles = ISOLATED_PROFILES_ROOT / args.run_id
    env = os.environ.copy()
    env["LLAMACODE_CONTROL_PORT"] = str(PORT)
    env["LLAMACODE_PROFILES_DIR"] = str(isolated_profiles)
    models_dir = pathlib.Path(os.environ["LOCALAPPDATA"]) / "LlamaCode/LlamaCode/models"
    # ProfileManager builds deterministic model IDs from this value verbatim.
    # Keep Qt's forward-slash path form so it matches the scanner/catalog path.
    env["LLAMACODE_MODELS_DIR"] = models_dir.as_posix()
    env["LLAMACODE_TEST_MODE"] = "1"
    env["LLAMACODE_AGENT_DATA_DIR"] = str(TASK / "runtime/agent-data" / args.run_id)
    isolated_profiles.mkdir(parents=True, exist_ok=False)

    try:
        request_json(BASE + "/health", timeout=1)
        raise SystemExit(f"El puerto local {PORT} ya está ocupado; no reutilizo otro daemon")
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        pass

    settings = setting_snapshot(["lastLaunchId", "lastAgentLaunchId"])
    registry_source = pathlib.Path(os.environ["APPDATA"]) / "LlamaCode/LlamaCode/binary_registry.json"
    registry_test = pathlib.Path(os.environ["APPDATA"]) / "qttest/LlamaCode/LlamaCode/binary_registry.json"
    registry_items = json.loads(registry_source.read_text(encoding="utf-8"))
    pinned_runtime = next((item for item in registry_items
                           if item.get("versionHint") == RUNTIME_PIN), None)
    if not pinned_runtime:
        raise RuntimeError(f"El runtime oficial fijado {RUNTIME_PIN} no está en el registro instalado")
    if registry_test.exists():
        test_registry_items = json.loads(registry_test.read_text(encoding="utf-8"))
    else:
        test_registry_items = []
    if not any(item.get("id") == pinned_runtime.get("id") for item in test_registry_items):
        test_registry_items.append(pinned_runtime)
        registry_test.parent.mkdir(parents=True, exist_ok=True)
        registry_test.write_text(json.dumps(test_registry_items, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    registry_receipt = {"source": str(registry_source), "source_sha256": hashlib.sha256(
        registry_source.read_bytes()).hexdigest(), "test_registry": str(registry_test),
        "runtime_id": pinned_runtime.get("id"), "runtime_path": pinned_runtime.get("path"),
        "version_hint": pinned_runtime.get("versionHint")}
    save_json(run_dir / "pre-run-settings.json", {
        key: ({"exists": value["exists"], "value": value.get("value")}
              if value["exists"] else {"exists": False})
        for key, value in settings.items()
    })
    save_json(run_dir / "runtime-registry.json", registry_receipt)
    daemon_log = (run_dir / "llamacode-daemon.log").open("w", encoding="utf-8", buffering=1)
    daemon = subprocess.Popen([str(APP), "--agent-daemon"], cwd=ROOT, env=env,
                              stdout=daemon_log, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    result = {
        "run_id": args.run_id,
        "started_at_local": dt.datetime.now().astimezone().isoformat(),
        "launch_profile_id": MODEL_ID,
        "agent_base_profile_id": BASE_AGENT_ID,
        "daemon_pid": daemon.pid,
        "binary": str(APP),
        "binary_sha256": hashlib.sha256(APP.read_bytes()).hexdigest(),
        "isolated_profiles_dir": str(isolated_profiles),
        "workspace_id": args.workspace_id,
        "workspace": str(workspace),
        "case_fixture": case_fixture,
        "excel_cleanup_before": excel_cleanup_before,
        "cases": [],
        "daemon_log": str(run_dir / "llamacode-daemon.log"),
    }
    try:
        wait_until(lambda: request_json(BASE + "/health", timeout=2).get("ok"),
                   "ControlApi health", 120)
        wait_until(lambda: not prop("startupBusy"), "arranque headless", 120)
        methods = request_json(BASE + "/methods")
        save_json(run_dir / "control-methods.json", methods)

        catalog = invoke("agentToolCatalog").get("result", [])
        desktop_tools = sorted(item["name"] for item in catalog
                               if item.get("name", "").startswith("desktop_"))
        if len(desktop_tools) < 20:
            raise RuntimeError(f"Catálogo desktop_* incompleto: {desktop_tools!r}")
        duplicate = invoke("duplicateAgentProfile", [BASE_AGENT_ID], "profileManager")
        profile_id = duplicate.get("result", "")
        if not profile_id:
            raise RuntimeError(f"No pude duplicar {BASE_AGENT_ID}: {duplicate!r}")
        case_tools = tools_for_case(case_id, desktop_tools)
        update = invoke("updateAgentProfile", [{
            "id": profile_id,
            "name": f"CU20 headless · {BASE_AGENT_ID}",
            "enabledTools": case_tools,
            "approvalMode": "super",
            "mcpEnabled": False,
        }], "profileManager")
        if update.get("result") is not True:
            raise RuntimeError(f"No pude limitar el perfil derivado: {update!r}")
        set_profile = setprop("activeAgentProfileId", profile_id)
        effective = invoke("agentProfileSpec", [profile_id], "profileManager").get("result", {})
        effective_tools = effective.get("tools", {}).get("include", [])
        if (not effective_tools or any(not str(name).startswith("desktop_") for name in effective_tools)
                or effective.get("permissions", {}).get("approvalMode") != "super"):
            raise RuntimeError(f"El perfil efectivo no quedó aislado: {effective!r}")
        result["agent_profile"] = {
            "id": profile_id, "base": BASE_AGENT_ID, "tools": effective_tools,
            "catalog_tools": desktop_tools,
            "approvalMode": effective["permissions"]["approvalMode"],
            "mcpEnabled": False, "setprop": set_profile,
        }
        agent_file = isolated_profiles / "agent_profiles.json"
        if agent_file.exists():
            result["agent_profile"]["file_sha256"] = hashlib.sha256(agent_file.read_bytes()).hexdigest()
        save_json(run_dir / "profile-effective.json", result["agent_profile"])

        selected_launch = invoke("getLaunchProfile", [MODEL_ID], "profileManager").get("result", {})
        if not selected_launch:
            raise RuntimeError(f"No pude resolver el launch profile {MODEL_ID}")
        result["launch_profile"] = selected_launch

        model_path = (models_dir / "gemma-4-12b" / "gemma-4-12b-it-UD-Q3_K_XL.gguf").as_posix()
        model_id = str(uuid.uuid5(uuid.UUID("a1b2c3d4-e5f6-4a5b-8c7d-0e1f2a3b4c5d"), model_path))
        model_row = invoke("get", [model_id], "modelCatalog").get("result", {})
        if not model_row.get("isAvailable"):
            root_result = invoke("add", [models_dir.as_posix(), "CU20 Gemma 12B", "manual", []],
                                 "rootRegistry").get("result", "")
            if not root_result:
                raise RuntimeError("No pude agregar la carpeta Gemma al catálogo de prueba")
            wait_until(lambda: bool(invoke("get", [model_id], "modelCatalog")
                                   .get("result", {}).get("isAvailable")),
                       "Gemma 12B en catálogo aislado", 240, 2)
            result["isolated_model_scan"] = {
                "root_id": root_result, "models_dir": models_dir.as_posix(),
                "model_id": model_id, "model_path": model_path,
                "catalog_row": invoke("get", [model_id], "modelCatalog").get("result", {}),
            }
        else:
            result["isolated_model_scan"] = {
                "reused_test_catalog_row": True, "model_id": model_id,
                "model_path": model_path, "catalog_row": model_row,
            }
        server_log_before = str(prop("serverLog"))
        invoke("startServerAndAgent", [MODEL_ID])
        last_state = None
        def ready_state():
            nonlocal last_state
            last_state = {key: prop(key) for key in
                          ("serverRunning", "serverReady", "agentRunning", "agentStarting", "serverState")}
            current_server_log = str(prop("serverLog"))
            if (last_state.get("serverState") in ("failed", "error")
                    or ("startServer abort:" in current_server_log
                        and current_server_log != server_log_before)):
                raise RuntimeError("El server rechazó el perfil de lanzamiento: "
                                   + current_server_log[-2200:])
            return (last_state.get("serverRunning") and last_state.get("serverReady")
                    and last_state.get("agentRunning") and not last_state.get("agentStarting"))
        wait_until(ready_state, "servidor Gemma + agente", args.model_timeout, 2)
        result["started_state"] = last_state
        result["server_base_url"] = prop("serverBaseUrl")
        try:
            result["models_endpoint"] = request_json(
                str(result["server_base_url"]).rstrip("/") + "/v1/models", timeout=10)
        except Exception as exc:
            result["models_endpoint_error"] = f"{type(exc).__name__}: {exc}"
        edge_shortcut = None
        if case_id in {"CU05", "CU06", "CU07", "CU08"}:
            edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            edge_shortcut = (EDGE_TEST_ROOT / args.run_id / "Edge-CU20-UserProfile.lnk").resolve()
            create_edge_shortcut(edge_shortcut, edge)
            save_json(run_dir / "edge-shortcut.json", {
                "shortcut": str(edge_shortcut), "target": edge,
                "arguments": edge_shortcut_arguments(),
                "profile_mode": "existing_user_profile",
                "guest": False, "inprivate": False,
                "user_data_dir_override": None,
                "shortcut_sha256": hashlib.sha256(edge_shortcut.read_bytes()).hexdigest(),
            })
        prompt = case_prompt(case_id, workspace, edge_shortcut,
                             args.diagnostic_target_id, args.diagnostic_target_pid,
                             args.diagnostic_target_file)
        if case_id not in {"CU18", "DIAG_CLOSE_TEST_EXCEL"}:
            prompt = apply_excel_recovery_authorization(case_id, prompt, workspace)
        before = prop("agentMessages")
        before_count = len(before) if isinstance(before, list) else 0
        started = dt.datetime.now().astimezone().isoformat()
        clipboard_before = clipboard_snapshot() if case_id == "CU18" else None
        call = invoke("sendToAgent", [prompt])
        continuation_prompt = None
        continuation_call = None
        inter_turn_excel_cleanup = None
        first_stage_validation = None
        stage_elapsed_seconds = []
        turn_started = time.monotonic()
        delta = []
        turn_error = None
        try:
            first_delta, first_elapsed = wait_turn(before_count, args.turn_timeout,
                                                   edge_shortcut)
            delta = list(first_delta)
            stage_elapsed_seconds.append(round(first_elapsed, 3))
            elapsed = first_elapsed
            if case_id == "CU13":
                first_assistant = next((m for m in reversed(first_delta)
                                        if isinstance(m, dict) and m.get("role") == "assistant"), {})
                first_error = (str(first_assistant.get("content"))
                               if str(first_assistant.get("content", "")).lstrip().startswith("[error:")
                               else None)
                first_stage_validation = validate_cu13_open_turn(first_delta, workspace)
                if first_error:
                    turn_error = first_error
                elif not first_stage_validation.get("passed"):
                    turn_error = "CU13 no completó la primera apertura y lectura: " + json.dumps(
                        first_stage_validation, ensure_ascii=False)
                else:
                    inter_turn_excel_cleanup = close_test_excel_processes(case_id, workspace)
                    if (inter_turn_excel_cleanup.get("remaining_pids")
                            or not inter_turn_excel_cleanup.get("closed_pids")):
                        turn_error = "CU13 no pudo cerrar la primera instancia de Excel del fixture: " + json.dumps(
                            inter_turn_excel_cleanup, ensure_ascii=False)
                    else:
                        continuation_prompt = apply_excel_recovery_authorization(
                            case_id, cu13_reopen_prompt(workspace), workspace)
                        before_second = prop("agentMessages")
                        before_second_count = (len(before_second)
                                               if isinstance(before_second, list) else 0)
                        continuation_call = invoke("sendToAgent", [continuation_prompt])
                        second_delta, second_elapsed = wait_turn(
                            before_second_count, args.turn_timeout, edge_shortcut)
                        delta.extend(second_delta)
                        stage_elapsed_seconds.append(round(second_elapsed, 3))
                        elapsed += second_elapsed
            elif case_id == "CU18":
                first_stage_validation = validate_cu18_copy_stage(first_delta, workspace)
                if not first_stage_validation.get("passed"):
                    turn_error = ("CU18 no superó la verificación Notepad→portapapeles; "
                                  "se detuvo antes de abrir Excel: "
                                  + json.dumps(first_stage_validation, ensure_ascii=False))
                else:
                    first_session_messages = prop("agentMessages")
                    first_session_count = (len(first_session_messages)
                                           if isinstance(first_session_messages, list) else 0)
                    result["fresh_agent_session_before_continuation"] = (
                        start_fresh_agent_session(first_session_count))
                    continuation_prompt = cu18_paste_prompt(workspace)
                    before_second = prop("agentMessages")
                    before_second_count = (len(before_second)
                                           if isinstance(before_second, list) else 0)
                    continuation_call = invoke("sendToAgent", [continuation_prompt])
                    second_delta, second_elapsed = wait_turn(
                        before_second_count, args.turn_timeout, edge_shortcut)
                    delta.extend(second_delta)
                    stage_elapsed_seconds.append(round(second_elapsed, 3))
                    elapsed += second_elapsed
            else:
                delta = list(first_delta)
            last_assistant = next((m for m in reversed(delta)
                                   if isinstance(m, dict) and m.get("role") == "assistant"), {})
            if (not turn_error
                    and str(last_assistant.get("content", "")).lstrip().startswith("[error:")):
                turn_error = str(last_assistant.get("content"))
            failed_tools = [
                m for m in delta
                if isinstance(m, dict) and m.get("role") == "toolcall"
                and (m.get("ok") is False
                     or (isinstance(m.get("desktopReceipt"), dict)
                         and m["desktopReceipt"].get("status") == "failed"))
            ]
            desktop_calls = [
                m for m in delta
                if isinstance(m, dict) and m.get("role") == "toolcall"
                and str(m.get("name", "")).startswith("desktop_")
            ]
            if failed_tools:
                failures = "; ".join(
                    f"{m.get('name')}: {str(m.get('output', ''))[:500]}"
                    for m in failed_tools)
                turn_error = (turn_error + " | " if turn_error else "") + failures
            if not desktop_calls:
                turn_error = ((turn_error + " | ") if turn_error else "") + (
                    "El agente no ejecutó ninguna herramienta desktop_*; el turno no demuestra "
                    "Computer Usage efectivo.")
        except Exception as exc:
            delta.extend(list(getattr(exc, "delta", [])))
            elapsed = time.monotonic() - turn_started
            error_message = f"{type(exc).__name__}: {exc}"
            turn_error = (turn_error + " | " if turn_error else "") + error_message
        clipboard_status = (restore_clipboard_if_unchanged(clipboard_before)
                            if clipboard_before is not None else None)
        images = desktop_images(delta, run_dir, case_id)
        validation = validate_artifact(
            case_id, workspace, delta,
            initial_sha256=case_fixture.get("sha256_before_agent"),
            inter_turn_excel_cleanup=inter_turn_excel_cleanup)
        if validation.get("passed") is False:
            detail = json.dumps(validation, ensure_ascii=False)
            turn_error = (turn_error + " | " if turn_error else "") + "artifact validation failed: " + detail
        excel_cleanup_after = ({"workbook_path": str(case_excel_path(case_id, workspace)),
                               "matched_pids": [], "closed_pids": [], "remaining_pids": []})
        if case_excel_path(case_id, workspace) is not None:
            excel_cleanup_after = close_test_excel_processes(case_id, workspace)
        if excel_cleanup_after.get("remaining_pids"):
            turn_error = ((turn_error + " | ") if turn_error else "") + (
                "Excel de prueba no cerró tras WM_CLOSE; el cierre queda pendiente y "
                "no deben iniciarse otros casos de escritorio.")
        try:
            raw_agent_log = str(prop("agentLog"))
            agent_log = {"sha256": hashlib.sha256(raw_agent_log.encode("utf-8")).hexdigest(),
                         "character_count": len(raw_agent_log), "content_redacted": True}
        except Exception:
            agent_log = None
        safe_delta = sanitize_desktop_observations(delta)
        safe_turn_error = turn_error
        for raw_message, safe_message in zip(delta, safe_delta):
            if (not isinstance(raw_message, dict) or raw_message.get("role") != "toolcall"
                    or raw_message.get("ok") is not False):
                continue
            raw_output = str(raw_message.get("output", ""))[:500]
            safe_output = str(safe_message.get("output", "[detalle omitido]"))
            if raw_output and safe_turn_error:
                safe_turn_error = safe_turn_error.replace(raw_output, safe_output)
        receipt = {
            "case_id": case_id, "started_at_local": started,
            "elapsed_seconds": round(elapsed, 3), "stage_elapsed_seconds": stage_elapsed_seconds,
            "prompt": prompt, "continuation_prompt": continuation_prompt,
            "send_response": call, "messages_delta": safe_delta,
            "continuation_send_response": continuation_call,
            "inter_turn_excel_cleanup": inter_turn_excel_cleanup,
            "first_stage_validation": first_stage_validation,
            "agent_log": agent_log, "copied_window_images": images,
            "artifact_validation": validation,
            "clipboard_preservation": clipboard_status,
            "excel_cleanup_after": excel_cleanup_after,
            "turn_error": safe_turn_error,
        }
        result["cases"].append(receipt)
        save_json(run_dir / f"{case_id}.json", receipt)
        with (run_dir / "progress.jsonl").open("a", encoding="utf-8") as progress:
            progress.write(json.dumps({"case_id": case_id,
                                       "elapsed_seconds": round(elapsed, 3),
                                       "turn_error": safe_turn_error,
                                       "artifact_validation": validation,
                                       "image_count": len(images)}, ensure_ascii=False) + "\n")
        print(console_json_line({"run_id": args.run_id, "case_id": case_id,
                          "elapsed_seconds": round(elapsed, 1),
                          "turn_error": safe_turn_error,
                          "artifact_validation": validation,
                          "clipboard_preservation": clipboard_status,
                          "images": len(images)}), flush=True)
        if turn_error:
            result["stopped_after_unresolved_case"] = case_id

        result["finished_at_local"] = dt.datetime.now().astimezone().isoformat()
        result["case_count"] = len(result["cases"])
        result["errors"] = sum(bool(item["turn_error"]) for item in result["cases"])
        result["server_log_final"] = prop("serverLog")
        return_code = int(result["errors"] > 0)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["agent_log_on_error"] = None
        try:
            raw_agent_log = str(prop("agentLog"))
            result["agent_log_on_error"] = {
                "sha256": hashlib.sha256(raw_agent_log.encode("utf-8")).hexdigest(),
                "character_count": len(raw_agent_log), "content_redacted": True}
            result["server_log_on_error"] = prop("serverLog")
        except Exception:
            pass
        return_code = 1
    finally:
        result["finished_at_local"] = result.get("finished_at_local") or dt.datetime.now().astimezone().isoformat()
        try:
            if request_json(BASE + "/health", timeout=2).get("ok"):
                for method in ("stopAgent", "stopServer"):
                    try:
                        invoke(method)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            daemon.terminate()
            daemon.wait(timeout=20)
        except subprocess.TimeoutExpired:
            daemon.kill()
            daemon.wait(timeout=10)
        except Exception:
            pass
        daemon_log.close()
        restore_settings(settings)
        save_json(run_dir / "RESULT.json", result)
    print(f"RECEIPT={run_dir / 'RESULT.json'}", flush=True)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
