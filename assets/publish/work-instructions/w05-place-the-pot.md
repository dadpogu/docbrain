# Work Instruction: Place the Pot in the Kiln
**WI ID:** WI-005  
**Related Process:** P-001 Thermolysis Pot Cycle ([p01-high-level-process.md](../processes/p01-high-level-process.md))  
**Revision:** 1.1  
**Location:** Kiln Area / Hot Condenser Connection  
**Document Owner:** Facility Manager  
**Approver:** Operations Director  
**Status:** Draft for approval  
**Effective Date:** To be assigned on approval  
**Next Review:** 12 months after approval, or earlier following material change or incident

> [!NOTE]
> Values marked **[TBC]** must be confirmed before approval. Valve tag numbers must match the current Process & Instrumentation Diagram (P&ID).

## 1. Purpose & Scope
**Purpose:** To place the sealed, loaded pot in the kiln and connect it gas-tight to the hot condenser and the instrumentation, ready for process start-up.

**Scope:** Starts with a sealed pot ([WI-004](w04-close-pot-lid.md)). Ends with the pot in the kiln, the column flange connected and leak-free, the column knife valve open, and the sensors connected. Opening the downstream valves and starting the program is covered by [WI-006](w06-start-the-process.md).

## 2. Safety & PPE (Critical for Pyrolysis)
> [!IMPORTANT]
> **DANGER:** The kiln, its surrounds and the condenser may still be **hot** from earlier cycles. The condenser line may contain residual flammable vapour. **The kiln must be de-energised and isolated (lock-out/tag-out (LOTO)) while the pot is being placed.**

- **Required PPE:** Heat-resistant gloves, safety glasses and face shield, FR coveralls, steel-capped boots, hard hat during crane lifts, and a personal 4-gas detector.
- **Emergency Stop:** RED button on the main control panel. Kiln-area emergency stop: **[TBC location]**. Response: [WI-007](w07-emergency-shutdown.md).
- **Key hazards:** suspended load (pot, lid and charge: **[TBC kg]**), hot surfaces, residual gas at the condenser flange, crush points between the pot and the kiln wall, and electrical hazards from sensor connections.

## 3. Environmental Aspects & Controls (ISO 14001)
| Aspect | Potential Impact | Control |
|--------|------------------|---------|
| Flange leak at the column or condenser joint | Fugitive VOC emissions, odour, fire | Use a new gasket every cycle and tighten the bolts in sequence. Leak-test before heating (and again at [WI-006](w06-start-the-process.md)). |
| Residual vapour released when the blank is removed | Odour, air emissions | Keep the condenser-side knife valve **closed** until the flange is fully made up. Remove the blank under local extraction. |
| Used gaskets | Waste | Segregate them for appropriate disposal (they may be contaminated). |

## 4. Roles, Responsibilities & Competence
| Role | Responsibility |
|------|----------------|
| Operator | Makes up the flange, connects the sensors and operates the valve. |
| Crane Operator (HRWL where required) | Lifts and places the pot. |
| Dogger / Rigger (if the lift needs one under OHS Regs Part 3.6) | Slings the load and directs the crane. |
| Facility Manager (or an Operator delegated in writing, not the person who made up the flange) | Verifies isolation and the flange connection before the knife valve is opened. |

## 5. Tools & Equipment
- Overhead crane and rated lifting gear for the full pot mass
- Lock-out/tag-out kit (personal locks and danger tags)
- New column flange gasket **[specification TBC]**
- Flange bolts and nuts, spanners and calibrated torque wrench (**[TBC] Nm**)
- Flange alignment pins
- Personal 4-gas detector and leak-detection spray (or soap solution)
- Sensor cable connector caps, and contact cleaner (approved)

## 6. Pre-conditions (Start Criteria)
- [ ] WI-004 has been completed and the torque verification hold point is signed in F-001.
- [ ] The previous pot has been removed and the kiln chamber is empty, inspected and free of debris.
- [ ] The kiln is isolated under LOTO, and the control panel shows the kiln is OFF.
- [ ] The hot condenser knife valve is **closed** and the condenser-side flange is blanked.

