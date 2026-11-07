"""
analog_mosfet_solver.py - Bidirectional Analog MOSFET Circuit & Problem Solver.
EDA Studio Module for continuous analog microelectronics, DC biasing, AC small-signal analysis,
dynamic Given vs To-Find numerical solving, and educational step-by-step problem derivations.
"""
import math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QComboBox,
    QCheckBox, QWidget, QGroupBox, QFrame, QGridLayout,
    QScrollArea, QTextBrowser, QApplication, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor


class BidirectionalMosfetEngine:
    """
    Mathematical and microelectronics derivation engine for bidirectional
    solving of MOSFET analog circuits.
    """

    @staticmethod
    def solve(given_dict, target_keys, topo_type="Common Source (CS) Amplifier",
              is_nmos=True, bypassed=True):
        """
        Solves the circuit for the requested target_keys given the known values.
        Returns:
            solution_dict: computed values for all parameters
            steps_html: formatted educational step-by-step derivation
            plain_steps: plain text version for copying
            mode: 'Saturation', 'Triode', or 'Cutoff'
            sat_ok: boolean
        """
        vals = dict(given_dict)
        steps = []
        raw_steps = []

        def add_step(title, html_body, plain_body):
            steps.append(f"""
            <div style="margin-bottom: 12px;">
                <div style="font-weight: bold; color: #58a6ff; font-size: 11pt; margin-bottom: 4px;">{title}</div>
                <div style="background: #161b22; border-left: 3px solid #58a6ff; padding: 8px 12px; border-radius: 4px; font-family: Consolas, monospace; font-size: 10pt; line-height: 1.5; color: #c9d1d9;">
                    {html_body}
                </div>
            </div>
            """)
            raw_steps.append(f"=== {title} ===\n{plain_body}\n")

        # Step 0: Identify Knowns and Targets
        given_str = ", ".join([f"{k} = {vals[k]:.3g}" for k in sorted(vals.keys())])
        target_str = ", ".join(sorted(list(target_keys)))
        add_step(
            "Step 0: Problem Identification & Variable Roles",
            f"<b>Selected Topology:</b> {topo_type} ({'NMOS' if is_nmos else 'PMOS'})<br>"
            f"<b>Given Inputs ({len(vals)}):</b> {given_str}<br>"
            f"<b>Requested Targets ({len(target_keys)}):</b> {target_str}",
            f"Topology: {topo_type} ({'NMOS' if is_nmos else 'PMOS'})\nGiven: {given_str}\nTargets: {target_str}"
        )

        lam = vals.get('LAM', 0.0)

        # Topology specific terminal conditions
        if "Common Drain" in topo_type:
            if 'VDD' in vals and 'VD' not in vals:
                vals['VD'] = vals['VDD']
            if 'RD' not in vals:
                vals['RD'] = 0.0

        # Iterative propagation passes
        for _ in range(10):
            # 1. Gate Bias Divider
            if 'VDD' in vals and 'R1' in vals and 'R2' in vals and 'VG' not in vals:
                r1 = vals['R1']
                r2 = vals['R2']
                vdd = vals['VDD']
                if r1 + r2 > 0:
                    vg = vdd * (r2 / (r1 + r2))
                    vals['VG'] = vg
                    vals['Rin'] = (r1 * r2) / (r1 + r2)
                    add_step(
                        "Gate Divider Analysis (Thevenin Equivalent)",
                        f"V_G = V_DD &times; [ R_2 / (R_1 + R_2) ]<br>"
                        f"V_G = {vdd:.2f} &times; [ {r2:.2f} / ({r1:.2f} + {r2:.2f}) ] = <b>{vg:.3f} V</b><br>"
                        f"R_in = R_1 || R_2 = <b>{vals['Rin']:.2f} kΩ</b>",
                        f"VG = VDD * R2 / (R1 + R2) = {vg:.3f} V, Rin = {vals['Rin']:.2f} kOhm"
                    )

            # Reverse Gate Divider: Solve R2 or R1
            if 'VDD' in vals and 'VG' in vals:
                vdd = vals['VDD']
                vg = vals['VG']
                if 'R1' in vals and 'R2' not in vals:
                    r1 = vals['R1']
                    if vdd > vg > 0:
                        r2 = (vg * r1) / (vdd - vg)
                        vals['R2'] = r2
                        vals['Rin'] = (r1 * r2) / (r1 + r2)
                        add_step(
                            "Reverse Gate Divider: Solve R_2",
                            f"R_2 = (V_G &times; R_1) / (V_DD - V_G)<br>"
                            f"R_2 = ({vg:.3f} &times; {r1:.2f}) / ({vdd:.2f} - {vg:.3f}) = <b>{r2:.2f} kΩ</b>",
                            f"R2 = (VG * R1) / (VDD - VG) = {r2:.2f} kOhm"
                        )
                elif 'R2' in vals and 'R1' not in vals:
                    r2 = vals['R2']
                    if vg > 0 and vdd > vg:
                        r1 = r2 * (vdd - vg) / vg
                        vals['R1'] = r1
                        vals['Rin'] = (r1 * r2) / (r1 + r2)
                        add_step(
                            "Reverse Gate Divider: Solve R_1",
                            f"R_1 = R_2 &times; (V_DD - V_G) / V_G<br>"
                            f"R_1 = {r2:.2f} &times; ({vdd:.2f} - {vg:.3f}) / {vg:.3f} = <b>{r1:.2f} kΩ</b>",
                            f"R1 = R2 * (VDD - VG) / VG = {r1:.2f} kOhm"
                        )

            # 2. Overdrive and VGS / VTH
            if 'VGS' in vals and 'VTH' in vals and 'VOV' not in vals:
                vov = vals['VGS'] - vals['VTH']
                vals['VOV'] = vov
                add_step(
                    "Overdrive Voltage (V_OV)",
                    f"V_OV = V_GS - V_TH = {vals['VGS']:.3f} - {vals['VTH']:.3f} = <b>{vov:.3f} V</b>",
                    f"VOV = VGS - VTH = {vov:.3f} V"
                )
            if 'VOV' in vals and 'VTH' in vals and 'VGS' not in vals:
                vgs = vals['VTH'] + vals['VOV']
                vals['VGS'] = vgs
                add_step(
                    "Gate-Source Voltage from Overdrive",
                    f"V_GS = V_TH + V_OV = {vals['VTH']:.3f} + {vals['VOV']:.3f} = <b>{vgs:.3f} V</b>",
                    f"VGS = VTH + VOV = {vgs:.3f} V"
                )
            if 'VGS' in vals and 'VOV' in vals and 'VTH' not in vals:
                vth = vals['VGS'] - vals['VOV']
                vals['VTH'] = vth
                add_step(
                    "Threshold Voltage Extraction",
                    f"V_TH = V_GS - V_OV = {vals['VGS']:.3f} - {vals['VOV']:.3f} = <b>{vth:.3f} V</b>",
                    f"VTH = VGS - VOV = {vth:.3f} V"
                )

            # 3. Transconductance gm and ID relations
            if 'Kn' in vals and 'VOV' in vals:
                kn = vals['Kn']
                vov = vals['VOV']
                if 'gm' not in vals:
                    gm = 2.0 * kn * vov
                    vals['gm'] = gm
                    add_step(
                        "Transconductance (g_m)",
                        f"g_m = 2 &times; K_n &times; V_OV = 2 &times; {kn:.3f} &times; {vov:.3f} = <b>{gm:.3f} mS</b>",
                        f"gm = 2 * Kn * VOV = {gm:.3f} mS"
                    )
                if 'ID' not in vals and vov > 0:
                    id_ma = kn * (vov ** 2)
                    vals['ID'] = id_ma
                    add_step(
                        "Drain Current (Saturation Law)",
                        f"I_D = K_n &times; (V_OV)&sup2; = {kn:.3f} &times; ({vov:.3f})&sup2; = <b>{id_ma:.3f} mA</b>",
                        f"ID = Kn * (VOV^2) = {id_ma:.3f} mA"
                    )

            if 'ID' in vals and 'Kn' in vals and 'VOV' not in vals:
                kn = vals['Kn']
                id_ma = vals['ID']
                if kn > 0 and id_ma >= 0:
                    vov = math.sqrt(id_ma / kn)
                    vals['VOV'] = vov
                    add_step(
                        "Overdrive Voltage from Drain Current",
                        f"V_OV = &radic;(I_D / K_n) = &radic;({id_ma:.3f} / {kn:.3f}) = <b>{vov:.3f} V</b>",
                        f"VOV = sqrt(ID / Kn) = {vov:.3f} V"
                    )

            if 'ID' in vals and 'VOV' in vals and 'Kn' not in vals:
                id_ma = vals['ID']
                vov = vals['VOV']
                if vov > 0:
                    kn = id_ma / (vov ** 2)
                    vals['Kn'] = kn
                    add_step(
                        "Conduction Parameter Extraction (K_n)",
                        f"K_n = I_D / (V_OV)&sup2; = {id_ma:.3f} / ({vov:.3f})&sup2; = <b>{kn:.3f} mA/V&sup2;</b>",
                        f"Kn = ID / (VOV^2) = {kn:.3f} mA/V^2"
                    )

            if 'gm' in vals and 'ID' in vals:
                if 'VOV' not in vals and vals['gm'] > 0:
                    vov = (2.0 * vals['ID']) / vals['gm']
                    vals['VOV'] = vov
                    add_step(
                        "Overdrive from g_m and I_D",
                        f"V_OV = (2 &times; I_D) / g_m = (2 &times; {vals['ID']:.3f}) / {vals['gm']:.3f} = <b>{vov:.3f} V</b>",
                        f"VOV = 2*ID / gm = {vov:.3f} V"
                    )
                if 'Kn' not in vals and vals['ID'] > 0:
                    kn = (vals['gm'] ** 2) / (4.0 * vals['ID'])
                    vals['Kn'] = kn
                    add_step(
                        "K_n from g_m and I_D",
                        f"K_n = (g_m)&sup2; / (4 &times; I_D) = ({vals['gm']:.3f})&sup2; / (4 &times; {vals['ID']:.3f}) = <b>{kn:.3f} mA/V&sup2;</b>",
                        f"Kn = gm^2 / (4*ID) = {kn:.3f} mA/V^2"
                    )

            # 4. Terminal Potentials (VG, VS, VD, VGS, VDS)
            if 'VG' in vals and 'VGS' in vals and 'VS' not in vals:
                vs = vals['VG'] - vals['VGS'] if is_nmos else vals['VG'] + vals['VGS']
                vals['VS'] = vs
                add_step(
                    "Source Potential (V_S)",
                    f"V_S = V_G - V_GS = {vals['VG']:.3f} - {vals['VGS']:.3f} = <b>{vs:.3f} V</b>",
                    f"VS = VG - VGS = {vs:.3f} V"
                )

            if 'VG' in vals and 'VS' in vals and 'VGS' not in vals:
                vgs = vals['VG'] - vals['VS'] if is_nmos else vals['VS'] - vals['VG']
                vals['VGS'] = vgs
                add_step(
                    "Gate-Source Potential (V_GS)",
                    f"V_GS = V_G - V_S = {vals['VG']:.3f} - {vals['VS']:.3f} = <b>{vgs:.3f} V</b>",
                    f"VGS = VG - VS = {vgs:.3f} V"
                )

            if 'VS' in vals and 'VGS' in vals and 'VG' not in vals:
                vg = vals['VS'] + vals['VGS'] if is_nmos else vals['VS'] - vals['VGS']
                vals['VG'] = vg
                add_step(
                    "Gate Potential (V_G)",
                    f"V_G = V_S + V_GS = {vals['VS']:.3f} + {vals['VGS']:.3f} = <b>{vg:.3f} V</b>",
                    f"VG = VS + VGS = {vg:.3f} V"
                )

            # Source Resistor relations
            if 'VS' in vals and 'ID' in vals and vals['ID'] > 0 and 'RS' not in vals:
                rs = vals['VS'] / vals['ID']
                vals['RS'] = rs
                add_step(
                    "Source Resistor Sizing (R_S)",
                    f"R_S = V_S / I_D = {vals['VS']:.3f} V / {vals['ID']:.3f} mA = <b>{rs:.3f} kΩ</b>",
                    f"RS = VS / ID = {rs:.3f} kOhm"
                )

            if 'RS' in vals and 'ID' in vals and 'VS' not in vals:
                vs = vals['ID'] * vals['RS']
                vals['VS'] = vs
                add_step(
                    "Source Voltage Drop (V_S)",
                    f"V_S = I_D &times; R_S = {vals['ID']:.3f} mA &times; {vals['RS']:.3f} kΩ = <b>{vs:.3f} V</b>",
                    f"VS = ID * RS = {vs:.3f} V"
                )

            # Drain Resistor relations
            if 'VDD' in vals and 'VD' in vals and 'ID' in vals and vals['ID'] > 0 and 'RD' not in vals:
                rd = (vals['VDD'] - vals['VD']) / vals['ID'] if is_nmos else (vals['VD'] - 0.0) / vals['ID']
                vals['RD'] = max(0.0, rd)
                add_step(
                    "Drain Resistor Sizing (R_D)",
                    f"R_D = (V_DD - V_D) / I_D = ({vals['VDD']:.2f} - {vals['VD']:.3f}) / {vals['ID']:.3f} = <b>{vals['RD']:.3f} kΩ</b>",
                    f"RD = (VDD - VD) / ID = {vals['RD']:.3f} kOhm"
                )

            if 'VDD' in vals and 'RD' in vals and 'ID' in vals and 'VD' not in vals:
                vd = vals['VDD'] - vals['ID'] * vals['RD'] if is_nmos else vals['ID'] * vals['RD']
                vals['VD'] = vd
                add_step(
                    "Drain Potential (V_D)",
                    f"V_D = V_DD - (I_D &times; R_D) = {vals['VDD']:.2f} - ({vals['ID']:.3f} &times; {vals['RD']:.3f}) = <b>{vd:.3f} V</b>",
                    f"VD = VDD - ID * RD = {vd:.3f} V"
                )

            if 'VD' in vals and 'VS' in vals and 'VDS' not in vals:
                vds = vals['VD'] - vals['VS'] if is_nmos else vals['VS'] - vals['VD']
                vals['VDS'] = vds
                add_step(
                    "Drain-Source Voltage (V_DS)",
                    f"V_DS = V_D - V_S = {vals['VD']:.3f} - {vals['VS']:.3f} = <b>{vds:.3f} V</b>",
                    f"VDS = VD - VS = {vds:.3f} V"
                )

            if 'VS' in vals and 'VDS' in vals and 'VD' not in vals:
                vd = vals['VS'] + vals['VDS'] if is_nmos else vals['VS'] - vals['VDS']
                vals['VD'] = vd
                add_step(
                    "Drain Voltage from V_DS and V_S",
                    f"V_D = V_S + V_DS = {vals['VS']:.3f} + {vals['VDS']:.3f} = <b>{vd:.3f} V</b>",
                    f"VD = VS + VDS = {vd:.3f} V"
                )

            # 5. Coupled Self-Bias Quadratic (Four-Resistor CS)
            if ('ID' not in vals or 'VGS' not in vals) and 'VG' in vals and 'VTH' in vals and 'Kn' in vals and 'RS' in vals:
                vg = vals['VG']
                vth = vals['VTH']
                kn = vals['Kn']
                rs = vals['RS']

                v_diff = vg - vth
                if rs > 0 and kn > 0:
                    a = kn * rs
                    b = 1.0
                    c = -v_diff
                    disc = b ** 2 - 4.0 * a * c
                    if disc >= 0:
                        x1 = (-b + math.sqrt(disc)) / (2.0 * a)
                        x2 = (-b - math.sqrt(disc)) / (2.0 * a)
                        x_sol = max(x1, x2)
                        vals['VOV'] = x_sol
                        vals['VGS'] = vth + x_sol
                        vals['ID'] = kn * (x_sol ** 2)
                        vals['VS'] = vals['ID'] * rs
                        add_step(
                            "Quadratic Formulation for Self-Biased Overdrive",
                            f"Input loop: V_GS = V_G - I_D &times; R_S = V_G - K_n &times; (V_GS - V_TH)&sup2; &times; R_S<br>"
                            f"Let x = V_OV: &nbsp;&nbsp;<b>({kn:.3f} &times; {rs:.2f}) x&sup2; + x - ({v_diff:.3f}) = 0</b><br>"
                            f"Roots: x_1 = {x1:.3f} V, x_2 = {x2:.3f} V<br>"
                            f"Physical root (V_OV &ge; 0): <b>V_OV = {x_sol:.3f} V</b><br>"
                            f"&rarr; V_GS = {vals['VGS']:.3f} V, &nbsp; I_D = <b>{vals['ID']:.3f} mA</b>",
                            f"Quadratic: a={a:.3f}, b=1, c={c:.3f}. Physical V_OV = {x_sol:.3f} V, ID = {vals['ID']:.3f} mA"
                        )

            # 6. Small-Signal Output Resistance ro
            if 'ID' in vals and 'ro' not in vals:
                id_ma = vals['ID']
                if lam > 0 and id_ma > 0:
                    ro = 1.0 / (lam * id_ma)
                    vals['ro'] = ro
                    add_step(
                        "Small-Signal Output Resistance (r_o)",
                        f"r_o = 1 / (&lambda; &times; I_D) = 1 / ({lam:.3f} &times; {id_ma:.3f}) = <b>{ro:.2f} kΩ</b>",
                        f"ro = 1 / (lam * ID) = {ro:.2f} kOhm"
                    )
                else:
                    vals['ro'] = 999999.0

            # 7. Small-Signal Voltage Gain Av
            ro_val = vals.get('ro', 999999.0)
            if 'Av' not in vals and 'gm' in vals:
                gm = vals['gm']
                if "Common Drain" in topo_type:
                    rs = vals.get('RS', 1.0)
                    r_eff = (rs * ro_val) / (rs + ro_val) if ro_val < 100000 else rs
                    av = (gm * r_eff) / (1.0 + gm * r_eff)
                    vals['Av'] = av
                    vals['Rout'] = 1.0 / ((1.0 / rs) + gm + (1.0 / ro_val if ro_val < 100000 else 0.0))
                    add_step(
                        "Common Drain (Source Follower) Gain & Output Impedance",
                        f"A_v = [ g_m &times; (R_S || r_o) ] / [ 1 + g_m &times; (R_S || r_o) ] = <b>+{av:.3f} V/V</b><br>"
                        f"R_out = R_S || (1/g_m) || r_o = <b>{vals['Rout']:.2f} kΩ</b>",
                        f"Av = +{av:.3f} V/V, Rout = {vals['Rout']:.2f} kOhm"
                    )
                elif "Common Gate" in topo_type:
                    rd = vals.get('RD', 2.0)
                    rs = vals.get('RS', 1.0)
                    r_eff = (rd * ro_val) / (rd + ro_val) if ro_val < 100000 else rd
                    av = gm * r_eff
                    vals['Av'] = av
                    vals['Rin'] = 1.0 / gm
                    vals['Rout'] = r_eff
                    add_step(
                        "Common Gate Gain & Input Impedance",
                        f"A_v = +g_m &times; (R_D || r_o) = +{gm:.3f} &times; {r_eff:.2f} = <b>+{av:.2f} V/V</b><br>"
                        f"R_in &approx; 1/g_m = <b>{vals['Rin']:.2f} kΩ</b>, &nbsp; R_out = <b>{vals['Rout']:.2f} kΩ</b>",
                        f"Av = +{av:.2f} V/V, Rin = {vals['Rin']:.2f} kOhm, Rout = {vals['Rout']:.2f} kOhm"
                    )
                else:  # Common Source
                    rd = vals.get('RD', 2.0)
                    rs = vals.get('RS', 1.0)
                    r_eff = (rd * ro_val) / (rd + ro_val) if ro_val < 100000 else rd
                    if bypassed:
                        av = -gm * r_eff
                        add_step(
                            "Common Source Voltage Gain (Bypassed C_S)",
                            f"A_v = -g_m &times; (R_D || r_o) = -{gm:.3f} &times; {r_eff:.2f} = <b>{av:.2f} V/V</b><br>"
                            f"R_out = R_D || r_o = <b>{r_eff:.2f} kΩ</b>",
                            f"Av = -gm * (RD || ro) = {av:.2f} V/V, Rout = {r_eff:.2f} kOhm"
                        )
                    else:
                        denom = 1.0 + gm * rs
                        av = (-gm * r_eff) / denom
                        add_step(
                            "Common Source Voltage Gain (Unbypassed R_S)",
                            f"A_v = [ -g_m &times; (R_D || r_o) ] / [ 1 + g_m &times; R_S ] = <b>{av:.2f} V/V</b>",
                            f"Av = -gm*r_eff / (1 + gm*RS) = {av:.2f} V/V"
                        )
                    vals['Av'] = av
                    vals['Rout'] = r_eff

            # 8. Design Mode Target Gain -> Solve RD
            if 'Av' in vals and 'RD' not in vals and 'gm' in vals:
                gm = vals['gm']
                target_av = abs(vals['Av'])
                if gm > 0:
                    r_eff = target_av / gm
                    if ro_val < 100000 and ro_val > r_eff:
                        rd = (r_eff * ro_val) / (ro_val - r_eff)
                    else:
                        rd = r_eff
                    vals['RD'] = rd
                    add_step(
                        "Design Sizing: Drain Resistor (R_D) from Target Gain",
                        f"Required R_D || r_o = |A_v| / g_m = {target_av:.2f} / {gm:.3f} = {r_eff:.2f} kΩ<br>"
                        f"<b>Calculated R_D = {rd:.2f} kΩ</b>",
                        f"RD = {rd:.2f} kOhm to achieve Av = {vals['Av']:.2f}"
                    )

            # 9. Divider Resistor Sizing (R1 & R2 when both unknown and VG, VDD known)
            if 'VDD' in vals and 'VG' in vals and 'R1' not in vals and 'R2' not in vals:
                vdd = vals['VDD']
                vg = vals['VG']
                if vdd > vg > 0:
                    r_tot = 150.0  # standard 150 kOhm total divider resistance
                    r2 = (vg / vdd) * r_tot
                    r1 = r_tot - r2
                    vals['R1'] = r1
                    vals['R2'] = r2
                    vals['Rin'] = (r1 * r2) / (r1 + r2)
                    add_step(
                        "Design Sizing: Gate Divider Network (R_1, R_2)",
                        f"Target input divider R_total = 150 kΩ:<br>"
                        f"R_2 = (V_G / V_DD) &times; R_total = ({vg:.3f} / {vdd:.2f}) &times; 150 = <b>{r2:.2f} kΩ</b><br>"
                        f"R_1 = R_total - R_2 = 150 - {r2:.2f} = <b>{r1:.2f} kΩ</b><br>"
                        f"R_in = R_1 || R_2 = <b>{vals['Rin']:.2f} kΩ</b>",
                        f"Synthesized R1 = {r1:.2f} kOhm, R2 = {r2:.2f} kOhm for VG = {vg:.3f} V"
                    )

            # 10. Output Resistance Rout update if RD and ro are known
            if 'RD' in vals and 'ro' in vals and 'Rout' not in vals:
                ro_val = vals.get('ro', 999999.0)
                rd_val = vals['RD']
                if "Common Drain" not in topo_type:
                    vals['Rout'] = (rd_val * ro_val) / (rd_val + ro_val) if ro_val < 100000 else rd_val

        # Region Verification
        vgs = vals.get('VGS', 0.0)
        vth = vals.get('VTH', 1.0)
        vds = vals.get('VDS', 0.0)
        vov = vals.get('VOV', vgs - vth)

        if vgs < vth or vov <= 0:
            mode = "Cutoff"
            sat_ok = False
            badge_html = f"<b style='color: #f87171;'>CUTOFF (V_GS = {vgs:.2f}V &lt; V_TH = {vth:.2f}V)</b>"
        elif vds >= vov - 1e-4:
            mode = "Saturation"
            sat_ok = True
            margin = vds - vov
            badge_html = (
                f"<b style='color: #34d399;'>SATURATION VERIFIED ✓</b><br>"
                f"V_DS ({vds:.2f}V) &ge; V_OV ({vov:.2f}V) &nbsp; [Saturation Margin: +{margin:.2f}V]"
            )
        else:
            mode = "Triode"
            sat_ok = False
            badge_html = (
                f"<b style='color: #fbbf24;'>TRIODE / LINEAR REGION ⚠</b><br>"
                f"V_DS ({vds:.2f}V) &lt; V_OV ({vov:.2f}V) &nbsp; (Transistor acts as voltage-controlled resistor)"
            )

        add_step(
            "Step Final: Operating Region & Boundary Verification",
            badge_html,
            f"Region: {mode}. V_DS = {vds:.3f} V, V_OV = {vov:.3f} V."
        )

        full_html = "".join(steps)
        full_plain = "\n".join(raw_steps)
        return vals, full_html, full_plain, mode, sat_ok


