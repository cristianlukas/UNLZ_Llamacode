#!/usr/bin/env python3
"""Small EWMH window manager for private Xvfb computer-use evaluations.

It manages arbitrary client windows and supports the EWMH operations used by
LlamaCode's Linux desktop backend (window inventory, focus, resize, close).
It contains no application-specific behavior.
"""

from __future__ import annotations

import signal
import sys

from Xlib import X, display
from Xlib.protocol import event


dpy = display.Display()
root = dpy.screen().root
atoms = {name: dpy.intern_atom(name) for name in (
    "UTF8_STRING", "_NET_SUPPORTED", "_NET_SUPPORTING_WM_CHECK",
    "_NET_WM_NAME", "_NET_WM_PID", "_NET_WM_DESKTOP",
    "_NET_CLIENT_LIST", "_NET_ACTIVE_WINDOW", "_NET_WM_STATE",
    "_NET_WM_STATE_MAXIMIZED_VERT", "_NET_WM_STATE_MAXIMIZED_HORZ",
    "_NET_FRAME_EXTENTS", "_NET_MOVERESIZE_WINDOW", "_NET_ACTIVE_WINDOW",
    "_NET_CLOSE_WINDOW", "_NET_REQUEST_FRAME_EXTENTS", "WM_PROTOCOLS",
    "WM_DELETE_WINDOW",
)}
clients: list[int] = []


def set_clients() -> None:
    root.change_property(atoms["_NET_CLIENT_LIST"], Xatom_window, 32, clients)
    dpy.flush()


Xatom_window = dpy.intern_atom("WINDOW")
Xatom_atom = dpy.intern_atom("ATOM")
Xatom_cardinal = dpy.intern_atom("CARDINAL")
support = root.create_window(0, 0, 1, 1, 0, X.CopyFromParent, X.InputOutput,
                             X.CopyFromParent, event_mask=X.PropertyChangeMask)
support.change_property(atoms["_NET_WM_NAME"], atoms["UTF8_STRING"], 8,
                        b"LlamaCode Evaluation EWMH")
root.change_property(atoms["_NET_SUPPORTING_WM_CHECK"], Xatom_window, 32,
                     [support.id])
support.change_property(atoms["_NET_SUPPORTING_WM_CHECK"], Xatom_window, 32,
                       [support.id])
supported = [atoms[name] for name in (
    "_NET_SUPPORTED", "_NET_SUPPORTING_WM_CHECK", "_NET_WM_NAME",
    "_NET_WM_DESKTOP", "_NET_CLIENT_LIST", "_NET_ACTIVE_WINDOW",
    "_NET_WM_STATE", "_NET_WM_STATE_MAXIMIZED_VERT",
    "_NET_WM_STATE_MAXIMIZED_HORZ", "_NET_FRAME_EXTENTS",
    "_NET_MOVERESIZE_WINDOW", "_NET_CLOSE_WINDOW",
    "_NET_REQUEST_FRAME_EXTENTS",
)]
root.change_property(atoms["_NET_SUPPORTED"], Xatom_atom, 32, supported)
root.change_property(dpy.intern_atom("_NET_NUMBER_OF_DESKTOPS"), Xatom_cardinal,
                     32, [1])
root.change_property(dpy.intern_atom("_NET_CURRENT_DESKTOP"), Xatom_cardinal,
                     32, [0])
root.change_property(dpy.intern_atom("_NET_WORKAREA"), dpy.intern_atom("CARDINAL"),
                     32, [0, 0, dpy.screen().width_in_pixels,
                          dpy.screen().height_in_pixels])
root.change_attributes(event_mask=X.SubstructureRedirectMask |
                       X.SubstructureNotifyMask | X.PropertyChangeMask)
dpy.sync()


def activate(window_id: int) -> None:
    try:
        win = dpy.create_resource_object("window", window_id)
        win.map()
        win.set_input_focus(X.RevertToParent, X.CurrentTime)
        root.change_property(atoms["_NET_ACTIVE_WINDOW"], Xatom_window, 32,
                             [window_id])
        dpy.flush()
    except Exception:
        pass


