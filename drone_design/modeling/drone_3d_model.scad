// =============================================================================
// Plant-Watering Drone — DE10-Nano — Parametric 3D Model
// =============================================================================
// All dimensions in millimeters. X-configuration quadcopter.
// Render: OpenSCAD → F5 (preview) or F6 (full render)
// Export: File → Export as STL for 3D viewer / slicer
// =============================================================================

// ─── Global Parameters ───────────────────────────────────────────────────────

// Frame
plate_size       = 120;        // Bottom/top plate square dimension
plate_corner_r   = 2;          // Corner radius
bottom_thick     = 2.0;        // Bottom plate FR4 thickness
top_thick        = 1.6;        // Top plate FR4 thickness
arm_width        = 25;         // Arm PCB width
arm_length       = 220;        // Arm PCB total length
arm_thick        = 1.6;        // Arm PCB thickness
arm_tab          = 40;         // Inner tab length (inside plates)
motor_section    = 40;         // Outer motor mount section
plate_spacing    = 20;         // Vertical gap between bottom and top plates

// Landing gear
leg_width        = 20;
leg_height       = 80;         // Vertical portion
leg_thick        = 2.0;
foot_length      = 40;
foot_height      = 3;          // Foot thickness same as leg

// Motor
motor_diameter   = 28;         // 22xx class stator OD
motor_height     = 25;
motor_shaft_h    = 8;
prop_length      = 254;        // 10" prop = 254mm diameter
prop_width       = 18;
prop_thick       = 2;

// DE10-Nano
de10_w           = 68.6;
de10_l           = 107;
de10_h           = 1.6;        // PCB thickness
de10_standoff_h  = 15;         // Standoff height from bottom plate

// Daughter board
db_w             = 85;
db_l             = 100;
db_h             = 1.6;
db_offset_z      = 12;         // Above DE10-Nano top surface

// Battery
batt_w           = 35;
batt_l           = 105;
batt_h           = 27;

// Reservoir
res_w            = 50;
res_l            = 80;
res_h            = 40;

// Pump
pump_d           = 28;         // Pump body diameter
pump_l           = 50;         // Pump body length
pump_bracket_w   = 25;
pump_bracket_h   = 40;
pump_bracket_t   = 1.6;

// ESC
esc_w            = 17;
esc_l            = 31;
esc_h            = 5;

// ToF sensor
tof_w            = 12;
tof_l            = 15;
tof_h            = 1.0;
tof_sensor_h     = 2.5;       // Sensor module height

// ─── Derived ─────────────────────────────────────────────────────────────────

arm_overhang     = (arm_length - arm_tab) / 2 + arm_tab/2; // From center
motor_to_motor   = 2 * arm_overhang * cos(45) * 2;         // Diagonal

// Height references (Z=0 at ground level)
ground_z         = 0;
foot_z           = ground_z;
leg_top_z        = foot_z + foot_height + leg_height;
bottom_plate_z   = leg_top_z;
top_plate_z      = bottom_plate_z + plate_spacing;
de10_z           = bottom_plate_z + bottom_thick + de10_standoff_h;
db_z             = de10_z + de10_h + db_offset_z;

// ─── Colors ──────────────────────────────────────────────────────────────────

c_fr4_green      = [0.1, 0.45, 0.15, 0.85];
c_fr4_dark       = [0.08, 0.35, 0.12, 0.85];
c_copper         = [0.72, 0.45, 0.2, 0.9];
c_motor          = [0.2, 0.2, 0.2];
c_prop           = [0.15, 0.15, 0.15, 0.4];
c_de10           = [0.0, 0.3, 0.6, 0.9];
c_daughter       = [0.5, 0.1, 0.1, 0.9];
c_battery        = [0.15, 0.15, 0.15];
c_reservoir      = [0.3, 0.6, 0.9, 0.5];
c_pump           = [0.3, 0.3, 0.3];
c_esc            = [0.1, 0.1, 0.1];
c_tof            = [0.6, 0.1, 0.6, 0.9];
c_silver         = [0.75, 0.75, 0.78];

// ─── Utility Modules ─────────────────────────────────────────────────────────

