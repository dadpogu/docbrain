# Work Instruction: Pump Out from Process Tanks
**WI ID:** WI-010  
**Related Process:** P-001 Thermolysis Pot Cycle ([p01-high-level-process.md](../processes/p01-high-level-process.md))  
**Revision:** 1.1  
**Location:** Process Tank Area (bunded) / Filtration Units  
**Document Owner:** Facility Manager  
**Approver:** Operations Director  
**Status:** Draft for approval  
**Effective Date:** To be assigned on approval  
**Next Review:** 12 months after approval, or earlier following material change or incident

> [!NOTE]
> Values marked **[TBC]** must be confirmed before approval. Tank and valve tags must match the current P&ID and tank schedule.

## 1. Purpose & Scope
**Purpose:** To transfer the recovered hydrocarbon fractions **H1, H2 and H3** from the process tanks to the filtration units without spills, mixing or loss of traceability, and to keep **H4** for reprocessing in the next pot cycle.

**Scope:** Starts after the process train has been isolated ([WI-008](w08-stopping-the-process.md)). Ends when the H1–H3 transfers are complete and recorded. Filtration, centrifuging, testing and product release are covered by separate procedures (FOM-001 §7.8). Re-use of H4 is covered by [WI-003](w03-load-the-pot.md).

## 2. Safety & PPE (Critical for Pyrolysis)
> [!IMPORTANT]
> **DANGER:** H1–H4 are **flammable or combustible hydrocarbon liquids**. Vapour can form explosive atmospheres. Ground and bond all transfer equipment, keep ignition sources away, and confirm the LEL sensors are active. **Never leave a transfer unattended.**

- **Required PPE:** Chemical splash goggles, nitrile gloves, FR coveralls, steel-capped boots, and an organic vapour respirator if specified on the SDS or by the risk assessment.
- **Emergency Stop:** RED button on the main control panel. Transfer pump emergency stop: **[TBC location]**. Response: [WI-007](w07-emergency-shutdown.md).
- **Key hazards:** flammable vapour, static discharge, skin contact, spills and slips, and pressure in hoses or lines.
- Safety data sheets (SDS) for H1–H4 must be available at the tank area (OHS Regs 2017, Part 4.1).

## 3. Environmental Aspects & Controls (ISO 14001)
| Aspect | Potential Impact | Control |
|--------|------------------|---------|
| Spill or overfill during transfer | Soil, stormwater or groundwater contamination | Transfer only inside the bunded area. Before starting, confirm the receiving vessel has enough free space. Supervise the whole transfer. Keep the spill kit at hand and drains isolated. |
| Mixing of fractions | Off-specification product, more waste | Line up one fraction at a time, with two-person valve verification. Flush lines per **[TBC]**. |
| Tank vapour emissions | VOC emissions, odour | Keep hatches closed. Vent through the designated vent or carbon system. |
| Water phase or sludge in tank bottoms | Water pollution if mishandled | Do not pump the water phase to filtration unless the procedure allows it. Manage it under the process water controls (FOM-001 §7.8). |
| Electricity use (pumps) | Resource use | Stop the pumps immediately when the transfer is complete. |

## 4. Roles, Responsibilities & Competence
| Role | Responsibility |
|------|----------------|
| Operator (authorised for transfers) | Lines up the valves, runs the pumps, supervises the transfer and records volumes. |
| Second Operator (or the Facility Manager) | Independently verifies the valve line-up before the pump starts. |
| Quality Analyst | Assigns the status of the filtered product (awaiting test, released or quarantined). |

## 5. Tools & Equipment
- Transfer pumps and motors (rated for flammable liquids **[TBC Ex rating]**)
- Earthing and bonding clamps
- Tank level gauges (calibrated), and flow meter if fitted
- F-008 Product Transfer Record
- Valve tags and locks
- Spill kit, drip trays, and drain isolation covers or valves
- Sample bottles and chain-of-custody labels (if sampling is required at transfer)

## 6. Pre-conditions (Start Criteria)
- [ ] WI-008 has been completed. The knife valves from the condensers to the tanks are confirmed **closed**.
- [ ] The filtration units are serviceable and have enough capacity for the volume to be transferred.
- [ ] Bunds are clean and dry and the bund drain valves are closed.
- [ ] Earthing and bonding are in place.

