# Work Instruction: Stopping the Process
**WI ID:** WI-008  
**Related Process:** P-001 Thermolysis Pot Cycle ([p01-high-level-process.md](../processes/p01-high-level-process.md))  
**Revision:** 1.1  
**Location:** Control Room / Main Control Panel, Condenser & Tank Area  
**Document Owner:** Facility Manager  
**Approver:** Operations Director  
**Status:** Draft for approval  
**Effective Date:** To be assigned on approval  
**Next Review:** 12 months after approval, or earlier following material change or incident

> [!NOTE]
> Values marked **[TBC]** must be confirmed against the approved recipe and the manufacturer's control system documentation before approval.

## 1. Purpose & Scope
**Purpose:** To confirm that the thermolysis program has completed, isolate the process train in a controlled sequence, and record the batch outcome for traceability, the mass balance and compliance reporting.

**Scope:** Covers the normal end of a program-controlled cycle, from automatic program completion until the knife valves are closed and the pot is cooling. Emergency stops are covered by [WI-007](w07-emergency-shutdown.md). Lifting the pot is covered by [WI-009](w09-lifting-the-pot.md).

## 2. Safety & PPE (Critical for Pyrolysis)
> [!IMPORTANT]
> **DANGER:** When the program ends, the pot is still at process temperature and can still give off gas. **Close the knife valves only after the program shows COMPLETE and the pot pressure is at or below the safe-isolation value [TBC].** Closing them too early can over-pressurise the pot. Before proceeding, confirm the LEL sensors are active.

- **Required PPE (field):** Heat-resistant gloves, safety glasses and face shield, FR coveralls, steel-capped boots, hearing protection, personal 4-gas detector.
- **Emergency Stop:** RED button on the main control panel. Response: [WI-007](w07-emergency-shutdown.md).
- **Key hazards:** hot surfaces, residual gas pressure, and leaks when the valves are operated.

## 3. Environmental Aspects & Controls (ISO 14001)
| Aspect | Potential Impact | Control |
|--------|------------------|---------|
| Residual gas when the valves are closed | Odour, VOC emissions | Close the valves in the specified order. Keep the thermal oxidiser running until the column valve is closed. |
| Thermal oxidiser fuel use after the process | Energy use, emissions | Shut the oxidiser down per the manufacturer's instructions once the gas path is isolated. |
| Product inventory (H1–H4) | Spill risk, traceability | Record the tank levels. Confirm there are no high-level conditions. |

## 4. Roles, Responsibilities & Competence
| Role | Responsibility |
|------|----------------|
| Control Panel Operator | Confirms completion, records the end-of-batch data, and directs the valve closure. |
| Field Operator | Closes and verifies the knife valves. |
| Facility Manager or delegate | Reviews the batch record and any deviations. |

## 5. Tools & Equipment
- Main control panel / HMI
- F-006 Valve Line-up & Pre-start Checklist (isolation section)
- Valve position indicators, valve locks or tags if required
- Personal 4-gas detector

## 6. Pre-conditions (Start Criteria)
- [ ] The thermolysis program has reached its end-of-program state and the system has shut itself down (heating OFF).

## 7. Step-by-Step Procedure
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | Watch the control panel. Confirm the process status shows **COMPLETE** and the elapsed program time is consistent with the recipe (about 14–16 h). | Status = COMPLETE, with no active alarms. Record the end time on F-007. |
| 2 | Record the final readings: pot temperature, pressure, tank levels (H1, H2, H3, H4) and the energy meter reading. | Recorded on F-007. |
| 3 | Wait until the pot pressure is ≤ **[TBC] kPa(g)** and there is no gas flow to the thermal oxidiser **[TBC indicator]**. | **HOLD POINT:** the Panel Operator confirms it is safe to isolate. |
| 4 | Field Operator: close the knife valves to the **process tanks**. | Each valve indicator shows CLOSED. Tick it on F-006. |
| 5 | Close the knife valves to the **condensers**. | Each valve indicator shows CLOSED. Tick it on F-006. |
| 6 | Close the knife valves to the **thermal oxidiser**. | Each valve indicator shows CLOSED. Tick it on F-006. |
| 7 | Close the **column flange** knife valve. | Valve indicator shows CLOSED. Tick it on F-006. |
| 8 | Shut down the thermal oxidiser per the manufacturer's sequence. | The oxidiser is in a safe standby or off state. |
| 9 | Gas-test around the column flange and the valves. | LEL < 10 %. No leak at the closed valves. |
| 10 | Record the batch outcome on F-001: program completed, any deviations, and the production volumes (by tank level difference). | The batch record is complete and ready for the mass balance. |
| 11 | Leave the pot to cool in the kiln. Record the pot temperature every **[TBC] h** until it is ≤ 100 °C (the trigger for WI-009). | Temperature trend recorded on F-007. |

## 8. Troubleshooting
| Issue | Possible Cause | Corrective Action |
|-------|----------------|------------------|
| Program did not finish (aborted or faulted) | Alarm, power interruption or control fault | Treat it as an abnormal event. Follow [WI-007](w07-emergency-shutdown.md) if needed. Raise F-004. The Facility Manager decides what happens to the batch. |
| Pressure does not decay | Gas still being produced, or vent path blocked | Do not close the valves. Keep the gas path to the thermal oxidiser open. Notify the Facility Manager. |
| Valve will not close fully | Char or tar on the gate | Do not force it. Tag it, raise F-004 and notify the Facility Manager to arrange maintenance. Keep the area gas-monitored. |
| Yield well below the expected range | Feedstock variation, leak, or condenser performance | Record it and notify the Facility Manager. Investigate as a potential nonconformity (FOM-001 §8.1, §9.1). |

## 9. Records to Complete
- F-007 Thermolysis Process Log: end time, final readings, cool-down trend
- F-006 Valve Line-up & Pre-start Checklist (isolation section)
- F-001 Pot Cycle Batch Record: batch outcome and production volumes
- Production and stock records for recovered hydrocarbon products **[confirm excise record-keeping applicability]**
- F-004 Incident, Near Miss & Nonconformance Report (if required)

## 10. References
- [FOM-001](../manuals/op-manual.md): §7.6 Batch processing, §7.7 Traceability, §8.1 Monitoring and mass balance
- [Excise Act 1901 s.50 Record keeping](../assets/regulations/Excise%20Act%20%201901.md) and [Excise Guidelines for the fuel industry](../assets/regulations/Excise%20Guidelines%20for%20the%20fuel%20industry.md) **[applicability to be confirmed]**
- ISO 9001:2015 cl. 8.5.1, 8.5.2; ISO 14001:2015 cl. 8.1, 9.1.1

## 11. Revision History
| Version | Date | Description of Change | Author |
|---------|------|------------------------|-------|
| 1.0     | 2026-10-02 | Initial Release (developed from P-001 draft) | [Name] |
| 1.1 | 2026-10-04 | Roles aligned to the Organisational Structure (Operations Director, Facility Manager, Chief Chemist / Quality Analyst, multi-skilled Operators) | [Name] |