module rounded_rect(w, l, h, r) {
    linear_extrude(h)
        offset(r=r)
            square([w - 2*r, l - 2*r], center=true);
}

// ─── Skeleton Plate ──────────────────────────────────────────────────────────
// Plate with arm slots and lightening cutouts

module skeleton_plate(thick, is_bottom=true) {
    slot_w = 1.7;
    slot_l = 40;
    rib_w  = 8;           // Structural rib width

    color(is_bottom ? c_copper : c_fr4_green)
    difference() {
        // Base plate
        rounded_rect(plate_size, plate_size, thick, plate_corner_r);

        // 4 arm slots at 45° diagonals
        for (angle = [45, 135, 225, 315]) {
            rotate([0, 0, angle])
                translate([0, 0, -0.5])
                    cube([slot_w, slot_l, thick + 1], center=true);
        }

        // Central cutout (top plate only — for DE10-Nano clearance)
        if (!is_bottom) {
            translate([0, 0, -0.5])
                rounded_rect(70, 110, thick + 1, 2);
        }

        // Lightening cutouts — 4 triangular zones between arm slots
        for (angle = [0, 90, 180, 270]) {
            rotate([0, 0, angle])
                translate([0, 42, -0.5])
                    rounded_rect(30, 18, thick + 1, 3);
        }

        // DE10-Nano mounting holes (bottom plate)
        if (is_bottom) {
            // Approximate mounting pattern
            for (dx = [-de10_w/2 + 4, de10_w/2 - 4])
                for (dy = [-de10_l/2 + 4, de10_l/2 - 4])
                    translate([dx, dy, -0.5])
                        cylinder(d=2.5, h=thick+1, $fn=16);
        }
    }
}

// ─── Arm (I-Beam skeleton profile) ──────────────────────────────────────────

module arm() {
    flange_w = 5;
    web_w    = 3;

    color(c_copper)
    translate([0, 0, -arm_thick/2])
    linear_extrude(arm_thick)
    difference() {
        // Arm outline
        square([arm_length, arm_width], center=true);

        // I-beam cutouts: remove material between flanges and web
        for (side = [-1, 1]) {
            translate([0, side * (flange_w/2 + (arm_width/2 - flange_w - web_w/2)/2)])
                square([arm_length - arm_tab*2 - 20, arm_width/2 - flange_w - web_w/2], center=true);
        }

        // Motor mount holes (4× M3 at outer end)
        for (end = [1]) {
            for (dx = [-8, 8])
                for (dy = [-9.5, 9.5])
                    translate([arm_length/2 - motor_section/2 + dx, dy])
                        circle(d=3.2, $fn=16);
        }
    }
}

// ─── Motor ───────────────────────────────────────────────────────────────────

module motor() {
    color(c_motor) {
        // Motor bell
        cylinder(d=motor_diameter, h=motor_height, $fn=32);
        // Shaft
        translate([0, 0, motor_height])
            cylinder(d=5, h=motor_shaft_h, $fn=16);
    }
}

// ─── Propeller ───────────────────────────────────────────────────────────────

module propeller() {
    color(c_prop)
    hull() {
        translate([-prop_length/2, 0, 0])
            cylinder(d=prop_width*0.4, h=prop_thick, $fn=16);
        cylinder(d=prop_width, h=prop_thick, $fn=16);
        translate([prop_length/2, 0, 0])
            cylinder(d=prop_width*0.4, h=prop_thick, $fn=16);
    }
}

// ─── Landing Gear Leg ────────────────────────────────────────────────────────

module landing_leg() {
    color(c_fr4_dark) {
        // Vertical section
        translate([-leg_width/2, 0, foot_height])
            cube([leg_width, leg_thick, leg_height]);

        // Foot (horizontal)
        translate([-leg_width/2, 0, 0])
            cube([leg_width, foot_length, foot_height]);

        // Lightening holes in vertical section (aesthetic)
        // (shown as solid for simplicity — skeleton cuts done in real PCB)
    }
}

// ─── ESC ─────────────────────────────────────────────────────────────────────

module esc() {
    color(c_esc)
        cube([esc_l, esc_w, esc_h], center=true);
}

// ─── ToF Sensor Board ────────────────────────────────────────────────────────

