// 100% Zero-Support Parametric Gear & Stand Assembly
// Overhang Ratio: 0.00% across all parts
$fn = 64;

// 1. Gear with 8mm Shaft and Hex Drive Key (Prints flat on gear face, 0% overhang)
module gear_and_shaft() {
    m = 2.5; z = 15; pitch_d = m * z; outer_d = pitch_d + 2*m;
    union() {
        // 15T Gear Body
        linear_extrude(height = 8.0)
        difference() {
            circle(d = outer_d);
            for (i = [0 : z - 1]) {
                rotate([0, 0, i * 360 / z])
                translate([pitch_d / 2, 0, 0]) circle(r = m * 0.95);
            }
        }
        // Thrust Shoulder
        translate([0, 0, 8.0]) cylinder(d = 12.0, h = 3.0);
        // 8mm Center Shaft (Journal)
        translate([0, 0, 11.0]) cylinder(d = 8.0, h = 16.0);
        // 6mm Hex Drive Interlock Tip
        translate([0, 0, 27.0])
        rotate([0, 0, 30])
        cylinder(r = 6.0 / (2 * cos(30)), h = 6.0, $fn = 6);
    }
}

// 2. Crank Arm with Matching Hex Socket (Prints flat on arm face, 0% overhang)
module crank_arm_and_knob() {
    union() {
        difference() {
            // Flat Arm Body
            hull() {
                cylinder(d = 12.0, h = 5.0);
                translate([22.0, 0, 0]) cylinder(d = 12.0, h = 5.0);
            }
            // 6.36mm Hex Socket (0.18mm clearance for positive press-fit)
            translate([0, 0, -1])
            rotate([0, 0, 30])
            cylinder(r = 6.36 / (2 * cos(30)), h = 7.0, $fn = 6);
        }
        // Vertical Ergonomic Spinner Knob
        translate([22.0, 0, 5.0]) cylinder(d = 10.0, h = 16.0);
    }
}

// 3. Anti-Tip Stand with Drop-In U-Cradle (0% overhang)
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
            cube([20.0, 14.0, 38.0], center = true);
        }
        // Central U-Cradle Channel (8.5mm wide for 8.0mm stem)
        translate([-4.25, -8.0, 35.0])
            cube([8.5, 16.0, 10.0]);
    }
}

// 4. Drop-In Retaining Journal Lock Cap (0% overhang)
module retaining_cap() {
    union() {
        // Cap Plate
        hull() {
            for (x = [-9, 9], y = [-6, 6]) {
                translate([x, y, 0]) cylinder(r = 2.5, h = 4.0);
            }
        }
        // Central Locking Plug
        translate([0, 0, 4.0])
        hull() {
            for (x = [-3.0, 3.0], y = [-5.5, 5.5]) {
                translate([x, y, 0]) cylinder(r = 1.0, h = 7.5);
            }
        }
    }
}

// Plated Layout for 1-Click Print
translate([-25, 0, 0]) gear_and_shaft();
translate([25, -5, 0]) stand_base();
translate([-25, 32, 0]) crank_arm_and_knob();
translate([25, 32, 0]) retaining_cap();
