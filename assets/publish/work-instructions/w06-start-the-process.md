# Work Instruction: Start the Thermolysis Process
**WI ID:** WI-006  
**Related Process:** P-001 Thermolysis Pot Cycle ([p01-high-level-process.md](../processes/p01-high-level-process.md))  
**Revision:** 1.1  
**Location:** Control Room / Main Control Panel, Condenser & Tank Area, Thermal Oxidiser  
**Document Owner:** Facility Manager  
**Approver:** Operations Director  
**Status:** Draft for approval  
**Effective Date:** To be assigned on approval  
**Next Review:** 12 months after approval, or earlier following material change or incident

> [!NOTE]
> Values marked **[TBC]** (baseline ranges, alarm limits, program names) must be confirmed against the approved recipe and the manufacturer's control system documentation before approval.

## 1. Purpose & Scope
**Purpose:** To bring the system online in a controlled way: correct valve line-up, verified instruments and baseline readings, and the approved thermolysis program. The cycle (approximately 14–16 h, 200–500 °C) then runs inside its approved limits, gives traceable product, and meets licence conditions.

**Scope:** Starts with the pot connected in the kiln ([WI-005](w05-place-the-pot.md)). Ends with the program running and the first-hour checks complete. Monitoring during the cycle is also covered here. For shutdown, see [WI-008](w08-stopping-the-process.md); for emergencies, see [WI-007](w07-emergency-shutdown.md).

## 2. Safety & PPE (Critical for Pyrolysis)
> [!IMPORTANT]
> **DANGER:** Once heating starts, the system contains **flammable gas and vapour under heat**. **Never start heating unless the full gas path to the thermal oxidiser is open.** A closed valve can over-pressurise the system. Before proceeding, confirm the LEL sensors are active and healthy. **Never bypass an interlock or alarm** (FOM-001 §7.6).

- **Required PPE (field checks):** Safety glasses, FR coveralls, steel-capped boots, heat-resistant gloves, hearing protection, personal 4-gas detector.
- **Emergency Stop:** RED emergency shutdown button on the main control panel. Field emergency stops: **[TBC locations]**. Response: [WI-007](w07-emergency-shutdown.md).
- **Key hazards:** over-pressure, gas leaks, fire or explosion, hot surfaces, and electrical hazards at the panel.

## 3. Environmental Aspects & Controls (ISO 14001)
| Aspect | Potential Impact | Control |
|--------|------------------|---------|
| Non-condensable gas emissions | Air pollution, licence breach | The thermal oxidiser must be running and at its operating temperature **before** gas arrives. Monitor the emissions per licence conditions. |
| Fugitive leaks at the flanges and lid | VOC emissions, odour | Do a leak check at the first temperature hold. Walk-down inspections at the frequency below. |
| Energy use (kiln heating) | Greenhouse gas emissions, resource use | Use only the approved recipe. Record energy use per batch for the objectives and targets (FOM-001 §5.4). |
| Tank overfill | Spill, soil or stormwater contamination | Confirm receiving tank capacity before start. High-level alarms must be active. |

## 4. Roles, Responsibilities & Competence
| Role | Responsibility |
|------|----------------|
| Control Panel Operator (authorised) | Checks the line-up, verifies the baseline, selects the program, monitors the cycle and keeps the log. |
| Field Operator | Opens and checks valves, checks for leaks, does walk-down inspections. |
| Facility Manager or delegate | Authorises the batch sheet and recipe. Approves any deviation. |

## 5. Tools & Equipment
- Main control panel / human-machine interface (HMI) and approved thermolysis program library
- Current P&ID, Valve Schedule and F-006 Valve Line-up & Pre-start Checklist
- Personal 4-gas detector, leak-detection spray, infrared thermometer
- Radio or communication device between the control room and the field

## 6. Pre-conditions (Start Criteria)
- [ ] WI-005 has been completed and the flange hold point is signed in F-001.
- [ ] The batch sheet is authorised and the recipe/program ID is specified.
- [ ] Receiving tanks (H1, H2, H3, H4) have enough ullage (free space) for the expected yield: **[TBC] L** each.
- [ ] The thermal oxidiser fuel supply, the activated carbon system, cooling water and compressed air are available.
- [ ] Daily pre-start checks are complete (FOM-001 §7.1): bunds, alarms, fire equipment and spill kits.
- [ ] No open maintenance permits or isolations on the process train.