class AnalogMosfetSolverDialog(QDialog):
    """
    Bidirectional Problem Solver for Analog MOSFET Circuits.
    Every variable can be dynamically configured as 'Given (Input)' or 'To Find (Target)'.
    """

    PARAM_DEFINITIONS = [
        # (Key, Category, Symbol, Label, Unit, DefaultVal)
        ("VDD", "Power & Bias Network", "V_DD", "Supply Voltage", "V", 10.0),
        ("R1",  "Power & Bias Network", "R_1",  "Upper Divider Resistor", "kΩ", 100.0),
        ("R2",  "Power & Bias Network", "R_2",  "Lower Divider Resistor", "kΩ", 47.0),
        ("RD",  "Power & Bias Network", "R_D",  "Drain Resistor", "kΩ", 2.0),
        ("RS",  "Power & Bias Network", "R_S",  "Source Resistor", "kΩ", 1.0),

        ("VTH", "Device Parameters",    "V_TH", "Threshold Voltage", "V", 1.5),
        ("Kn",  "Device Parameters",    "K_n",  "Conduction Factor 0.5μCoxW/L", "mA/V²", 1.0),
        ("LAM", "Device Parameters",    "λ",    "Channel-Length Modulation", "1/V", 0.01),

        ("ID",  "DC Operating Point",   "I_D",  "Drain Current", "mA", 0.8),
        ("VGS", "DC Operating Point",   "V_GS", "Gate-Source Voltage", "V", 2.3),
        ("VDS", "DC Operating Point",   "V_DS", "Drain-Source Voltage", "V", 3.8),
        ("VOV", "DC Operating Point",   "V_OV", "Overdrive (V_GS - V_TH)", "V", 0.8),
        ("VG",  "DC Operating Point",   "V_G",  "Gate DC Voltage", "V", 3.2),
        ("VS",  "DC Operating Point",   "V_S",  "Source DC Voltage", "V", 0.9),
        ("VD",  "DC Operating Point",   "V_D",  "Drain DC Voltage", "V", 4.7),

        ("gm",  "Small-Signal & Gain",  "g_m",  "Transconductance", "mS", 1.6),
        ("ro",  "Small-Signal & Gain",  "r_o",  "Output Resistance", "kΩ", 100.0),
        ("Av",  "Small-Signal & Gain",  "A_v",  "Voltage Gain", "V/V", -3.2),
        ("Rin", "Small-Signal & Gain",  "R_in", "Input Impedance", "kΩ", 32.0),
        ("Rout","Small-Signal & Gain",  "R_out","Output Impedance", "kΩ", 2.0),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bidirectional Analog MOSFET Problem Solver")
        self.resize(1050, 780)
        self.setMinimumSize(880, 600)
        self._current_plain_solution = ""
        self.param_widgets = {}

        self._init_ui()
        self._apply_preset_forward()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #0d1117; color: #e6edf3; font-family: 'Segoe UI', Arial, sans-serif; }
            QLabel { color: #c9d1d9; font-size: 10pt; }
            QGroupBox {
                border: 1px solid #30363d;
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
                font-size: 10pt;
                color: #58a6ff;
                padding-top: 12px;
                background-color: #161b22;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QComboBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #f0f6fc;
                padding: 3px 6px;
                font-size: 9pt;
            }
            QLineEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #f0f6fc;
                padding: 3px 6px;
                font-family: Consolas, monospace;
                font-size: 9.5pt;
            }
            QLineEdit:focus { border: 1px solid #58a6ff; }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #c9d1d9;
                padding: 5px 12px;
                font-size: 9pt;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #30363d; color: #ffffff; }
            QRadioButton { color: #c9d1d9; font-size: 9.5pt; }
            QCheckBox { color: #c9d1d9; font-size: 9.5pt; }
            QScrollArea { border: none; background: transparent; }
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 14, 16, 14)
        main_lay.setSpacing(10)

        # 1. Header & Configuration Banner
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; border-radius: 6px;")
        h_lay = QVBoxLayout(header_card)
        h_lay.setContentsMargins(14, 10, 14, 10)
        h_lay.setSpacing(8)

        top_row = QHBoxLayout()
        title_icon = QLabel("📐")
        title_icon.setFont(QFont("Segoe UI Emoji", 16))
        title_lbl = QLabel("Bidirectional Analog MOSFET Problem Solver")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_lbl.setStyleSheet("color: #58a6ff;")
        self.badge_mode = QLabel("READY TO SOLVE")
        self.badge_mode.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.badge_mode.setStyleSheet("background: #1f2937; color: #9ca3af; padding: 4px 10px; border-radius: 4px;")

        top_row.addWidget(title_icon)
        top_row.addWidget(title_lbl)
        top_row.addStretch()
        top_row.addWidget(self.badge_mode)
        h_lay.addLayout(top_row)

        # Controls Row: Transistor Type, Topology, Bypass Toggle
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(16)

        lbl_type = QLabel("Device:")
        lbl_type.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.radio_nmos = QRadioButton("NMOS (Enhancement)")
        self.radio_pmos = QRadioButton("PMOS (Enhancement)")
        self.radio_nmos.setChecked(True)
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio_nmos)
        self.radio_group.addButton(self.radio_pmos)

        ctrl_row.addWidget(lbl_type)
        ctrl_row.addWidget(self.radio_nmos)
        ctrl_row.addWidget(self.radio_pmos)
        ctrl_row.addSpacing(12)

        lbl_topo = QLabel("Topology:")
        lbl_topo.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.combo_topo = QComboBox()
        self.combo_topo.addItems([
            "Common Source (CS) Amplifier",
            "Common Drain (CD / Source Follower)",
            "Common Gate (CG) Amplifier",
            "Direct Terminal Biasing (Fixed VG, VD, VS)"
        ])
        ctrl_row.addWidget(lbl_topo)
        ctrl_row.addWidget(self.combo_topo, stretch=1)

        self.chk_bypass = QCheckBox("Source Bypass Capacitor (C_S active)")
        self.chk_bypass.setChecked(True)
        ctrl_row.addWidget(self.chk_bypass)

        h_lay.addLayout(ctrl_row)
        main_lay.addWidget(header_card)

        # 2. Quick Preset Buttons Bar
        preset_bar = QHBoxLayout()
        preset_bar.setSpacing(8)
        lbl_pre = QLabel("⚡ Quick Presets:")
        lbl_pre.setFont(QFont("Segoe UI", 9, QFont.Bold))
        lbl_pre.setStyleSheet("color: #8b949e;")
        preset_bar.addWidget(lbl_pre)

        btn_pre_fwd = QPushButton("Forward CS (Given Resistors ➔ Find Q-Point, Av)")
        btn_pre_fwd.clicked.connect(self._apply_preset_forward)
        btn_pre_des = QPushButton("Design Mode (Given Av, ID ➔ Find RD, RS)")
        btn_pre_des.clicked.connect(self._apply_preset_design)
        btn_pre_q = QPushButton("Bias Matching (Given ID, VDS ➔ Find RD, RS)")
        btn_pre_q.clicked.connect(self._apply_preset_q_point)
        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self._clear_all)

        preset_bar.addWidget(btn_pre_fwd)
        preset_bar.addWidget(btn_pre_des)
        preset_bar.addWidget(btn_pre_q)
        preset_bar.addWidget(btn_clear)
        preset_bar.addStretch()
        main_lay.addLayout(preset_bar)

        # 3. Unified Parameter Table (Scrollable Two-Column Categorized Grid)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent;")
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(12)

        categories = [
            ("Power & Bias Network", ["VDD", "R1", "R2", "RD", "RS"]),
            ("Device Parameters", ["VTH", "Kn", "LAM"]),
            ("DC Operating Point (Q-Point)", ["ID", "VGS", "VDS", "VOV", "VG", "VS", "VD"]),
            ("AC Small-Signal & Gain", ["gm", "ro", "Av", "Rin", "Rout"]),
        ]

        # Two groups side-by-side per row
        row_grid = QGridLayout()
        row_grid.setSpacing(10)
        r_idx = 0

        for cat_title, keys in categories:
            gb = QGroupBox(cat_title)
            g_lay = QGridLayout(gb)
            g_lay.setContentsMargins(10, 14, 10, 10)
            g_lay.setSpacing(6)

            # Columns: Symbol, Label, Role Combo, Input LineEdit, Unit
            for row_i, k in enumerate(keys):
                item_def = next(x for x in self.PARAM_DEFINITIONS if x[0] == k)
                sym, name, unit, def_val = item_def[2], item_def[3], item_def[4], item_def[5]

                lbl_sym = QLabel(f"<b>{sym}</b>")
                lbl_sym.setStyleSheet("color: #58a6ff; font-family: Consolas, monospace; font-size: 10pt;")
                lbl_sym.setFixedWidth(46)

                lbl_name = QLabel(name)
                lbl_name.setStyleSheet("color: #c9d1d9; font-size: 9pt;")
                lbl_name.setToolTip(f"{name} ({sym})")

                role_combo = QComboBox()
                role_combo.addItem("Given (Input)")
                role_combo.addItem("To Find (Target)")
                role_combo.setFixedWidth(130)

                edit = QLineEdit()
                edit.setText(str(def_val))
                edit.setAlignment(Qt.AlignRight)
                edit.setFixedWidth(100)

                lbl_unit = QLabel(unit)
                lbl_unit.setStyleSheet("color: #8b949e; font-size: 8.5pt;")
                lbl_unit.setFixedWidth(42)

                role_combo.currentIndexChanged.connect(
                    lambda idx, e=edit, r=role_combo: self._on_role_changed(r, e)
                )

                g_lay.addWidget(lbl_sym, row_i, 0)
                g_lay.addWidget(lbl_name, row_i, 1)
                g_lay.addWidget(role_combo, row_i, 2)
                g_lay.addWidget(edit, row_i, 3)
                g_lay.addWidget(lbl_unit, row_i, 4)

                self.param_widgets[k] = {
                    'combo': role_combo,
                    'edit': edit,
                    'unit': unit,
                    'sym': sym,
                    'name': name
                }

            row_grid.addWidget(gb, r_idx // 2, r_idx % 2)
            r_idx += 1

        content_lay.addLayout(row_grid)
        scroll.setWidget(content)
        main_lay.addWidget(scroll, stretch=1)

        # 4. Action Row: Solve Button & Toggle Procedure
        act_row = QHBoxLayout()
        act_row.setSpacing(10)

        self.btn_solve = QPushButton("⚡ Solve Circuit (Calculate Unknowns)")
        self.btn_solve.setFixedHeight(38)
        self.btn_solve.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_solve.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                border: 1px solid #388bfd;
                border-radius: 6px;
                padding: 6px 20px;
            }
            QPushButton:hover { background-color: #388bfd; }
            QPushButton:pressed { background-color: #1158c7; }
        """)
        self.btn_solve.setCursor(Qt.PointingHandCursor)
        self.btn_solve.clicked.connect(self._solve_circuit)

        self.btn_toggle_steps = QPushButton("📖 Show Step-by-Step Procedure & Formulas")
        self.btn_toggle_steps.setFixedHeight(38)
        self.btn_toggle_steps.setCheckable(True)
        self.btn_toggle_steps.setChecked(True)
        self.btn_toggle_steps.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:checked {
                background-color: #30363d;
                color: #58a6ff;
                border: 1px solid #58a6ff;
            }
        """)
        self.btn_toggle_steps.toggled.connect(self._toggle_steps_panel)

        self.btn_copy_steps = QPushButton("📋 Copy Solution")
        self.btn_copy_steps.setFixedHeight(38)
        self.btn_copy_steps.clicked.connect(self._copy_solution_to_clipboard)

        act_row.addWidget(self.btn_solve, stretch=2)
        act_row.addWidget(self.btn_toggle_steps, stretch=1)
        act_row.addWidget(self.btn_copy_steps)
        main_lay.addLayout(act_row)

        # 5. Expanding Step-by-Step Rich Derivation Card
        self.steps_container = QFrame()
        self.steps_container.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; border-radius: 6px;")
        sc_lay = QVBoxLayout(self.steps_container)
        sc_lay.setContentsMargins(12, 10, 12, 10)
        sc_lay.setSpacing(6)

        st_head = QLabel("📖 Step-by-Step Mathematical Derivation & Verification")
        st_head.setFont(QFont("Segoe UI", 10, QFont.Bold))
        st_head.setStyleSheet("color: #58a6ff;")
        sc_lay.addWidget(st_head)

        self.steps_browser = QTextBrowser()
        self.steps_browser.setMinimumHeight(170)
        self.steps_browser.setStyleSheet("border: none; background: #0d1117; color: #c9d1d9; font-family: Consolas, monospace;")
        sc_lay.addWidget(self.steps_browser)

        main_lay.addWidget(self.steps_container)

    def _on_role_changed(self, combo, edit):
        is_given = (combo.currentIndex() == 0)
        if is_given:
            combo.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #38bdf8;")
            edit.setReadOnly(False)
            edit.setPlaceholderText("")
            edit.setStyleSheet("background-color: #0d1117; color: #f0f6fc; border: 1px solid #30363d;")
        else:
            combo.setStyleSheet("background-color: #2e1065; color: #c084fc; border: 1px solid #c084fc;")
            edit.setReadOnly(True)
            edit.setPlaceholderText("Calculated on Solve")
            edit.setStyleSheet("background-color: #131722; color: #94a3b8; border: 1px dashed #64748b;")

    def _toggle_steps_panel(self, checked):
        self.steps_container.setVisible(checked)

    def _apply_preset_forward(self):
        """Forward CS Bias: Given Resistors + Device -> Find Q-Point & Gain."""
        self.combo_topo.setCurrentIndex(0)
        self.radio_nmos.setChecked(True)
        self.chk_bypass.setChecked(True)

        given_vals = {
            "VDD": "10.0", "R1": "100.0", "R2": "47.0", "RD": "2.0", "RS": "1.0",
            "VTH": "1.5", "Kn": "1.0", "LAM": "0.01"
        }
        for k, w in self.param_widgets.items():
            if k in given_vals:
                w['combo'].setCurrentIndex(0)
                w['edit'].setText(given_vals[k])
            else:
                w['combo'].setCurrentIndex(1)
                w['edit'].clear()

        self._solve_circuit()

    def _apply_preset_design(self):
        """Design Mode: Target Av & ID -> Find RD & RS."""
        self.combo_topo.setCurrentIndex(0)
        self.radio_nmos.setChecked(True)
        self.chk_bypass.setChecked(True)

        given_vals = {
            "VDD": "12.0", "VTH": "1.2", "Kn": "1.5", "LAM": "0.01",
            "ID": "1.5", "Av": "-8.0", "VDS": "5.0", "R1": "120.0", "R2": "68.0"
        }
        for k, w in self.param_widgets.items():
            if k in given_vals:
                w['combo'].setCurrentIndex(0)
                w['edit'].setText(given_vals[k])
            else:
                w['combo'].setCurrentIndex(1)
                w['edit'].clear()

        self._solve_circuit()

    def _apply_preset_q_point(self):
        """Bias Matching: Given ID & VDS -> Find RD & RS."""
        self.combo_topo.setCurrentIndex(0)
        self.radio_nmos.setChecked(True)

        given_vals = {
            "VDD": "10.0", "VTH": "1.5", "Kn": "1.0", "LAM": "0.0",
            "ID": "1.0", "VDS": "4.0", "VG": "3.5"
        }
        for k, w in self.param_widgets.items():
            if k in given_vals:
                w['combo'].setCurrentIndex(0)
                w['edit'].setText(given_vals[k])
            else:
                w['combo'].setCurrentIndex(1)
                w['edit'].clear()

        self._solve_circuit()

    def _clear_all(self):
        for w in self.param_widgets.values():
            w['combo'].setCurrentIndex(0)
            w['edit'].clear()
        self.steps_browser.clear()
        self.badge_mode.setText("CLEARED")
        self.badge_mode.setStyleSheet("background: #1f2937; color: #9ca3af; padding: 4px 10px; border-radius: 4px;")

    def _solve_circuit(self):
        given_dict = {}
        target_keys = set()

        for k, w in self.param_widgets.items():
            if w['combo'].currentIndex() == 0:  # Given
                txt = w['edit'].text().strip()
                if txt:
                    try:
                        given_dict[k] = float(txt)
                    except ValueError:
                        QMessageBox.warning(self, "Invalid Input", f"Value for '{w['name']} ({k})' is not a valid number.")
                        return
            else:  # To Find
                target_keys.add(k)

        topo = self.combo_topo.currentText()
        is_nmos = self.radio_nmos.isChecked()
        bypassed = self.chk_bypass.isChecked()

        try:
            solved, steps_html, steps_plain, mode, sat_ok = BidirectionalMosfetEngine.solve(
                given_dict, target_keys, topo_type=topo, is_nmos=is_nmos, bypassed=bypassed
            )

            # Update To-Find input boxes with solved values and glowing green highlight
            for k in target_keys:
                w = self.param_widgets[k]
                if k in solved:
                    val = solved[k]
                    fmt = f"{val:.2f}" if abs(val) >= 10 else f"{val:.3f}"
                    w['edit'].setText(fmt)
                    w['edit'].setStyleSheet("""
                        background-color: #064e3b;
                        color: #34d399;
                        border: 1px solid #10b981;
                        font-weight: bold;
                    """)
                else:
                    w['edit'].setText("—")
                    w['edit'].setStyleSheet("background-color: #161b22; color: #ef4444; border: 1px solid #ef4444;")

            # Update Badge
            if mode == "Saturation":
                self.badge_mode.setText("SATURATION VERIFIED ✓")
                self.badge_mode.setStyleSheet("background: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
            elif mode == "Triode":
                self.badge_mode.setText("TRIODE REGION ⚠")
                self.badge_mode.setStyleSheet("background: #451a03; color: #fbbf24; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
            else:
                self.badge_mode.setText("CUTOFF (OFF) ✕")
                self.badge_mode.setStyleSheet("background: #4c0519; color: #f87171; padding: 4px 10px; border-radius: 4px; font-weight: bold;")

            # Display Derivations
            self.steps_browser.setHtml(steps_html)
            self._current_plain_solution = steps_plain

        except Exception as err:
            self.steps_browser.setHtml(f"<b style='color: #f87171;'>Solver Error: {err}</b>")

    def _copy_solution_to_clipboard(self):
        if not self._current_plain_solution:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(self._current_plain_solution)
        self.btn_copy_steps.setText("✓ Copied!")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_copy_steps.setText("📋 Copy Solution"))