module tof_board() {
    // PCB
    color(c_tof)
        cube([tof_w, tof_l, tof_h], center=true);
    // Sensor module on front face
    color([0.2, 0.2, 0.2])
        translate([0, 0, tof_h/2])
            cube([4, 4, tof_sensor_h], center=true);
}

// ─── DE10-Nano Board ─────────────────────────────────────────────────────────

module de10_nano() {
    color(c_de10)
        rounded_rect(de10_w, de10_l, de10_h, 1);

    // Heatsink representation
    color(c_silver)
        translate([0, -10, de10_h])
            cube([40, 40, 8], center=true);

    // GPIO headers (2x20 pin blocks)
    color([0.15, 0.15, 0.15])
    for (dx = [-de10_w/2 + 8, de10_w/2 - 8])
        translate([dx, 0, de10_h])
            cube([5, 51, 8.5], center=true);
}

// ─── Daughter Board ──────────────────────────────────────────────────────────

module daughter_board() {
    color(c_daughter)
        rounded_rect(db_w, db_l, db_h, 1);

    // Component representations (ICs, mux, etc.)
    color([0.15, 0.15, 0.15])
    for (pos = [[0, 20, db_h], [-15, -15, db_h], [15, -15, db_h]])
        translate(pos)
            cube([8, 8, 2], center=true);
}

// ─── Battery ─────────────────────────────────────────────────────────────────

module battery() {
    color(c_battery)
        rounded_rect(batt_w, batt_l, batt_h, 3);
    // XT60 pigtail
    color([1, 0.8, 0])
        translate([0, batt_l/2, batt_h/2])
            rotate([90, 0, 0])
                cylinder(d=8, h=12, $fn=8);
}

// ─── Water Reservoir ─────────────────────────────────────────────────────────

module reservoir() {
    color(c_reservoir)
        rounded_rect(res_w, res_l, res_h, 5);
}

// ─── Pump ────────────────────────────────────────────────────────────────────

module pump_assembly() {
    // Bracket
    color(c_fr4_green)
        translate([0, 0, 0])
            cube([pump_bracket_w, pump_bracket_t, pump_bracket_h], center=true);

    // Pump body (cylinder)
    color(c_pump)
        translate([0, -pump_d/2 - pump_bracket_t/2, 0])
            rotate([0, 90, 0])
                cylinder(d=pump_d, h=pump_l, center=true, $fn=24);
}

// ─── Tubing ──────────────────────────────────────────────────────────────────

module tubing_run() {
    color([0.8, 0.8, 0.85, 0.6]) {
        // Vertical drop from reservoir to pump
        translate([30, -45, bottom_plate_z - 30])
            cylinder(d=5, h=25, $fn=12);
        // From pump down to nozzle
        translate([30, -55, bottom_plate_z - 55])
            cylinder(d=5, h=20, $fn=12);
    }
}

// ─── Standoff ────────────────────────────────────────────────────────────────

module standoff(h) {
    color(c_silver) {
        cylinder(d=5, h=h, $fn=6);
    }
}

// ─── Nozzle ──────────────────────────────────────────────────────────────────

module drip_nozzle() {
    color([0.4, 0.4, 0.4]) {
        cylinder(d1=8, d2=3, h=15, $fn=16);
        translate([0, 0, -2])
            cylinder(d=5, h=2, $fn=12);
    }
}

// =============================================================================
// ASSEMBLY
// =============================================================================

module drone_assembly() {

    // ── Bottom Plate ──
    translate([0, 0, bottom_plate_z])
        skeleton_plate(bottom_thick, is_bottom=true);

    // ── Top Plate ──
    translate([0, 0, top_plate_z])
        skeleton_plate(top_thick, is_bottom=false);

    // ── 4 Arms (X-config at 45° diagonals) ──
    arm_center_z = bottom_plate_z + bottom_thick/2 + (plate_spacing)/2;
    for (angle = [45, 135, 225, 315]) {
        rotate([0, 0, angle])
            translate([arm_length/2 - arm_tab/2, 0, arm_center_z])
                rotate([90, 0, 0])
                    rotate([0, 0, 0])
                        arm();
    }

