<%
# Matches the layout in module.cpp.mako: 7 rows per column pair, 4 HP per pair.
n_audio = max(e.dsp.n_inputs, e.dsp.n_outputs) if e.dsp else e.n_channels
n_rows = len(e.params) + n_audio
hp = 1 + 4 * max(1, -(-n_rows // 7))
width = hp * 5.08
%>\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${f"{width:.2f}"}mm" height="128.5mm" viewBox="0 0 ${f"{width:.2f}"} 128.5">
  <rect width="${f"{width:.2f}"}" height="128.5" fill="#e6e6e6"/>
</svg>
