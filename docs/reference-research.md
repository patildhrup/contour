# Reference research — 21 October 2026

REA was requested first. Read its official repository and CLI documentation, then attempted `npx --yes rea-agents --help`. The sandboxed download failed; two unrestricted attempts (including an isolated cache) failed with npm ECONNRESET. REA could not run; no evidence is represented as REA-generated. No user configuration was changed by REA setup.

Fallback: inspected the public website and its built-in gears example in the browser. Observed an upload-first landing page with examples; processing stages Upload / Process / Fetch; a checkerboard preview with Compare / Vector / Outlines modes; refinement controls; and a separate export page offering SVG, PDF, DXF, EPS and PNG. SVG has version and geometry options. These observations informed the upload → inspect → export interaction, not proprietary implementation. No reference artwork or source was copied. Contour supplies original canvas artwork and a separately implemented VTracer pipeline.

Sources:
- https://github.com/morluto/rea
- https://raw.githubusercontent.com/morluto/rea/main/docs/cli.md
- https://vectorizer.ai/

## Engine decision

VTracer's repository is MIT-licensed and supports color tracing. Installed and executed the available Python wheel **0.6.15** on Python 3.12/Windows; verified its `convert_raw_image_to_svg` signature and parsed genuine path output for all accepted formats. The repository's newer desktop/CLI engine has options not present in this Python wheel: this app only exposes verified Python options.

Potrace was evaluated from its official documentation: it is a strong bitmap/monochrome tracer with several output formats and GPL/commercial licensing. A separate Potrace executable would add packaging/licensing complexity without improving this app's color workflow. Use VTracer with explicit grayscale threshold preprocessing for monochrome instead. Pillow handles decoding, EXIF orientation and palette quantization; NumPy handles binary transparency and near-white removal. This is classical automatic tracing, not a trained AI model.

Sources:
- https://github.com/visioncortex/vtracer (MIT)
- https://pypi.org/project/vtracer/0.6.15/
- https://potrace.sourceforge.net/

## Deliberate scope

SVG is the vector export. PNG is a browser-rasterized convenience export, clearly labeled raster. No fake EPS/PDF/DXF buttons. Alpha is thresholded at 128, not preserved as partial opacity. Background removal removes near-white pixels everywhere, not semantic subjects. Photographs, gradients, textures, tiny lettering and low-resolution inputs may need manual refinement. Pricing is a placeholder; no account/billing service is implied.