## 7. Step-by-Step Procedure
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | Switch on the control panel and the monitoring equipment. Let the system self-test. | No active faults. The LEL and gas detectors show HEALTHY. |
| 2 | Check that all sensor cables are connected and that every lid and process sensor reads at the panel. | Every sensor shows a live, credible value (no open-circuit or out-of-range flags). |
| 3 | Start the thermal oxidiser and bring it up to operating temperature. | Temperature ≥ **[TBC] °C** **before** Step 6. |
| 4 | Field Operator: follow F-006 and open the knife valves in this order: thermal oxidiser inlet, then tanks, then condensers. Confirm the column knife valve is open (from WI-005). | **HOLD POINT:** every valve on F-006 is confirmed OPEN, from the pot to the thermal oxidiser. The Panel Operator countersigns. |
| 5 | Check the baseline readings at the panel. | Pressure = **[TBC] kPa(g) ± [TBC]** (ambient or baseline). Temperatures are at ambient or residual baseline. Record them on F-007. |
| 6 | Select the thermolysis program shown on the batch sheet. Check the program ID and version on screen against the batch sheet. | **Quality gate:** the program ID matches the batch sheet exactly. |
| 7 | Press **START**. Record the start time and the batch number on F-007. | The program status shows RUNNING. |
| 8 | At the first temperature hold (about **[TBC] °C**), the Field Operator leak-tests the lid joint, the column flange and the condenser joints. | No leak (no bubbles, and gas detector < 10 % LEL). If there is a leak, follow Troubleshooting. |
| 9 | Monitor the cycle. Record temperature, pressure, thermal oxidiser temperature and tank levels on F-007 **every 30 min** for the first 2 h, then **every [TBC] h**. | All readings are within the recipe envelope. Investigate any trend toward an alarm limit (FOM-001 §8.1). |
| 10 | Field walk-down every **[TBC] h**: check for leaks, odour, abnormal noise, and condenser and tank condition. | Record on F-007. Report any abnormality immediately. |
| 11 | At shift change, hand over the process status, alarms and any deviations. | Handover recorded on F-007. |

## 8. Troubleshooting
| Issue | Possible Cause | Corrective Action |
|-------|----------------|------------------|
| Baseline pressure not at zero/baseline | Valve closed, blockage, or sensor fault | Do not start. Re-check the F-006 line-up and the sensor. Notify the Facility Manager. |
| Thermal oxidiser will not reach temperature | Fuel supply or burner fault | Do not start the program. Notify the Facility Manager to arrange maintenance. |
| Leak found at the first hold | Gasket or lid seal failure | Put the program on HOLD (or abort it per the manufacturer's instructions). If the leak is major or the LEL is ≥ 10 %, start [WI-007](w07-emergency-shutdown.md). Raise F-004. |
| Pressure rising faster than the recipe | Downstream restriction, or high-volatile feedstock | Check the valve positions and condenser cooling. If the pressure reaches the alarm limit **[TBC]**, follow [WI-007](w07-emergency-shutdown.md). |
| Temperature not rising | Heater failure | Check the kiln circuit breakers and alarms. Notify the Facility Manager to arrange maintenance. Record the downtime. |
| Tank high-level alarm | Insufficient ullage | Follow the alarm response. Do not bypass it. Raise F-004. |

## 9. Records to Complete
- F-006 Valve Line-up & Pre-start Checklist
- F-007 Thermolysis Process Log: baseline, program ID, start time, readings, walk-downs, handover
- F-001 Pot Cycle Batch Record (WI-006 sign-off)
- Energy meter reading at start
- F-004 Incident, Near Miss & Nonconformance Report (if required)

## 10. References
- [FOM-001](../manuals/op-manual.md): §3.1 Facility and process, §7.6 Batch processing, §7.10 Environmental controls, §8.1 Monitoring
- EPA Victoria Pilot Project Licence PPL000300013 (air emission and monitoring conditions)
- [OHS Regulations 2017](../assets/regulations/Occupational%20Health%20and%20Safety%20Regulations%202017.md): Part 3.5 Plant
- [Excise Act 1901 s.50](../assets/regulations/Excise%20Act%20%201901.md) and [Excise Guidelines for the fuel industry](../assets/regulations/Excise%20Guidelines%20for%20the%20fuel%20industry.md): manufacture records for recovered hydrocarbon fuel **[applicability to be confirmed]**
- ISO 9001:2015 cl. 8.5.1, 9.1.1; ISO 14001:2015 cl. 8.1, 9.1.1

## 11. Revision History
| Version | Date | Description of Change | Author |
|---------|------|------------------------|-------|
| 1.0     | 2026-10-02 | Initial Release (developed from P-001 draft) | [Name] |
| 1.1 | 2026-10-04 | Roles aligned to the Organisational Structure (Operations Director, Facility Manager, Chief Chemist / Quality Analyst, multi-skilled Operators) | [Name] |
