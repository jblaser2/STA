#!/usr/bin/env python3
"""
Subtomogram alignment reviewer.

Press Y / Enter      = aligned (good)
Press N / Backspace  = NOT aligned (flagged)
Press O              = Other — type a note, then Enter to confirm
Press B / Left arrow = Go back to previous subtomo and re-judge it
Press S              = Skip (revisit at end)
Press Q              = Quit and save progress

Resume works automatically — completed tomos are skipped on re-run.
Results: STA/alignment_review_results.txt
Progress: STA/alignment_review_progress.json
"""

import sys
import json
from pathlib import Path

import numpy as np
import mrcfile
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Button, TextBox

SUBTOMOS_DIR = Path(__file__).parent.parent / "subtomos_mrc"
PROGRESS_FILE = Path(__file__).parent / "alignment_review_progress.json"
RESULTS_FILE = Path(__file__).parent / "alignment_review_results.txt"


def normalize_slice(sl):
    p2, p98 = np.percentile(sl, (2, 98))
    if p98 == p2:
        return np.zeros_like(sl, dtype=float)
    return np.clip((sl.astype(float) - p2) / (p98 - p2), 0, 1)


def load_slices(mrc_path, half_slab=5):
    with mrcfile.open(str(mrc_path), mode='r', permissive=True) as f:
        data = f.data.copy()
    nz, ny, nx = data.shape
    cz, cy, cx = nz // 2, ny // 2, nx // 2
    z_sl = normalize_slice(data[max(0, cz-half_slab):cz+half_slab, :, :].mean(axis=0))
    y_sl = normalize_slice(data[:, max(0, cy-half_slab):cy+half_slab, :].mean(axis=1))
    x_sl = normalize_slice(data[:, :, max(0, cx-half_slab):cx+half_slab].mean(axis=2))
    return z_sl, y_sl, x_sl


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            raw = json.load(f)
        reviewed = {}
        for name, val in raw.get("reviewed", {}).items():
            if isinstance(val, str):
                reviewed[name] = {"verdict": val, "note": ""}
            else:
                reviewed[name] = val
        return {"reviewed": reviewed, "skipped": raw.get("skipped", [])}
    return {"reviewed": {}, "skipped": []}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def save_results(progress):
    reviewed = progress["reviewed"]
    bad = {n: v for n, v in reviewed.items() if v["verdict"] == "bad"}
    other = {n: v for n, v in reviewed.items() if v["verdict"] == "other"}
    good_count = sum(1 for v in reviewed.values() if v["verdict"] == "good")
    total_reviewed = len(reviewed)

    with open(RESULTS_FILE, "w") as f:
        f.write("Alignment Review Results\n")
        f.write("========================\n")
        f.write(f"Total reviewed : {total_reviewed}\n")
        f.write(f"Good (aligned) : {good_count}\n")
        f.write(f"Bad (flagged)  : {len(bad)}\n")
        f.write(f"Other (notes)  : {len(other)}\n\n")
        if bad:
            f.write("NOT ALIGNED:\n")
            for name in sorted(bad):
                note = bad[name].get("note", "")
                suffix = f'  — "{note}"' if note else ""
                f.write(f"  {name}{suffix}\n")
            f.write("\n")
        if other:
            f.write("OTHER (with notes):\n")
            for name in sorted(other):
                note = other[name].get("note", "")
                f.write(f'  {name}  — "{note}"\n')
            f.write("\n")
        if not bad and not other:
            f.write("All reviewed subtomos appear aligned.\n")

    print(f"\nResults written to: {RESULTS_FILE}")
    if bad:
        print(f"  {len(bad)} flagged as NOT aligned:")
        for name in sorted(bad):
            print(f"    {name}")
    if other:
        print(f"  {len(other)} flagged as Other:")
        for name, v in sorted(other.items()):
            print(f'    {name}  — "{v.get("note", "")}"')
    if not bad and not other:
        print("  All reviewed subtomos appear aligned.")


