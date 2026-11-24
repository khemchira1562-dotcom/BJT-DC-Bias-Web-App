"""Presentation helpers: turn parsed ngspice numbers into inline SVG.

No dependency and no physics here. Values arrive already computed by
spice_engine; this module only maps them to pixels and labels.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping

WIDTH = 760
HEIGHT = 300
LEFT = 62
RIGHT = 18
TOP = 28
BOTTOM = 28


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def _polyline(points: Iterable[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def _x_log(value: float, low: float, high: float) -> float:
    span = max(math.log10(high), math.log10(low) + 1e-9) - math.log10(low)
    return (math.log10(max(value, low)) - math.log10(low)) / span


def bode_svg(series: list[Mapping[str, float]]) -> str:
    """Gain (dB) and phase (deg) versus frequency (Hz)."""
    if not series:
        return '<svg viewBox="0 0 760 300"></svg>'

    frequencies = [float(row["frequency_hz"]) for row in series]
    fmin, fmax = min(frequencies), max(frequencies)
    if fmax <= fmin:
        fmax = fmin * 10.0

    gains = [float(row["gain_db"]) for row in series]
    phases = [float(row["phase_deg"]) for row in series]
    gain_min, gain_max = min(gains), max(gains)
    if gain_max - gain_min < 2.0:
        gain_max = gain_min + 2.0

    plot_left = LEFT + 30
    plot_right = WIDTH - RIGHT - 10
    gain_top, gain_bottom = 34, 140
    phase_top, phase_bottom = 178, 268

    def px(frequency: float) -> float:
        return plot_left + _x_log(frequency, fmin, fmax) * (plot_right - plot_left)

    def gy(gain: float) -> float:
        return gain_bottom - (gain - gain_min) / (gain_max - gain_min) * (
            gain_bottom - gain_top
        )

    def py(phase: float) -> float:
        return phase_bottom - (phase + 180.0) / 360.0 * (phase_bottom - phase_top)

    gain_points = [(px(row["frequency_hz"]), gy(row["gain_db"])) for row in series]
    phase_points = [(px(row["frequency_hz"]), py(row["phase_deg"])) for row in series]

    grid = []
    for decade in range(math.floor(math.log10(fmin)), math.ceil(math.log10(fmax)) + 1):
        frequency = 10.0**decade
        if frequency < fmin or frequency > fmax:
            continue
        x = px(frequency)
        grid.append(
            f'<line x1="{x:.2f}" y1="{gain_top}" x2="{x:.2f}" y2="{phase_bottom}" '
            'stroke="#dce7ee" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{x:.2f}" y="{phase_bottom + 15}" font-size="10" '
            f'text-anchor="middle" fill="#486275">10^{decade}</text>'
        )

    return f'''<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img"
     aria-label="Bode plot from ngspice: gain in dB and phase in degrees versus frequency"
     style="width:100%;height:auto;background:#f9fcfd;border:1px solid #dce7ee;border-radius:8px">
  <text x="{LEFT}" y="18" font-size="12" fill="#103658" font-weight="700">AC response · ngspice</text>
  {''.join(grid)}
  <line x1="{plot_left}" y1="{gain_bottom}" x2="{plot_right}" y2="{gain_bottom}" stroke="#9cb2c2"/>
  <line x1="{plot_left}" y1="{gain_top}" x2="{plot_left}" y2="{gain_bottom}" stroke="#9cb2c2"/>
  <line x1="{plot_left}" y1="{phase_bottom}" x2="{plot_right}" y2="{phase_bottom}" stroke="#9cb2c2"/>
  <line x1="{plot_left}" y1="{phase_top}" x2="{plot_left}" y2="{phase_bottom}" stroke="#9cb2c2"/>
  <text x="8" y="{gain_top + 6}" font-size="11" fill="#486275">{_fmt(gain_max)} dB</text>
  <text x="8" y="{gain_bottom}" font-size="11" fill="#486275">{_fmt(gain_min)} dB</text>
  <text x="12" y="{phase_top + 8}" font-size="11" fill="#486275">+180°</text>
  <text x="12" y="{phase_bottom}" font-size="11" fill="#486275">−180°</text>
  <text x="4" y="{gain_top - 8}" font-size="11" fill="#0c8078">Gain</text>
  <text x="4" y="{phase_top - 8}" font-size="11" fill="#a65a2c">Phase</text>
  <text x="{plot_right}" y="{HEIGHT - 6}" font-size="11" text-anchor="end" fill="#486275">Frequency (Hz)</text>
  <polyline fill="none" stroke="#0c8078" stroke-width="2.2" points="{_polyline(gain_points)}"/>
  <polyline fill="none" stroke="#a65a2c" stroke-width="2" stroke-dasharray="5 3" points="{_polyline(phase_points)}"/>
</svg>'''


def waveform_svg(series: list[Mapping[str, float]]) -> str:
    """Vin / Vout versus time, both in mV and ms."""
    if not series:
        return '<svg viewBox="0 0 760 300"></svg>'

    step = max(1, math.ceil(len(series) / 1000))
    rows = series[::step]
    times = [float(row["time_s"]) * 1000.0 for row in rows] or [0.0, 1.0]
    vin = [float(row["vin_v"]) * 1000.0 for row in rows]
    vout = [float(row["vout_v"]) * 1000.0 for row in rows]
    tmin, tmax = min(times), max(times)
    if tmax <= tmin:
        tmax = tmin + 1e-6
    vmin = min(min(vin), min(vout))
    vmax = max(max(vin), max(vout))
    if vmax - vmin < 1.0:
        vmax = vmin + 1.0

    plot_left, plot_right = LEFT + 10, WIDTH - RIGHT - 10
    plot_top, plot_bottom = 42, 258

    def px(time: float) -> float:
        return plot_left + (time - tmin) / (tmax - tmin) * (plot_right - plot_left)

    def vy(millivolts: float) -> float:
        return plot_bottom - (millivolts - vmin) / (vmax - vmin) * (
            plot_bottom - plot_top
        )

    vin_points = [
        (px(float(row["time_s"]) * 1000.0), vy(float(row["vin_v"]) * 1000.0))
        for row in rows
    ]
    vout_points = [
        (px(float(row["time_s"]) * 1000.0), vy(float(row["vout_v"]) * 1000.0))
        for row in rows
    ]

    return f'''<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img"
     aria-label="Transient plot from ngspice: input and output voltage versus time"
     style="width:100%;height:auto;background:#f9fcfd;border:1px solid #dce7ee;border-radius:8px">
  <text x="{LEFT}" y="18" font-size="12" fill="#103658" font-weight="700">Transient response · ngspice</text>
  <line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" y2="{plot_bottom}" stroke="#9cb2c2"/>
  <line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" y2="{plot_bottom}" stroke="#9cb2c2"/>
  <line x1="{plot_left}" y1="{vy(0.0):.2f}" x2="{plot_right}" y2="{vy(0.0):.2f}" stroke="#cbd8e2" stroke-dasharray="4 4"/>
  <text x="8" y="{plot_top + 8}" font-size="11" fill="#486275">{_fmt(vmax)} mV</text>
  <text x="8" y="{plot_bottom}" font-size="11" fill="#486275">{_fmt(vmin)} mV</text>
  <text x="{plot_right}" y="{HEIGHT - 6}" font-size="11" text-anchor="end" fill="#486275">Time (ms)</text>
  <polyline fill="none" stroke="#0c8078" stroke-width="2.1" points="{_polyline(vin_points)}"/>
  <polyline fill="none" stroke="#c77a35" stroke-width="2.1" points="{_polyline(vout_points)}"/>
  <rect x="{plot_right - 150}" y="{plot_top - 2}" width="150" height="20" rx="4" fill="#ffffff" opacity="0.9"/>
  <line x1="{plot_right - 140}" y1="{plot_top + 8}" x2="{plot_right - 120}" y2="{plot_top + 8}" stroke="#0c8078" stroke-width="2.1"/>
  <text x="{plot_right - 114}" y="{plot_top + 12}" font-size="11" fill="#486275">Vin</text>
  <line x1="{plot_right - 78}" y1="{plot_top + 8}" x2="{plot_right - 58}" y2="{plot_top + 8}" stroke="#c77a35" stroke-width="2.1"/>
  <text x="{plot_right - 52}" y="{plot_top + 12}" font-size="11" fill="#486275">Vout</text>
</svg>'''
