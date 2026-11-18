# Glossary

Terms used in this project, in plain language. Add new terms as they come up.

---

## Investigations (ways of finding out what's underground)

### CPT: Cone Penetration Test
A steel rod with a cone on the tip is **pushed** into the ground by a truck- or rig-mounted hydraulic ram, at a steady rate of about 2 cm per second. Sensors in the cone record a reading every 1–2 cm as it goes down. That gives a continuous profile of how the ground resists the cone, from the surface to the bottom of the test (often 10–20 m).

It measures three things:
- **qc (cone/tip resistance)**: how hard the ground pushes back on the tip. High in dense sand and gravel, low in soft silt, clay and peat. Usually in MPa.
- **fs (sleeve friction)**: the drag on a sleeve just behind the tip. Clays are "sticky" relative to their tip resistance; sands are not.
- **u2 (pore water pressure)**: the water pressure just behind the cone. It shows the groundwater and helps tell sand from clay.

A CPT **doesn't bring up any soil**. The soil type is *inferred* from the ratio between these readings, using a standard chart (see *Ic*). It's cheap, fast and very repeatable, which is why there are tens of thousands of them in Christchurch. CPTs often stop ("refuse") when they hit dense gravel, because the rig can't push any harder.

### SCPT: Seismic CPT
A CPT that also has a sensor which picks up shear waves sent down from a hammer blow at the surface. It measures how stiff the ground is (shear-wave velocity, *Vs*).

### BH: Borehole
A hole **drilled** into the ground. Soil samples come up and a geologist describes them by depth, for example "0.0–1.2 m: brown silty SAND, loose, moist". The result is a **borehole log**: a list of depth intervals with descriptions. It's slower and more expensive than a CPT, but you see the actual material, and it can get through gravel.

### Bore log / borehole log
The written record from a borehole: depth intervals, soil descriptions and sometimes test results and groundwater level. In this project, a parsed log becomes a list of `Interval`s (top, bottom, material).

### DPCH
Another type of test on the NZGD, probably a **dynamic probe** (a cone *hammered* into the ground, counting blows per depth increment). _To be confirmed against the NZGD's list of investigation types._

### Groundwater depth
The depth below the ground surface at which the soil is fully saturated with water. In Christchurch it's often only 1–3 m down. It matters a lot for liquefaction.

### Liquefaction
In an earthquake, shaking can make loose, saturated sand behave briefly like a liquid. Buildings sink and tilt, and sand boils up through the ground. It happened across eastern Christchurch in 2010–11.

### Ic: Soil Behaviour Type Index
A single number calculated from a CPT's `qc` and `fs` that puts each reading into a soil class (gravelly sand, sand, silty sand, silt, clay, organic). This is how a continuous CPT trace becomes layers. It's planned for Phase 1.

---

## Places, people and data sources

### OSU: Oregon State University
A US university. Its researchers (Stuedlein, Jana and Cary) carried out the CPTs in the DesignSafe dataset PRJ-3352. In the file names, `OSU-A1` means **OSU's CPT number 1 at the Avondale site**. The other sites follow the same pattern: S = Shirley, T = Ti Rakau, M = Meadow St.

### DesignSafe (DesignSafe-CI)
A US-funded online repository for natural-hazards research data. This is where the OSU dataset is published.

### NZGD: New Zealand Geotechnical Database
New Zealand's national database of geotechnical investigations, run by MBIE. It's the main source of CPTs and boreholes for this project. See `decisions.md` D-001 for what its terms allow.

### ECan: Environment Canterbury
The Canterbury regional council. It keeps a database of water wells, many with bore logs.

### LINZ: Land Information New Zealand (Toitū Te Whenua)
The government agency that publishes New Zealand's maps, coordinate systems and LiDAR elevation data.

---

## Coordinates and heights

### Coordinate reference system (CRS)
The rules that turn numbers into a position on Earth. The same point has different numbers in different systems, so every coordinate needs to say which CRS it's in.

### EPSG code
A standard ID number for a CRS, for example `EPSG:2193` (NZTM2000) or `EPSG:4326` (WGS84 lat/lon). Libraries such as `pyproj` use these codes.

### Latitude / longitude
Angles that say how far north or south of the equator (latitude) and east or west of Greenwich (longitude) a point is. They're written in degrees, either as degrees-minutes-seconds (43°30'29.28" S) or as decimal degrees (−43.508133). South and west are negative. Good for web maps, awkward for measuring distances.

### Eastings and northings
Coordinates in **metres** on a flat map grid (a *projected* CRS), instead of angles on a globe.
- **Easting**: how far east a point is from the grid's reference line. Bigger numbers are further east.
- **Northing**: how far north a point is from the grid's reference line. Bigger numbers are further north.

Because they're in metres, distance is just Pythagoras: `√(ΔE² + ΔN²)`. That's why the pipeline does all its maths in eastings and northings.

In New Zealand they're usually **NZTM2000** values. Christchurch is around **E 1,570,000 m, N 5,180,000 m**. The numbers are large because the grid's origin is set far to the south-west, so every value in New Zealand comes out positive. A common bug is mixing up the order: write easting first, then northing (like x then y).

### NZTM2000: New Zealand Transverse Mercator 2000 (EPSG:2193)
New Zealand's standard national map grid, in metres. The pipeline stores everything in it.

### WGS84 (EPSG:4326)
The global lat/lon system used by GPS and web maps. In New Zealand it's within about a metre of NZGD2000, the country's own lat/lon datum.

### Datum (vertical datum)
The "zero" that heights are measured from. The same spot can have a different height number depending on the datum.
- **NZVD2016**: New Zealand's current national vertical datum. The project uses this one.
- **LVD37 (Lyttelton Vertical Datum 1937)**: the old local datum for Christchurch.
- **CDD (Christchurch Drainage Datum)**: the council's own datum, offset from LVD37.

### Collar / collar elevation
The top of a borehole or CPT at ground level, and its height above the datum. Layer elevation = collar elevation − depth.

### Depth vs elevation
**Depth** is measured downwards from the ground surface at that hole. **Elevation** is height above the datum. Logs give depths; the 3D model needs elevations.

### DEM: Digital Elevation Model
A grid of ground heights. LINZ publishes a 1 m DEM for Christchurch, made from LiDAR.

### LiDAR
Laser scanning from an aircraft, used to measure the ground surface very accurately (to roughly 10–20 cm vertically).