def handle(ev) -> None:
    if ev.type == X.MapRequest:
        win = ev.window
        win.change_property(atoms["_NET_WM_DESKTOP"], dpy.intern_atom("CARDINAL"),
                            32, [0])
        win.change_property(atoms["_NET_FRAME_EXTENTS"],
                            dpy.intern_atom("CARDINAL"), 32, [0, 0, 0, 0])
        win.map()
        if win.id not in clients:
            clients.append(win.id)
            set_clients()
        activate(win.id)
    elif ev.type == X.ConfigureRequest:
        values = {}
        for mask, key in ((X.CWX, "x"), (X.CWY, "y"), (X.CWWidth, "width"),
                          (X.CWHeight, "height"), (X.CWBorderWidth, "border_width"),
                          (X.CWSibling, "sibling"), (X.CWStackMode, "stack_mode")):
            if ev.value_mask & mask:
                values[key] = getattr(ev, key)
        ev.window.configure(**values)
    elif ev.type == X.DestroyNotify:
        if ev.window.id in clients:
            clients.remove(ev.window.id)
            set_clients()
    elif ev.type == X.ClientMessage:
        kind = ev.client_type
        raw_data = ev.data
        data = list(raw_data[1] if isinstance(raw_data, tuple)
                    else raw_data.data32)
        if kind == atoms["_NET_ACTIVE_WINDOW"]:
            activate(ev.window.id)
        elif kind == atoms["_NET_MOVERESIZE_WINDOW"]:
            flags = data[0] & 0xF
            values = {}
            for bit, key, value in zip((1, 2, 4, 8),
                                       ("x", "y", "width", "height"), data[1:5]):
                if flags & bit:
                    values[key] = value
            if values:
                ev.window.configure(**values)
        elif kind == atoms["_NET_CLOSE_WINDOW"]:
            try:
                protocols = ev.window.get_wm_protocols() or []
                if atoms["WM_DELETE_WINDOW"] in protocols:
                    ev.window.send_event(event.ClientMessage(
                        window=ev.window, client_type=atoms["WM_PROTOCOLS"],
                        data=(32, [atoms["WM_DELETE_WINDOW"], X.CurrentTime, 0, 0, 0])),
                        event_mask=0)
                else:
                    ev.window.destroy()
            except Exception:
                pass
        elif kind == atoms["_NET_WM_STATE"]:
            action = data[0]
            state_atoms = [data[1], data[2]]
            current = ev.window.get_full_property(atoms["_NET_WM_STATE"], Xatom_atom)
            current_states = list(current.value) if current else []
            for atom in state_atoms:
                if atom not in (atoms["_NET_WM_STATE_MAXIMIZED_VERT"],
                                atoms["_NET_WM_STATE_MAXIMIZED_HORZ"]):
                    continue
                if action == 0 and atom in current_states:
                    current_states.remove(atom)
                elif action == 1 and atom not in current_states:
                    current_states.append(atom)
                elif action == 2:
                    current_states = [a for a in current_states if a != atom] \
                        if atom in current_states else current_states + [atom]
            ev.window.change_property(atoms["_NET_WM_STATE"], Xatom_atom, 32,
                                      current_states)
            if any(a in current_states for a in state_atoms):
                ev.window.configure(x=0, y=0, width=dpy.screen().width_in_pixels,
                                    height=dpy.screen().height_in_pixels)
        elif kind == atoms["_NET_REQUEST_FRAME_EXTENTS"]:
            ev.window.change_property(atoms["_NET_FRAME_EXTENTS"],
                                      dpy.intern_atom("CARDINAL"), 32,
                                      [0, 0, 0, 0])


def stop(_sig, _frame) -> None:
    dpy.close()
    sys.exit(0)


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
while True:
    handle(dpy.next_event())
