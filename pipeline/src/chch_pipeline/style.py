"""Colours shared by the map page and the 3D viewer, so both read the same way."""

# Robertson soil behaviour type zone -> colour. 0 = unknown / no data.
ZONE_COLOURS = {
    7: "#b8862b",  # gravelly sand to dense sand
    6: "#e3c069",  # sand
    5: "#b9c47c",  # sand mixtures
    4: "#79a88f",  # silt mixtures
    3: "#5b7ea3",  # clay
    2: "#5e4130",  # organic / peat
    0: "var(--unknown)",
}
UNKNOWN_HEX = "#bdb8ae"  # for places that can't use the CSS variable
