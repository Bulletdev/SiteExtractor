"""Interface gráfica (Tkinter) do Site Extractor.

O download roda numa *thread* separada para não congelar a janela, e o
progresso é refletido numa barra e num rótulo de status. A comunicação entre a
thread de trabalho e a interface acontece por uma fila, respeitando o modelo
*single-thread* do Tkinter.
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .crawler import SiteExtractor, create_zip


class SiteExtractorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Site Extractor")
        self.root.geometry("520x300")
        self.root.minsize(480, 280)

        self._events: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._extractor: SiteExtractor | None = None

        self._build_widgets()
        self.root.after(100, self._drain_events)

    # UI

    def _build_widgets(self) -> None:
        pad = {"padx": 12, "pady": 6}

        tk.Label(self.root, text="URL do site:").pack(anchor="w", **pad)
        self.entry_url = tk.Entry(self.root, width=60)
        self.entry_url.pack(fill="x", padx=12)

        options = tk.Frame(self.root)
        options.pack(fill="x", **pad)

        tk.Label(options, text="Profundidade:").pack(side="left")
        self.spin_depth = tk.Spinbox(options, from_=0, to=10, width=4)
        self.spin_depth.delete(0, "end")
        self.spin_depth.insert(0, "1")
        self.spin_depth.pack(side="left", padx=(4, 16))

        self.var_robots = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options, text="Respeitar robots.txt", variable=self.var_robots
        ).pack(side="left")

        self.var_zip = tk.BooleanVar(value=True)
        tk.Checkbutton(options, text="Gerar ZIP", variable=self.var_zip).pack(
            side="left", padx=8
        )

        buttons = tk.Frame(self.root)
        buttons.pack(fill="x", **pad)
        self.btn_start = tk.Button(buttons, text="Baixar Site", command=self._start)
        self.btn_start.pack(side="left")
        self.btn_cancel = tk.Button(
            buttons, text="Cancelar", command=self._cancel, state="disabled"
        )
        self.btn_cancel.pack(side="left", padx=8)

        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=(10, 4))

        self.status = tk.Label(self.root, text="Pronto.", anchor="w", fg="gray")
        self.status.pack(fill="x", padx=12)

    # actions

    def _start(self) -> None:
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "Informe a URL do site.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        output_dir = filedialog.askdirectory(title="Escolha a pasta de destino")
        if not output_dir:
            return

        try:
            depth = int(self.spin_depth.get())
        except ValueError:
            depth = 1

        self._extractor = SiteExtractor(
            url,
            output_dir,
            max_depth=depth,
            respect_robots=self.var_robots.get(),
            progress_callback=self._on_progress,
        )

        self.btn_start.config(state="disabled")
        self.btn_cancel.config(state="normal")
        self.progress.config(mode="indeterminate")
        self.progress.start(15)
        self._set_status("Iniciando…")

        self._worker = threading.Thread(
            target=self._run_worker,
            args=(output_dir, self.var_zip.get()),
            daemon=True,
        )
        self._worker.start()

    def _cancel(self) -> None:
        if self._extractor is not None:
            self._extractor.cancel()
            self._set_status("Cancelando…")

    def _run_worker(self, output_dir: str, make_zip: bool) -> None:
        try:
            result = self._extractor.run()
            zip_path = None
            if make_zip and result.pages_visited:
                zip_path = os.path.abspath(output_dir.rstrip("/\\")) + ".zip"
                create_zip(output_dir, zip_path)
            self._events.put(("done", result, zip_path))
        except Exception as exc:  # noqa: BLE001 - reportado na UI
            self._events.put(("error", str(exc), None))

    # thread bridge

    def _on_progress(self, done: int, total: int, message: str) -> None:
        # Chamado pela thread de trabalho - apenas enfileira o evento.
        self._events.put(("progress", (done, total), message))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload, extra = self._events.get_nowait()
                if kind == "progress":
                    done, total = payload
                    self._set_status(f"[{done}/{total}] {extra}")
                elif kind == "done":
                    self._finish(payload, extra)
                elif kind == "error":
                    self._fail(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)

    def _finish(self, result, zip_path) -> None:
        self.progress.stop()
        self.progress.config(mode="determinate", value=100)
        self.btn_start.config(state="normal")
        self.btn_cancel.config(state="disabled")
        msg = (
            f"Concluído.\n\n"
            f"Páginas: {result.pages_visited}\n"
            f"Arquivos: {result.files_downloaded}\n"
            f"Erros: {len(result.errors)}"
        )
        if zip_path:
            msg += f"\n\nZIP: {zip_path}"
        self._set_status("Concluído.")
        messagebox.showinfo("Site Extractor", msg)

    def _fail(self, error: str) -> None:
        self.progress.stop()
        self.progress.config(mode="determinate", value=0)
        self.btn_start.config(state="normal")
        self.btn_cancel.config(state="disabled")
        self._set_status("Erro.")
        messagebox.showerror("Erro", error)

    def _set_status(self, text: str) -> None:
        self.status.config(text=text)


def main() -> None:
    root = tk.Tk()
    SiteExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