    // ── Motors + Props + ESCs ──
    motor_r = (arm_length - arm_tab/2);  // Distance from center to motor
    for (i = [0:3]) {
        angle = 45 + i * 90;
        // Motor position
        mx = motor_r * cos(angle) * 0.5;
        my = motor_r * sin(angle) * 0.5;

        // Motor
        translate([mx, my, top_plate_z + top_thick])
            motor();

        // Propeller
        translate([mx, my, top_plate_z + top_thick + motor_height + motor_shaft_h])
            rotate([0, 0, angle + 30])
                propeller();

        // ESC (on arm underside, near center)
        esc_r = 60; // ESC position along arm
        ex = esc_r * cos(angle);
        ey = esc_r * sin(angle);
        translate([ex, ey, bottom_plate_z - esc_h/2 - 1])
            rotate([0, 0, angle])
                esc();
    }

    // ── Landing Gear (4 legs at plate corners/edges) ──
    for (i = [0:3]) {
        angle = i * 90;  // Legs at 0°, 90°, 180°, 270° (between arms)
        lx = (plate_size/2 + 2) * cos(angle);
        ly = (plate_size/2 + 2) * sin(angle);

        translate([lx, ly, ground_z])
            rotate([0, 0, angle])
                translate([0, -leg_thick/2, 0])
                    landing_leg();
    }

    // ── DE10-Nano ──
    translate([0, 0, de10_z])
        de10_nano();

    // Standoffs
    for (dx = [-de10_w/2 + 4, de10_w/2 - 4])
        for (dy = [-de10_l/2 + 4, de10_l/2 - 4])
            translate([dx, dy, bottom_plate_z + bottom_thick])
                standoff(de10_standoff_h);

    // ── Daughter Board ──
    translate([0, 0, db_z])
        daughter_board();

    // ── Battery (below bottom plate) ──
    translate([0, 0, bottom_plate_z - batt_h - 5])
        battery();

    // ── Water Reservoir (between/below plates) ──
    translate([0, 30, bottom_plate_z - res_h - 3])
        reservoir();

    // ── Pump Assembly (soldered to plate edge) ──
    translate([0, -(plate_size/2 + pump_bracket_t/2), bottom_plate_z - pump_bracket_h/2])
        pump_assembly();

    // ── Drip Nozzle ──
    translate([0, -(plate_size/2 + 20), bottom_plate_z - pump_bracket_h - 10])
        drip_nozzle();

    // ── Tubing ──
    tubing_run();

    // ── ToF Sensors (6 directions) ──

    // Down — center of bottom plate, facing ground
    translate([0, 0, bottom_plate_z - tof_sensor_h - 2])
        rotate([180, 0, 0])
            tof_board();

    // Up — center of top plate, facing ceiling
    translate([0, 0, top_plate_z + top_thick + 2])
        tof_board();

    // Front — top plate front edge
    translate([0, plate_size/2, top_plate_z + top_thick/2 + tof_l/2])
        rotate([90, 0, 0])
            rotate([0, 0, 90])
                tof_board();

    // Back — top plate rear edge
    translate([0, -plate_size/2, top_plate_z + top_thick/2 + tof_l/2])
        rotate([-90, 0, 0])
            rotate([0, 0, 90])
                tof_board();

    // Left — top plate left edge
    translate([-plate_size/2, 0, top_plate_z + top_thick/2 + tof_l/2])
        rotate([0, -90, 90])
            tof_board();

    // Right — top plate right edge
    translate([plate_size/2, 0, top_plate_z + top_thick/2 + tof_l/2])
        rotate([0, 90, -90])
            tof_board();
}

// ─── Render ──────────────────────────────────────────────────────────────────

drone_assembly();

// ─── Info Echo ───────────────────────────────────────────────────────────────

echo(str("Motor-to-motor diagonal (approx): ",
    2 * (arm_length - arm_tab/2) * 0.5 * sqrt(2), " mm"));
echo(str("Bottom plate Z: ", bottom_plate_z, " mm"));
echo(str("Top plate Z: ", top_plate_z, " mm"));
echo(str("Total height (ground to prop tip): ",
    top_plate_z + top_thick + motor_height + motor_shaft_h + prop_thick, " mm"));