## 7. Step-by-Step Procedure
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | Confirm the kiln is isolated. Apply a personal lock and tag. | Isolation is verified (try-start test from the control panel). |
| 2 | Inspect the kiln chamber and the pot seating. | Clean, no debris, and refractory or insulation intact. |
| 3 | Complete the crane pre-use check. Attach the rated lifting gear to the pot lifting lugs (**not** to the lid alone). | F-002 is complete. The load is slung through the pot lugs only. |
| 4 | Lift the pot and lid together with the crane. Lift it smoothly and avoid swinging it. | No personnel are under the load and the exclusion zone is set. |
| 5 | Lower the pot into the kiln. Use the guide rails or locating marks to centre it. | The pot is seated level and fully down. The lid column is aligned with the condenser flange. |
| 6 | Remove the lifting gear and move the crane clear. | The crane is parked outside the kiln area. |
| 7 | Remove the column outlet cap. Gas-test at the condenser-side blank, then remove the blank under local extraction. | LEL **< 10 %**. Do not proceed if this limit is exceeded. |
| 8 | Fit a **new** gasket. Align the lid column flange with the hot condenser flange using the alignment pins. | The gasket is centred and not pinched or damaged. |
| 9 | Fit all flange bolts. Tighten them in a star pattern to **[TBC] Nm** in 3 passes. | **HOLD POINT:** all bolts at torque, with an even flange gap. The Facility Manager (or delegate) verifies this and signs F-001. |
| 10 | Open the knife valve at the condenser (column) flange. | The valve position indicator shows OPEN. Record the valve tag and position on F-006. |
| 11 | Connect each sensor cable to the matching lid sensor (temperature, pressure **[TBC list]**). Check the connector tags. | Every connector is seated, locked and correctly matched (tag to tag). |
| 12 | Remove your personal lock once all work in the kiln area is complete and personnel are clear. | Isolation is removed and recorded. Sign off WI-005 in F-001. |

## 8. Troubleshooting
| Issue | Possible Cause | Corrective Action |
|-------|----------------|------------------|
| Pot will not seat level | Debris in the kiln, or pot deformed | Lift the pot out and clear the debris. If the pot is deformed, raise F-004 and do not use it. |
| Flanges will not align | Pot rotated, or column bent | Lift the pot and re-orient it. If the column is bent, raise F-004 and notify the Facility Manager to arrange maintenance. |
| LEL detected at the condenser flange | Residual vapour in the line | Keep extraction on, re-fit the blank and ventilate. Re-test. Notify the Facility Manager. |
| Sensor reads open circuit or abnormal at panel | Connector not seated, or sensor damaged | Re-seat and clean the connector. If the fault persists, do not start; raise F-004. |
| Knife valve stiff or will not open fully | Char or tar build-up | Do not force it. Raise F-004 for maintenance before start-up. |

## 9. Records to Complete
- F-001 Pot Cycle Batch Record: kiln ID, gasket fitted, flange torque, supervisor verification
- F-002 Lifting Equipment Pre-use Checklist
- F-006 Valve Line-up & Pre-start Checklist (column knife valve)
- LOTO / Isolation Register
- F-004 Incident, Near Miss & Nonconformance Report (if required)

## 10. References
- [FOM-001](../manuals/op-manual.md): §7.6 Batch preparation and processing, §7.11 Maintenance and return to service
- [OHS Regulations 2017](../assets/regulations/Occupational%20Health%20and%20Safety%20Regulations%202017.md): Part 3.5 Plant (isolation), Part 3.6 High risk work
- Current P&ID and Valve Schedule **[TBC reference]**
- ISO 9001:2015 cl. 8.5.1; ISO 14001:2015 cl. 8.1

## 11. Revision History
| Version | Date | Description of Change | Author |
|---------|------|------------------------|-------|
| 1.0     | 2026-10-02 | Initial Release (developed from P-001 draft) | [Name] |
| 1.1 | 2026-10-04 | Roles aligned to the Organisational Structure (Operations Director, Facility Manager, Chief Chemist / Quality Analyst, multi-skilled Operators) | [Name] |