## 7. Step-by-Step Procedure
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | Confirm the valves from the condensers to the tanks are **closed**. | Indicators show CLOSED (checked against F-006). |
| 2 | Record the starting level of each tank (H1, H2, H3, H4) and the batch number. | Recorded on F-008. |
| 3 | Take a sample from each tank if the sampling plan requires it. Label it with the batch, fraction, date and time. | Chain-of-custody form started. |
| 4 | Select **one** fraction to transfer (e.g. H1). Open the outlet knife valve of that tank and the inlet valve of the matching filtration unit. Confirm that **all other tank outlet valves, including H4, are closed**. | **HOLD POINT:** a second person verifies the line-up (source tank, route, destination). Two signatures on F-008. |
| 5 | Check the filtration unit has enough free space for the tank volume. | Ullage ≥ the transfer volume plus a **[TBC] %** margin. |
| 6 | Switch on the transfer pump motor. Watch the first minutes for leaks at the pump, hose and flange connections. | No leaks, and flow is confirmed at the destination. |
| 7 | Stay with the transfer the whole time. Monitor the source and destination levels. | Destination level stays below the high-level alarm. |
| 8 | Stop the pump when the source tank reaches the minimum level **[TBC]**, or when water is detected at the outlet. | The pump does not run dry and no water phase is carried over. |
| 9 | Close the tank outlet and filtration inlet valves. | Valves are CLOSED. |
| 10 | Repeat Steps 4–9 for **H2** and then **H3**. | Each fraction is transferred and recorded separately. |
| 11 | **Do NOT pump out H4.** Keep H4 in its tank for reprocessing in the next pot cycle. Record the H4 volume. | **Quality gate:** the H4 outlet to filtration stayed closed throughout. H4 volume is recorded on F-008. |
| 12 | Record the final tank levels and the volumes transferred. Label the filtration units or receiving vessels with the batch, fraction and status **AWAITING TEST**. | The volumes reconcile with F-007 production volumes within **[TBC] %**. |
| 13 | Remove the bonding clamps, cap hose ends over drip trays, and check the bund for any spills. | The bund is clean. Sign off WI-010 in F-001. |

## 8. Troubleshooting
| Issue | Possible Cause | Corrective Action |
|-------|----------------|------------------|
| Pump will not prime or flow is low | Closed valve, blocked strainer or air lock | Stop the pump and check the line-up and strainer. Do not run the pump dry. |
| Leak at the pump or a connection | Gasket, seal or hose failure | Stop the pump, close the valves and contain the leak with the spill kit. Raise F-004. |
| Wrong fraction sent to a filtration unit (mixing) | Line-up error | Stop immediately. Quarantine the affected product. Raise F-004 (nonconforming output, FOM-001 §7.9). |
| H4 pumped out by mistake | Line-up error | Stop. Quarantine and identify the H4. The Facility Manager decides what happens to it. Raise F-004. |
| High-level alarm at the destination | Not enough free space, or level gauge error | Stop the pump right away and verify the level by dipping. Raise F-004. |
| Volumes don't reconcile | Leak, gauge error, or water content | Investigate (FOM-001 §8.1). Check for leaks and verify the gauge calibration. |

## 9. Records to Complete
- F-008 Product Transfer Record: tank levels, volumes, valve line-up verification, H4 retained
- F-001 Pot Cycle Batch Record (WI-010 sign-off)
- Sample chain-of-custody forms
- Product stock and movement records **[confirm excise record-keeping applicability]**
- F-004 Incident, Near Miss & Nonconformance Report (if required)

## 10. References
- [FOM-001](../manuals/op-manual.md): §7.7 Identification and traceability, §7.8 Monitoring, sampling and release, §7.9 Nonconforming outputs, §7.10 Environmental controls
- [OHS Regulations 2017](../assets/regulations/Occupational%20Health%20and%20Safety%20Regulations%202017.md): Part 4.1 Hazardous substances
- Dangerous Goods (Storage and Handling) Regulations 2022 (Vic) **[confirm applicability]**
- [Excise Act 1901 s.50](../assets/regulations/Excise%20Act%20%201901.md) and [Excise Guidelines for the fuel industry](../assets/regulations/Excise%20Guidelines%20for%20the%20fuel%20industry.md) **[applicability to be confirmed]**
- ISO 9001:2015 cl. 8.5.2, 8.5.4, 8.6, 8.7; ISO 14001:2015 cl. 8.1, 8.2

## 11. Revision History
| Version | Date | Description of Change | Author |
|---------|------|------------------------|-------|
| 1.0     | 2026-10-02 | Initial Release (developed from P-001 draft) | [Name] |
| 1.1 | 2026-10-04 | Roles aligned to the Organisational Structure (Operations Director, Facility Manager, Chief Chemist / Quality Analyst, multi-skilled Operators) | [Name] |