def main():
    all_files = sorted(SUBTOMOS_DIR.glob("*.mrc"))
    if not all_files:
        print(f"No .mrc files found in {SUBTOMOS_DIR}")
        sys.exit(1)

    total = len(all_files)
    progress = load_progress()

    skipped_set = set(progress.get("skipped", []))
    reviewed_set = set(progress["reviewed"].keys())
    todo = [f for f in all_files if f.name not in reviewed_set and f.name not in skipped_set]
    skipped_files = [f for f in all_files if f.name in skipped_set]
    queue = todo + skipped_files

    if not queue:
        print("All subtomos already reviewed.")
        save_results(progress)
        return

    already_done = len(reviewed_set)
    print("Subtomogram alignment reviewer")
    print(f"  Total files   : {total}")
    print(f"  Already done  : {already_done}")
    print(f"  To review     : {len(queue)}")
    print()
    print("Controls:")
    print("  Y / Enter      = aligned (good)")
    print("  N              = NOT aligned")
    print("  O              = Other — type a note, then Enter")
    print("  B / Left arrow = go back and re-judge previous")
    print("  S              = skip for now")
    print("  Q              = quit and save")
    print()

    # ── Figure layout ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(13, 6))
    fig.patch.set_facecolor("#1a1a2e")

    gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.05,
                           left=0.03, right=0.97, top=0.82, bottom=0.22)
    ax_z = fig.add_subplot(gs[0, 0])
    ax_y = fig.add_subplot(gs[0, 1])
    ax_x = fig.add_subplot(gs[0, 2])

    for ax, label in zip((ax_z, ax_y, ax_x),
                          ("Z avg slab (axial)", "Y avg slab (coronal)", "X avg slab (sagittal)")):
        ax.set_facecolor("#0d0d1a")
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        for sp in ax.spines.values():
            sp.set_edgecolor("#444")
        ax.set_title(label, color="#aaa", fontsize=9)

    im_z = ax_z.imshow(np.zeros((80, 80)), cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    im_y = ax_y.imshow(np.zeros((80, 80)), cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    im_x = ax_x.imshow(np.zeros((80, 80)), cmap="gray", vmin=0, vmax=1, interpolation="nearest")

    # Green crosshair overlay — drawn once, stays on top of every image update
    _cross_kw = dict(color="#00ff55", lw=0.9, alpha=0.75, linestyle="--")
    for _ax in (ax_z, ax_y, ax_x):
        _ax.axhline(39.5, **_cross_kw)
        _ax.axvline(39.5, **_cross_kw)

    title_txt = fig.suptitle("", color="white", fontsize=11, fontweight="bold")
    verdict_txt = fig.text(0.5, 0.88, "", ha="center", va="center",
                           fontsize=13, color="white", fontweight="bold")

    # ── Buttons ────────────────────────────────────────────────────────────────
    btn_specs = [
        (0.03, "B  Back",         "#2a1a4a", "#3a2a6a"),
        (0.21, "Y  Aligned",      "#1a4a2a", "#2a7a3a"),
        (0.39, "N  NOT aligned",  "#4a1a1a", "#7a2a2a"),
        (0.57, "O  Other/note",   "#1a2a4a", "#2a3a7a"),
        (0.72, "S  Skip",         "#3a3a1a", "#5a5a2a"),
        (0.87, "Q  Quit",         "#2a2a2a", "#444"),
    ]
    buttons = []
    for x, label, c, hc in btn_specs:
        ax_b = fig.add_axes([x, 0.08, 0.14, 0.07])
        b = Button(ax_b, label, color=c, hovercolor=hc)
        b.label.set_color("white")
        b.label.set_fontsize(10)
        buttons.append(b)
    btn_back, btn_y, btn_n, btn_o, btn_s, btn_q = buttons

    # ── TextBox for "Other" notes ───────────────────────────────────────────────
    ax_tb = fig.add_axes([0.10, 0.01, 0.80, 0.06])
    ax_tb.set_visible(False)
    textbox = TextBox(ax_tb, "Note: ", initial="", color="#111133", hovercolor="#111155")
    textbox.label.set_color("#aaa")
    textbox.text_disp.set_color("white")

    # ── State ──────────────────────────────────────────────────────────────────
    # history tracks names of queue items reviewed this session, in order,
    # so "go back" knows what to un-review.
    state = {"idx": 0, "quit": False, "waiting_note": False, "history": []}

    def show_current(flash=""):
        idx = state["idx"]
        if idx >= len(queue):
            plt.close(fig)
            return
        mrc_path = queue[idx]
        done_so_far = len(progress["reviewed"])
        remaining = len(queue) - idx
        pct = 100.0 * done_so_far / total

        z_sl, y_sl, x_sl = load_slices(mrc_path)
        im_z.set_data(z_sl)
        im_y.set_data(y_sl)
        im_x.set_data(x_sl)

        title_txt.set_text(
            f"{mrc_path.name}    "
            f"[{done_so_far}/{total}  —  {pct:.1f}% done  |  {remaining} remaining]"
        )
        verdict_txt.set_text(flash)
        verdict_txt.set_color("#aaaaff")
        _hide_textbox()
        fig.canvas.draw_idle()

    def _show_textbox():
        ax_tb.set_visible(True)
        textbox.set_val("")
        fig.canvas.draw_idle()
        textbox.begin_typing()

    def _hide_textbox():
        state["waiting_note"] = False
        ax_tb.set_visible(False)

    def go_back():
        if not state["history"]:
            verdict_txt.set_text("Nothing to go back to.")
            verdict_txt.set_color("#888888")
            fig.canvas.draw_idle()
            return

        prev_name = state["history"].pop()
        # Un-review or un-skip the previous file
        if prev_name in progress["reviewed"]:
            del progress["reviewed"][prev_name]
        if prev_name in progress.get("skipped", []):
            progress["skipped"].remove(prev_name)

        state["idx"] -= 1
        save_progress(progress)
        show_current(flash="← Going back…")

    def record(verdict_str, color, note=""):
        if state["idx"] >= len(queue):
            return
        name = queue[state["idx"]].name
        verdict_txt.set_text(f"Marked: {verdict_str}" + (f'  — "{note}"' if note else ""))
        verdict_txt.set_color(color)

        if verdict_str == "SKIP":
            if name not in progress["skipped"]:
                progress["skipped"].append(name)
        else:
            verdict_key = {"ALIGNED": "good", "NOT ALIGNED": "bad", "OTHER": "other"}[verdict_str]
            progress["reviewed"][name] = {"verdict": verdict_key, "note": note}
            if name in progress.get("skipped", []):
                progress["skipped"].remove(name)

        state["history"].append(name)
        save_progress(progress)
        fig.canvas.draw_idle()

        state["idx"] += 1
        fig.canvas.start_event_loop(0.18)
        if state["quit"] or state["idx"] >= len(queue):
            plt.close(fig)
        else:
            show_current()

    def on_note_submit(text):
        note = text.strip()
        record("OTHER", "#aa66ff", note=note)

    textbox.on_submit(on_note_submit)

    def on_key(event):
        if state["waiting_note"]:
            if event.key == "escape":
                _hide_textbox()
                verdict_txt.set_text("")
                fig.canvas.draw_idle()
            return

        k = event.key
        if k in ("y", "Y", "return"):
            record("ALIGNED", "#44ff88")
        elif k in ("n", "N"):
            record("NOT ALIGNED", "#ff4444")
        elif k in ("o", "O"):
            state["waiting_note"] = True
            verdict_txt.set_text("Type a note below, then press Enter…")
            verdict_txt.set_color("#aa66ff")
            fig.canvas.draw_idle()
            _show_textbox()
        elif k in ("b", "B", "left"):
            go_back()
        elif k in ("s", "S"):
            record("SKIP", "#ffaa33")
        elif k in ("q", "Q"):
            state["quit"] = True
            plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)

    btn_back.on_clicked(lambda _: go_back())
    btn_y.on_clicked(lambda _: record("ALIGNED", "#44ff88"))
    btn_n.on_clicked(lambda _: record("NOT ALIGNED", "#ff4444"))
    btn_s.on_clicked(lambda _: record("SKIP", "#ffaa33"))
    btn_q.on_clicked(lambda _: (state.update({"quit": True}), plt.close(fig)))

    def on_other_btn(_):
        state["waiting_note"] = True
        verdict_txt.set_text("Type a note below, then press Enter…")
        verdict_txt.set_color("#aa66ff")
        fig.canvas.draw_idle()
        _show_textbox()

    btn_o.on_clicked(on_other_btn)

    show_current()

    try:
        plt.show()
    except Exception:
        pass

    save_results(progress)
    print(f"Progress saved to: {PROGRESS_FILE}")
    skipped_count = len(progress.get("skipped", []))
    if skipped_count:
        print(f"  {skipped_count} skipped — re-run to review them.")


if __name__ == "__main__":
    main()
