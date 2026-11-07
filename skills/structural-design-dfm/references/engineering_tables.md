# Mechanical Engineering & DFM Reference Tables

## 1. Metric Fastener Dimensions (mm) — Calibrated for FDM/SLA & CNC

| Size | Pitch | Close Clearance | Medium Clearance | Free Clearance | Socket Head Counterbore ($\varnothing \times \text{Depth}$) | 90° Countersink $\varnothing$ | Hex Nut Trap (Flats / Corners / Depth) | Heat-Set Insert Bore ($\varnothing \times \text{Min OD} \times \text{Depth}$) | Plastic Self-Tap Bore |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M1.6** | 0.35 | 1.75 | 1.85 | 2.00 | $3.5 \times 1.8$ | 3.4 | $3.40 / 3.93 / 1.5$ | $2.6 \times 5.2 \times 3.5$ | 1.40 |
| **M2** | 0.40 | 2.20 | 2.40 | 2.60 | $4.4 \times 2.2$ | 4.2 | $4.20 / 4.85 / 1.8$ | $3.2 \times 6.0 \times 4.0$ | 1.75 |
| **M2.5** | 0.45 | 2.70 | 2.90 | 3.10 | $5.4 \times 2.7$ | 5.2 | $5.20 / 6.00 / 2.2$ | $4.0 \times 7.0 \times 5.0$ | 2.20 |
| **M3** | 0.50 | 3.20 | 3.40 | 3.60 | $6.2 \times 3.2$ | 6.4 | $5.70 / 6.58 / 2.6$ | $4.1 \times 8.0 \times 5.8$ | 2.70 |
| **M4** | 0.70 | 4.30 | 4.50 | 4.80 | $8.0 \times 4.2$ | 8.6 | $7.20 / 8.31 / 3.4$ | $5.6 \times 10.4 \times 7.5$ | 3.60 |
| **M5** | 0.80 | 5.30 | 5.50 | 5.80 | $9.5 \times 5.2$ | 10.6 | $8.20 / 9.47 / 4.2$ | $6.4 \times 12.0 \times 9.0$ | 4.50 |
| **M6** | 1.00 | 6.40 | 6.60 | 7.00 | $11.0 \times 6.2$ | 12.8 | $10.20 / 11.78 / 5.2$ | $8.0 \times 15.0 \times 11.5$ | 5.40 |
| **M8** | 1.25 | 8.40 | 9.00 | 9.50 | $14.5 \times 8.2$ | 17.0 | $13.30 / 15.36 / 6.8$ | $10.2 \times 19.0 \times 14.0$ | 7.20 |
| **M10** | 1.50 | 10.50 | 11.00 | 12.00 | $17.5 \times 10.2$ | 21.0 | $16.30 / 18.82 / 8.4$ | $12.5 \times 23.0 \times 16.0$ | 9.00 |

---

## 2. Mating Fit Clearances (mm)

| Fit Class | Radial Gap (per side) | Total Diametral / Width Gap | Typical Engineering Application |
| :--- | :--- | :--- | :--- |
| **Interference / Press** | `0.00 – 0.03 mm` | `0.00 – 0.06 mm` | Ball bearings (e.g. 608ZZ `Ø22.05 mm`), steel dowel pins, permanent friction assembly |
| **Transition / Snug** | `0.15 – 0.18 mm` | `0.30 – 0.36 mm` | Removable enclosure lids, friction-fit caps, modular dovetail joints |
| **Sliding / Locational** | `0.20 – 0.25 mm` | `0.40 – 0.50 mm` | Sliding drawers, adjustable rails, telescoping sleeves |
| **Running / Loose** | `0.30 – 0.40 mm` | `0.60 – 0.80 mm` | Free-spinning shafts, hinges, pivot pins |
| **Print-in-Place Hinge** | `0.35 – 0.45 mm` | `0.70 – 0.90 mm` | Captive conical/cylindrical print-in-place joints and gears |

---

## 3. Material Properties & Snap-Fit Limits

| Material | Density ($\text{g/cm}^3$) | Typical Linear Shrinkage | Max Safe Snap-Fit Strain ($\varepsilon_{\max}$) | Min Recommended Structural Wall | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PLA / PLA+** | 1.24 | `0.20 – 0.30%` | `1.8%` (`0.018`) | `1.6 mm` | High stiffness, low creep limit under sustained deflection |
| **PETG** | 1.27 | `0.30 – 0.40%` | `3.2%` (`0.032`) | `1.6 mm` | Excellent for snap-fits, compliant clips, and outdoor enclosures |
| **ABS / ASA** | 1.05 | `0.60 – 0.80%` | `2.8%` (`0.028`) | `2.0 mm` | High heat resistance; use generous fillets to prevent thermal warp |
| **Nylon (PA12)** | 1.14 | `1.00 – 1.30%` | `4.5%` (`0.045`) | `1.6 mm` | Ideal for gears, living hinges, bushings, and high-wear parts |
| **6061 Aluminum** | 2.70 | `0.00%` | `0.4%` (`0.004`) | `1.5 mm` | Avoid deep narrow pockets (`depth > 4 × tool diameter`) |
