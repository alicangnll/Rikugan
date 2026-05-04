"""IDA PluginForm wrapper around the shared Spectra panel core."""

from __future__ import annotations

import importlib
from typing import Any

from spectra.ui.panel_core import SpectraPanelCore
from spectra.ui.qt_compat import QT_BINDING, QVBoxLayout, QWidget

from .actions import SpectraUIHooks
from .session_controller import IdaSessionController

idaapi = importlib.import_module("idaapi")


class SpectraPanel(idaapi.PluginForm):
    """IDA dockable form embedding the shared panel core widget."""

    def __init__(self):
        super().__init__()
        self._form_widget: QWidget | None = None
        self._root: QWidget | None = None
        self._core: SpectraPanelCore | None = None

    def OnCreate(self, form: Any) -> None:
        if QT_BINDING == "PyQt5":
            self._form_widget = self.FormToPyQtWidget(form)
        else:
            try:
                self._form_widget = self.FormToPySideWidget(form)
            except Exception:
                self._form_widget = self.FormToPyQtWidget(form)

        self._root = QWidget()
        form_layout = QVBoxLayout(self._form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.addWidget(self._root)

        root_layout = QVBoxLayout(self._root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self._core = SpectraPanelCore(
            controller_factory=IdaSessionController,
            ui_hooks_factory=lambda panel_getter: SpectraUIHooks(panel_getter=panel_getter),
            parent=self._root,
        )
        root_layout.addWidget(self._core)

    def OnClose(self, form):
        self.shutdown()
        if self._root is not None:
            self._root.setParent(None)
            self._root.deleteLater()
            self._root = None

    def show(self):
        result = self.Show(
            "Spectra",
            options=(idaapi.PluginForm.WOPN_TAB | idaapi.PluginForm.WOPN_PERSIST),
        )
        return result

    def close(self):
        self.Close(0)

    def shutdown(self) -> None:
        if self._core is not None:
            self._core.shutdown()
            self._core.setParent(None)
            self._core.deleteLater()
            self._core = None

    def prefill_input(self, text: str, auto_submit: bool = False) -> None:
        if self._core is not None:
            self._core.prefill_input(text, auto_submit=auto_submit)

    def on_database_changed(self, new_path: str) -> None:
        if self._core is not None:
            self._core.on_database_changed(new_path)

    def __getattr__(self, name: str):
        # Forward UI action accessors like _input_area / _on_submit.
        core = object.__getattribute__(self, "_core")
        if core is not None and hasattr(core, name):
            return getattr(core, name)
        raise AttributeError(name)
