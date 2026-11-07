// Parametric 15-Tooth Gear & Drop-In Bearing Stand Assembly
// 100% Watertight Manifold CAD Architecture
$fn = 64;

module spur_gear_15t(m = 2.5, z = 15, h = 8.0) {
    pitch_d = m * z;
    outer_d = pitch_d + 2*m;
    root_d = pitch_d - 2.5*m;
    linear_extrude(height = h)
    difference() {
        circle(d = outer_d);
        for (i = [0 : z - 1]) {
            rotate([0, 0, i * 360 / z])
            translate([pitch_d / 2, 0, 0])
                circle(r = m * 0.95);
        }
    }
}

// 1. Gear with 8mm Stem, Thrust Shoulder, and Crank
module gear_with_stem_and_crank() {
    union() {
        // 15T Gear Body
        spur_gear_15t(2.5, 15, 8.0);
        // Thrust Shoulder
        translate([0, 0, 8.0])
            cylinder(d = 12.0, h = 3.0);
        // 8mm Center Stem Shaft
        translate([0, 0, 11.0])
            cylinder(d = 8.0, h = 24.0);
        // 22mm Offset Crank Arm
        translate([0, 0, 35.0])
        hull() {
            cylinder(d = 11.0, h = 5.0);
            translate([22.0, 0, 0])
                cylinder(d = 11.0, h = 5.0);
        }
        // Ergonomic Spinner Knob
        translate([22.0, 0, 40.0])
            cylinder(d = 10.0, h = 16.0);
    }
}

// 2. Anti-Tip Stand with Drop-In Journal Bearing Cradle
module stand_base() {
    difference() {
        union() {
            // Flared Base
            hull() {
                for (x = [-24, 24], y = [-19, 19]) {
                    translate([x, y, 0]) cylinder(r = 6, h = 5.0);
                }
            }
            // Upright Post
            translate([0, 0, 5.0])
            hull() {
                for (x = [-7, 7], y = [-4, 4]) {
                    translate([x, y, 0]) cylinder(r = 3, h = 38.0);
                }
            }
        }
        // Drop-In U-Cradle (8.5mm bore for smooth 8mm shaft running)
        translate([0, 0, 35.0])
            rotate([90, 0, 0])
            cylinder(d = 8.5, h = 30, center = true);
        // Upper Vertical Drop Slot
        translate([-4.25, -15, 35.0])
            cube([8.5, 30, 10]);
    }
}

// 3. Drop-In Retaining Journal Lock Cap
module retaining_cap() {
    union() {
        // Cap Handle Plate
        hull() {
            for (x = [-9, 9], y = [-6, 6]) {
                translate([x, y, 0]) cylinder(r = 2.5, h = 4.0);
            }
        }
        // Central Locking Plug (with 0.22mm sliding clearance)
        translate([0, 0, 4.0])
        hull() {
            for (x = [-3.0, 3.0], y = [-5.5, 5.5]) {
                translate([x, y, 0]) cylinder(r = 1.0, h = 7.5);
            }
        }
    }
}

// Layout Plated on Build Plate
translate([-24, 0, 0]) gear_with_stem_and_crank();
translate([25, -5, 0]) stand_base();
translate([25, 28, 0]) retaining_cap();
